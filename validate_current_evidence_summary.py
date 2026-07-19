#!/usr/bin/env python3
"""Validate the current evidence bridge artifact.

This validator keeps `CURRENT_EVIDENCE_SUMMARY.md` and
`current_evidence_summary.json` tied to their source surfaces without treating a
clean rebuild as new forward-performance evidence.
"""

from __future__ import annotations

import copy
import json
import math
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import current_evidence_summary as summary_builder

BASE = Path(__file__).resolve().parent
SCRIPT = BASE / "current_evidence_summary.py"
MD_OUTPUT = BASE / "CURRENT_EVIDENCE_SUMMARY.md"
JSON_OUTPUT = BASE / "current_evidence_summary.json"
SETTLEMENT_AUDIT_JSON = BASE / "out" / "paper_trade_settlement_audit.json"
VALIDATION_DIR = BASE / "out" / "status_validation" / "current_evidence_summary"
VALIDATION_MD = VALIDATION_DIR / "current_evidence_summary_validation.md"
VALIDATION_JSON = VALIDATION_DIR / "current_evidence_summary_validation.json"
TMP_PARENT = VALIDATION_DIR / "_tmp"
VALID_EVIDENCE_SCOPE = summary_builder.VALID_EVIDENCE_SCOPE
SOURCE_FILE_LABELS = [
    "forward_evidence_scorecard_json",
    "paper_trade_now_json",
    "paper_trade_settlement_audit_json",
    "primary_signals_ledger",
    "primary_settlement_ledger",
    "shadow_signals_ledger",
    "shadow_settlement_ledger",
]

REQUIRED_MARKDOWN_SNIPPETS = [
    "# Current Evidence Summary",
    f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}",
    "new forward-performance evidence, live-profitability evidence, promotion-readiness evidence, or real-money evidence",
    "`OP_DURABLE_K7` remains the safest current OP anchor",
    "`CD_CORE_K8` remains the primary OP/CD paper-basket companion",
    "`OP_REFINED_K7` remains shadow/watch only",
    "Scorecard CI-only source `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`",
    "Current primary paper:",
    "ROI-complete settled rows",
    "hit rate",
    "flat-ticket ROI",
    "Primary rule mix:",
    "OP-anchor settlement gap:",
    "Settlement queue state:",
    "Open settlement queue by rule:",
    "same-candidate anchor-review floor",
    "CD companion rows do not reduce that OP-anchor gap.",
    "Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence.",
    "Latest primary recommendation context:",
    "## Source Consistency",
    "Overall source match: `True` across `PAPER_TRADE_NOW.json`, `out/paper_trade_settlement_audit.json`, and the primary settlement CSV recompute",
    "Primary ROI-complete rows:",
    "Cost/return sums:",
    "CSV settled_ts coverage:",
    "Settlement-audit upstream fingerprints:",
    "settlement audit upstream source fingerprints match disk",
    "scorecard, primary/shadow rules, primary/shadow signal ledgers, and primary/shadow settlement ledgers",
    "## Source Freshness",
    "Right-now source run date:",
    "bridge generated local date:",
    "bridge reference date:",
    "Right-now freshness state:",
    "Stale versus bridge reference date:",
    "Staleness age:",
    "Refresh boundary:",
    "wrapper refresh can update operator surfaces",
    "by itself it does not settle open rows, create ROI-complete evidence, promote OP_DURABLE_K7, or support real-money discussion",
    "## Calendar Context",
    "Generated local date:",
    "generated reference date:",
    "Staleness comparison:",
    "Calendar boundary:",
    "Calendar dates are operator-readiness context only",
    "refresh before right-now use:",
    "Freshness caveat:",
    "Operator issue context:",
    "Ops bucket:",
    "Operator issue boundary:",
    "Operator read gate:",
    "Operator read gate status:",
    "clean-empty/no-target evidence from current card",
    "BAQ (not treated as BEL)",
    "## Gate Minimums",
    "Gate source: `forward_evidence_scorecard.json`; loaded=True",
    "Gate source alignment: `True`",
    "Canonical gate values used by the bridge:",
    "Threshold sources: anchor `forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations`",
    "Real-money prerequisites:",
    "no-BAQ-as-BEL required = `True`",
    "Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`):",
    "`SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json`",
    "`python3 validate_scorecard_ranking_contract_audit.py`",
    "copied 30/20/100 gate floors, tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and no-BAQ-as-BEL prerequisite drift",
    "This route is synchronization metadata only, not current paper evidence.",
    "## Gate Progress",
    "Progress source: `forward_evidence_scorecard.json` `decision_gate_minimums`; status `all_uncleared`; all gates ready = `False`",
    "Primary first-read gate:",
    "OP same-candidate anchor review:",
    "Phase 8 promotion-review gate:",
    "Real-money discussion floor:",
    "Gate-progress boundary: machine-readable routing metadata only",
    "## Shadow Watch Status",
    "OP_REFINED CI-only check:",
    "Scorecard CI-only promotion check: `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` keeps `ci_only_promotion_allowed=false`",
    "OP_REFINED's positive CI lower bound is support context only, not a current paper promotion trigger",
    "OP_REFINED blockers from scorecard:",
    "OP_REFINED required before review:",
    "Does not count: positive bootstrap CI lower bound by itself",
    "the 20-row count is a review floor, not a promotion entitlement",
    "scorecard tiers remain binding (forward_evidence_scorecard.json)",
    "negative-holdout/SKIP rules still need cleaner split-aware evidence before any promotion discussion",
    "Per-rule shadow coverage:",
    "OP_REFINED_K7 (WATCH)",
    "CD_REFINED_K9 (SKIP)",
    "promotion-grade forward evidence",
    "do not promote OP_REFINED_K7 or Phase 8",
    "do not substitute BAQ for BEL",
    "wait for at least 30 ROI-complete primary rows before a first statistical read",
    "wait for 100 total ROI-complete settled observations plus concentration/payout sanity before real-money discussion",
    "## Rebuild & Validate",
    "Machine-readable contract: the JSON sidecar field `rebuild_validation_contract` is the source for this order",
    "quote it as `current_evidence_summary.json.rebuild_validation_contract`",
    "Upstream prerequisite:",
    "`python3 paper_trade_settlement_audit.py` before `python3 current_evidence_summary.py`",
    "Upstream refresh order:",
    "refresh settlement-audit source fingerprints after scorecard, rules, signals, or settlement-ledger byte changes",
    "Rebuild command: `python3 current_evidence_summary.py`",
    "Direct validation command: `python3 validate_current_evidence_summary.py`",
    "Broader rollup after report-surface wording changes:",
    "Green checks are reproducibility/operator-readiness metadata only; they are not settled ROI, live profitability, promotion readiness, bankroll guidance, or real-money evidence.",
    "| forward_evidence_scorecard_json | `forward_evidence_scorecard.json` |",
    "| paper_trade_now_json | `PAPER_TRADE_NOW.json` |",
    "| paper_trade_settlement_audit_json | `out/paper_trade_settlement_audit.json` |",
    "| primary_signals_ledger | `paper_trades/phase7_current_paper_paper_trade_signals.csv` |",
    "| primary_settlement_ledger | `paper_trades/phase7_current_paper_paper_trade_settlements.csv` |",
    "| shadow_signals_ledger | `paper_trades/phase8_shadow_paper_trade_signals.csv` |",
    "| shadow_settlement_ledger | `paper_trades/phase8_shadow_paper_trade_settlements.csv` |",
]

REQUIRED_DO_NOT_DO = {
    "do not change rules from the tiny sample",
    "do not promote OP_REFINED_K7 or Phase 8",
    "do not reopen current odds-only XGBoost",
    "do not substitute BAQ for BEL",
    "do not discuss real-money scaling",
}


def check(condition: bool, name: str, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if condition else "fail", "details": details}


def approx_equal(actual: Any, expected: float, *, tolerance: float = 1e-9) -> bool:
    try:
        value = float(actual)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and abs(value - expected) <= tolerance


def has_timezone_aware_generated_at(payload: dict[str, Any]) -> bool:
    value = str(payload.get("generated_at") or "").strip()
    if not value:
        return False
    parse_text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def load_payload() -> dict[str, Any]:
    return json.loads(JSON_OUTPUT.read_text(encoding="utf-8"))


def render_shadow_rule_progress(rows: list[dict[str, Any]]) -> str:
    return "; ".join(
        (
            f"{row.get('rule_id')} ({row.get('scorecard_tier', 'UNKNOWN')}) "
            f"{row.get('promotion_progress', '0/20 (0.0%)')}"
        )
        for row in rows
    )


def compact_shadow_rule_progress(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "rule_id",
        "signal_rows",
        "roi_complete_settled_rows",
        "promotion_progress",
        "promotion_ready",
        "scorecard_tier",
        "scorecard_action_now",
    ]
    return [{key: row.get(key) for key in keys} for row in rows]


def source_fingerprint_matches_disk(fp: dict[str, Any]) -> tuple[bool, str]:
    path_text = str(fp.get("path") or "").strip()
    if not path_text:
        return False, "missing path"
    path = Path(path_text)
    if not path.is_absolute():
        path = BASE / path
    if not path.exists():
        return False, f"missing source path {path_text}"
    actual = summary_builder.file_fingerprint(path)
    ok = (
        fp.get("path") == actual.get("path")
        and int(fp.get("bytes", -1) or -1) == int(actual.get("bytes", -2) or -2)
        and fp.get("sha256") == actual.get("sha256")
    )
    return ok, f"saved={fp}; actual={actual}"


def parse_source_fingerprints_table(markdown: str) -> dict[str, dict[str, Any]]:
    try:
        section = markdown.split("## Source Fingerprints\n\n", 1)[1]
    except IndexError:
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in section.splitlines():
        if not line.startswith("| "):
            if rows:
                break
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 4 or parts[0] in {"Source", "---"}:
            continue
        source, path_text, bytes_text, sha_text = parts
        try:
            byte_count = int(bytes_text.replace(",", ""))
        except ValueError:
            byte_count = -1
        rows[source] = {
            "path": path_text.strip("`"),
            "bytes": byte_count,
            "sha256": sha_text.strip("`"),
        }
    return rows


def audit_upstream_fingerprint_matches_disk(fp: dict[str, Any]) -> tuple[bool, str]:
    path_text = str(fp.get("path") or "").strip()
    if not path_text:
        return False, "missing path"
    path = Path(path_text)
    if not path.is_absolute():
        path = BASE / path
    if not path.exists():
        return False, f"missing source path {path_text}"
    actual = summary_builder.file_fingerprint(path)
    ok = (
        fp.get("path") == actual.get("path")
        and int(fp.get("bytes", -1) or -1) == int(actual.get("bytes", -2) or -2)
        and fp.get("sha256") == actual.get("sha256")
        and fp.get("exists", True) is not False
    )
    return ok, f"saved={fp}; actual={actual}"


def write_fixture_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def prepare_tmp_parent() -> Path:
    """Use project-local scratch space for validator fixtures and CLI rerenders."""
    if TMP_PARENT.exists():
        shutil.rmtree(TMP_PARENT)
    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    return TMP_PARENT


def stale_best_action_command_ok(payload: dict[str, Any]) -> bool:
    freshness = payload.get("source_freshness", {}) if isinstance(payload.get("source_freshness"), dict) else {}
    best_action = (
        payload.get("current_paper_status", {}).get("best_action", {})
        if isinstance(payload.get("current_paper_status"), dict)
        else {}
    )
    command = str(best_action.get("command") or "") if isinstance(best_action, dict) else ""
    return (not bool(freshness.get("requires_refresh_before_right_now_use"))) or "run_daily_portfolio_observation.sh" in command


def run_cli_parity(saved_payload: dict[str, Any]) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-summary-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        tmp_md = tmpdir / "CURRENT_EVIDENCE_SUMMARY.md"
        tmp_json = tmpdir / "current_evidence_summary.json"
        cmd = [
            "python3",
            str(SCRIPT),
            "--generated-at",
            str(saved_payload["generated_at"]),
            "--md-output",
            str(tmp_md),
            "--json-output",
            str(tmp_json),
        ]
        result = subprocess.run(cmd, cwd=BASE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            return False, f"CLI exited {result.returncode}: {result.stderr.strip()}"
        saved_md = MD_OUTPUT.read_text(encoding="utf-8")
        saved_json = JSON_OUTPUT.read_text(encoding="utf-8")
        if tmp_md.read_text(encoding="utf-8") != saved_md:
            return False, "markdown output differs from a timestamp-pinned CLI rerender"
        if tmp_json.read_text(encoding="utf-8") != saved_json:
            return False, "JSON output differs from a timestamp-pinned CLI rerender"
        if "Saved to:" not in result.stdout:
            return False, "CLI did not report saved outputs"
        return True, "timestamp-pinned CLI rerender matched saved markdown and JSON"


def run_bad_generated_at_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-bad-generated-at-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        bad_output_dir = tmpdir / "bad_generated_at_nested_output" / "artifacts"
        tmp_md = bad_output_dir / "CURRENT_EVIDENCE_SUMMARY.md"
        tmp_json = bad_output_dir / "current_evidence_summary.json"
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--generated-at",
                "2026-06-27 07:08:00",
                "--md-output",
                str(tmp_md),
                "--json-output",
                str(tmp_json),
            ],
            cwd=BASE,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        combined = f"{result.stdout}\n{result.stderr}"
        ok = (
            result.returncode != 0
            and "generated_at must be timezone-aware ISO provenance metadata" in combined
            and not bad_output_dir.exists()
            and not tmp_md.exists()
            and not tmp_json.exists()
        )
        return ok, (
            f"returncode={result.returncode}; created_output_dir={bad_output_dir.exists()}; "
            f"wrote_md={tmp_md.exists()}; wrote_json={tmp_json.exists()}"
        )


def run_source_mismatch_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-source-mismatch-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        primary_audit_count = next(
            int(lane.get("roi_complete_settled_rows") or 0)
            for lane in audit.get("lanes", [])
            if isinstance(lane, dict) and lane.get("name") == "primary"
        )
        mutated = copy.deepcopy(right_now)
        mutated.setdefault("primary", {})["roi_covered_settled"] = primary_audit_count + 1

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        consistency = payload.get("source_consistency", {})
        counts = consistency.get("primary_roi_complete_settled_rows", {})
        ok = (
            consistency.get("overall_match") is False
            and counts.get("paper_trade_now") == primary_audit_count + 1
            and counts.get("settlement_audit") == primary_audit_count
            and counts.get("settlement_csv_recomputed") == primary_audit_count
        )
        return ok, f"fixture counts={counts}; overall_match={consistency.get('overall_match')}"


def run_stale_settlement_audit_source_fingerprint_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-stale-audit-source-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        audit_path = tmpdir / "paper_trade_settlement_audit.json"
        bad_output_dir = tmpdir / "nested" / "bridge_outputs"
        tmp_md = bad_output_dir / "CURRENT_EVIDENCE_SUMMARY.md"
        tmp_json = bad_output_dir / "current_evidence_summary.json"

        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(audit)
        mutated.setdefault("source_files", {}).setdefault("primary_settlement_ledger", {})["sha256"] = "0" * 64
        write_fixture_json(audit_path, mutated)

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--settlement-audit-json",
                str(audit_path),
                "--md-output",
                str(tmp_md),
                "--json-output",
                str(tmp_json),
            ],
            cwd=BASE,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        combined = f"{result.stdout}\n{result.stderr}"
        ok = (
            result.returncode != 0
            and "upstream source fingerprints are stale or incomplete" in combined
            and "rerun `python3 paper_trade_settlement_audit.py` before `python3 current_evidence_summary.py`" in combined
            and "primary_settlement_ledger" in combined
            and not bad_output_dir.exists()
            and not tmp_md.exists()
            and not tmp_json.exists()
        )
        return ok, combined.strip()


def run_gate_source_mismatch_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-gate-mismatch-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(right_now)
        mutated.setdefault("decision_gate_minimums", {})[
            "anchor_displacement_min_roi_complete_settled_observations"
        ] = 31

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        gates = payload.get("decision_gate_minimums", {})
        markdown = summary_builder.render_markdown(payload)
        ok = (
            gates.get("source_values_match_scorecard") is False
            and gates.get("top_card_values", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 31
            and gates.get("scorecard_values", {}).get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and gates.get("mismatched_fields") == ["anchor_displacement_min_roi_complete_settled_observations"]
            and "Gate source alignment: `False`" in markdown
            and "PAPER_TRADE_NOW decision-gate fields do not match forward_evidence_scorecard.json" in markdown
            and "anchor_displacement_min_roi_complete_settled_observations" in markdown
        )
        return ok, f"gate_alignment={gates}"


def run_gate_source_missing_top_card_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-gate-missing-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(right_now)
        gate_payload = mutated.setdefault("decision_gate_minimums", {})
        gate_keys = [
            "anchor_displacement_min_roi_complete_settled_observations",
            "phase8_promotion_review_min_roi_complete_settled_observations",
            "real_money_discussion_min_total_settled_observations_with_usable_roi",
        ]
        for key in gate_keys:
            gate_payload.pop(key, None)

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        gates = payload.get("decision_gate_minimums", {})
        primary = payload.get("current_paper_status", {}).get("primary", {})
        anchor_gap = primary.get("anchor_settlement_gap", {}) if isinstance(primary, dict) else {}
        expected_gate_values = {
            "anchor_displacement_min_roi_complete_settled_observations": 30,
            "phase8_promotion_review_min_roi_complete_settled_observations": 20,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        }
        markdown = summary_builder.render_markdown(payload)
        ok = (
            gates.get("source_values_match_scorecard") is False
            and gates.get("top_card_values") == {key: None for key in gate_keys}
            and gates.get("scorecard_values") == expected_gate_values
            and gates.get("effective_values") == expected_gate_values
            and gates.get("effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and gates.get("missing_top_card_fields") == gate_keys
            and gates.get("mismatched_fields") == gate_keys
            and gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30
            and gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20
            and gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100
            and anchor_gap.get("same_candidate_anchor_review_floor") == 30
            and "Gate source alignment: `False`" in markdown
            and "Missing top-card fields: anchor_displacement_min_roi_complete_settled_observations" in markdown
            and "Use forward_evidence_scorecard.json decision_gate_minimums as the bridge's canonical gate floors" in markdown
            and "Canonical gate values used by the bridge: anchor `30`; Phase 8 `20`; real-money `100`" in markdown
        )
        return ok, f"gate_alignment={gates}; anchor_gap={anchor_gap}"


def run_malformed_scorecard_gate_fails_before_artifacts_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-bad-gates-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        base_scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        cases = [
            (
                "boolean_anchor",
                ("anchor_displacement", "min_roi_complete_settled_observations", True),
                "decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_phase8",
                ("phase8_promotion_review", "min_roi_complete_settled_observations", 0),
                "decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations must be a positive non-boolean integer",
            ),
            (
                "nonpositive_real_money",
                ("real_money_discussion", "min_total_settled_observations_with_usable_roi", 0),
                "decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi must be a positive non-boolean integer",
            ),
        ]
        details: list[str] = []
        all_ok = True
        for case_name, (gate_name, key, value), expected_error in cases:
            scorecard_path = tmpdir / f"{case_name}_forward_evidence_scorecard.json"
            bad_output_dir = tmpdir / case_name / "nested" / "outputs"
            tmp_md = bad_output_dir / "CURRENT_EVIDENCE_SUMMARY.md"
            tmp_json = bad_output_dir / "current_evidence_summary.json"

            mutated = copy.deepcopy(base_scorecard)
            mutated["decision_gate_minimums"][gate_name][key] = value
            write_fixture_json(scorecard_path, mutated)

            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--scorecard-json",
                    str(scorecard_path),
                    "--md-output",
                    str(tmp_md),
                    "--json-output",
                    str(tmp_json),
                ],
                cwd=BASE,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            combined = f"{result.stdout}\n{result.stderr}"
            case_ok = (
                result.returncode != 0
                and expected_error in combined
                and not bad_output_dir.exists()
                and not tmp_md.exists()
                and not tmp_json.exists()
            )
            all_ok = all_ok and case_ok
            details.append(
                f"{case_name}: returncode={result.returncode}; expected_error_present={expected_error in combined}; "
                f"artifacts_absent={not bad_output_dir.exists() and not tmp_md.exists() and not tmp_json.exists()}"
            )
        return all_ok, " | ".join(details)


def run_missing_scorecard_ci_only_diagnostic_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-missing-ci-only-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        bad_output_dir = tmpdir / "nested" / "outputs"
        tmp_md = bad_output_dir / "CURRENT_EVIDENCE_SUMMARY.md"
        tmp_json = bad_output_dir / "current_evidence_summary.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(scorecard)
        mutated.pop("ci_only_promotion_diagnostics", None)
        write_fixture_json(scorecard_path, mutated)

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--scorecard-json",
                str(scorecard_path),
                "--md-output",
                str(tmp_md),
                "--json-output",
                str(tmp_json),
            ],
            cwd=BASE,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        combined = f"{result.stdout}\n{result.stderr}"
        ok = (
            result.returncode != 0
            and "missing ci_only_promotion_diagnostics" in combined
            and not bad_output_dir.exists()
            and not tmp_md.exists()
            and not tmp_json.exists()
        )
        return ok, combined.strip()


def run_csv_timestamp_gap_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-csv-ts-gap-", dir=TMP_PARENT) as tmp:
        csv_path = Path(tmp) / "settlements.csv"
        csv_path.write_text(
            "\n".join(
                [
                    "signal_key,outcome,actual_cost,actual_return,settled_ts",
                    "valid_ts,HIT,24.00,96.00,2026-05-23T19:30:00-04:00",
                    "missing_ts,MISS,24.00,0.00,",
                    "placeholder_ts,MISS,24.00,0.00,<SETTLED_TS>",
                    "malformed_ts,MISS,24.00,0.00,2026-05-23",
                    "zero_cost,MISS,0.00,0.00,2026-05-23T19:40:00-04:00",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        recomputed = summary_builder.summarize_settlement_csv(csv_path)
        ok = (
            recomputed.get("roi_complete_rows_from_csv") == 1
            and recomputed.get("hit_count") == 1
            and recomputed.get("miss_count") == 0
            and approx_equal(recomputed.get("actual_cost_sum"), 24.0)
            and approx_equal(recomputed.get("actual_return_sum"), 96.0)
            and recomputed.get("settled_ts_gap_rows_from_csv") == 3
            and recomputed.get("settled_ts_gap_reason_counts") == {
                "malformed settled_ts": 1,
                "missing settled_ts": 1,
                "placeholder settled_ts": 1,
            }
            and recomputed.get("non_positive_cost_rows_from_csv") == 1
        )
        return ok, f"csv_recompute={recomputed}"


def run_fresh_source_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-source-fresh-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(right_now)
        mutated.setdefault("run_freshness", {})["run_date"] = "2026-05-25"
        mutated.setdefault("run_freshness", {})["as_of_date"] = "2026-05-25"
        mutated.setdefault("run_freshness", {})["is_stale"] = False
        mutated.setdefault("run_freshness", {})["freshness_state"] = "current_run_date"

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        freshness = payload.get("source_freshness", {})
        read = str(freshness.get("read") or "")

        stale_mutated = copy.deepcopy(mutated)
        stale_mutated.setdefault("run_freshness", {})["run_date"] = "2026-05-24"
        stale_mutated.setdefault("run_freshness", {})["as_of_date"] = "2026-05-25"
        stale_mutated.setdefault("run_freshness", {})["is_stale"] = True
        stale_mutated.setdefault("run_freshness", {})["freshness_state"] = "stale_past_run"
        stale_mutated.setdefault("best_action", {})["command"] = "./run_daily_portfolio_observation.sh"
        write_fixture_json(right_now_path, stale_mutated)
        stale_payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        stale_freshness = stale_payload.get("source_freshness", {})
        stale_read = str(stale_freshness.get("read") or "")

        rollover_mutated = copy.deepcopy(mutated)
        rollover_mutated.setdefault("run_freshness", {})["run_date"] = "2026-05-25"
        rollover_mutated.setdefault("run_freshness", {})["as_of_date"] = "2026-05-25"
        rollover_mutated.setdefault("run_freshness", {})["is_stale"] = False
        rollover_mutated.setdefault("run_freshness", {})["freshness_state"] = "current_run_date"
        rollover_mutated.setdefault("best_action", {})["command"] = "./run_daily_portfolio_observation.sh"
        write_fixture_json(right_now_path, rollover_mutated)
        rollover_payload = summary_builder.build_payload(
            generated_at="2026-05-26T00:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        rollover_freshness = rollover_payload.get("source_freshness", {})
        rollover_read = str(rollover_freshness.get("read") or "")

        combined_mutated = copy.deepcopy(stale_mutated)
        combined_mutated.setdefault("best_action", {})["command"] = "./run_daily_portfolio_observation.sh"
        write_fixture_json(right_now_path, combined_mutated)
        combined_payload = summary_builder.build_payload(
            generated_at="2026-05-26T00:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        combined_freshness = combined_payload.get("source_freshness", {})
        combined_read = str(combined_freshness.get("read") or "")

        cest_rollover_mutated = copy.deepcopy(mutated)
        cest_rollover_mutated.setdefault("run_freshness", {})["run_date"] = "2026-05-25"
        cest_rollover_mutated.setdefault("run_freshness", {})["as_of_date"] = "2026-05-25"
        cest_rollover_mutated.setdefault("run_freshness", {})["is_stale"] = False
        cest_rollover_mutated.setdefault("run_freshness", {})["freshness_state"] = "current_run_date"
        cest_rollover_mutated.setdefault("best_action", {})[
            "command"
        ] = "python3 paper_trade_settlement_helper.py list-open --settlement-ledger paper_trades/phase7_current_paper_paper_trade_settlements.csv"
        write_fixture_json(right_now_path, cest_rollover_mutated)
        cest_rollover_payload = summary_builder.build_payload(
            generated_at="2026-05-26T04:12:00+02:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        cest_rollover_freshness = cest_rollover_payload.get("source_freshness", {})
        cest_rollover_calendar = cest_rollover_payload.get("calendar_context", {})
        cest_rollover_read = str(cest_rollover_freshness.get("read") or "")

        missing_state_mutated = copy.deepcopy(mutated)
        missing_state_mutated.setdefault("run_freshness", {}).pop("freshness_state", None)
        missing_state_mutated.setdefault("best_action", {})["command"] = "./run_daily_portfolio_observation.sh"
        write_fixture_json(right_now_path, missing_state_mutated)
        missing_state_payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        missing_state_freshness = missing_state_payload.get("source_freshness", {})
        missing_state_read = str(missing_state_freshness.get("read") or "")

        stale_bad_command_mutated = copy.deepcopy(stale_mutated)
        stale_bad_command_mutated.setdefault("best_action", {})["command"] = "python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv"
        write_fixture_json(right_now_path, stale_bad_command_mutated)
        stale_bad_command_payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )

        ok = (
            freshness.get("is_stale_vs_generated_date") is False
            and freshness.get("right_now_internal_is_stale") is False
            and freshness.get("right_now_freshness_state") == "current_run_date"
            and freshness.get("right_now_freshness_state_valid") is True
            and freshness.get("requires_refresh_before_right_now_use") is False
            and freshness.get("right_now_internal_stale_age_days") == 0
            and freshness.get("source_stale_age_days_vs_bridge") == 0
            and freshness.get("refresh_age_days") == 0
            and stale_best_action_command_ok(payload)
            and "report/navigation context rather than performance evidence" in read
            and stale_freshness.get("is_stale_vs_generated_date") is False
            and stale_freshness.get("right_now_internal_is_stale") is True
            and stale_freshness.get("right_now_freshness_state") == "stale_past_run"
            and stale_freshness.get("right_now_freshness_state_valid") is True
            and stale_freshness.get("requires_refresh_before_right_now_use") is True
            and stale_freshness.get("requires_refresh_reason") == "right_now_internal_stale"
            and stale_freshness.get("right_now_internal_stale_age_days") == 1
            and stale_freshness.get("source_stale_age_days_vs_bridge") == 0
            and stale_freshness.get("refresh_age_days") == 1
            and stale_best_action_command_ok(stale_payload)
            and rollover_freshness.get("is_stale_vs_generated_date") is True
            and rollover_freshness.get("right_now_internal_is_stale") is False
            and rollover_freshness.get("right_now_freshness_state") == "current_run_date"
            and rollover_freshness.get("right_now_freshness_state_valid") is True
            and rollover_freshness.get("requires_refresh_before_right_now_use") is True
            and rollover_freshness.get("requires_refresh_reason") == "source_as_of_older_than_bridge"
            and rollover_freshness.get("right_now_internal_stale_age_days") == 0
            and rollover_freshness.get("source_stale_age_days_vs_bridge") == 1
            and rollover_freshness.get("refresh_age_days") == 1
            and stale_best_action_command_ok(rollover_payload)
            and "older than bridge reference date 2026-05-26" in rollover_read
            and combined_freshness.get("is_stale_vs_generated_date") is True
            and combined_freshness.get("right_now_internal_is_stale") is True
            and combined_freshness.get("right_now_freshness_state") == "stale_past_run"
            and combined_freshness.get("right_now_freshness_state_valid") is True
            and combined_freshness.get("requires_refresh_before_right_now_use") is True
            and combined_freshness.get("requires_refresh_reason") == "right_now_internal_and_source_stale"
            and combined_freshness.get("right_now_internal_stale_age_days") == 1
            and combined_freshness.get("source_stale_age_days_vs_bridge") == 1
            and combined_freshness.get("refresh_age_days") == 1
            and stale_best_action_command_ok(combined_payload)
            and "also older than bridge reference date 2026-05-26" in combined_read
            and cest_rollover_freshness.get("generated_date") == "2026-05-26"
            and cest_rollover_freshness.get("generated_reference_date") == "2026-05-25"
            and cest_rollover_freshness.get("generated_reference_timezone") == "America/New_York"
            and cest_rollover_freshness.get("generated_reference_date_differs_from_local_date") is True
            and cest_rollover_freshness.get("staleness_comparison_date") == "2026-05-25"
            and cest_rollover_freshness.get("is_stale_vs_generated_date") is False
            and cest_rollover_freshness.get("requires_refresh_before_right_now_use") is False
            and cest_rollover_freshness.get("requires_refresh_reason") == "source_current_for_bridge"
            and cest_rollover_freshness.get("right_now_internal_stale_age_days") == 0
            and cest_rollover_freshness.get("source_stale_age_days_vs_bridge") == 0
            and cest_rollover_freshness.get("refresh_age_days") == 0
            and stale_best_action_command_ok(cest_rollover_payload)
            and "not older than bridge reference date 2026-05-25" in cest_rollover_read
            and cest_rollover_calendar.get("staleness_comparison_date") == "2026-05-25"
            and cest_rollover_calendar.get("not_forward_performance_evidence") is True
            and missing_state_freshness.get("right_now_freshness_state") is None
            and missing_state_freshness.get("right_now_freshness_state_valid") is False
            and missing_state_freshness.get("requires_refresh_before_right_now_use") is True
            and missing_state_freshness.get("requires_refresh_reason") == "right_now_freshness_state_missing_or_invalid"
            and missing_state_freshness.get("refresh_age_days") == 0
            and stale_best_action_command_ok(missing_state_payload)
            and "did not publish a valid freshness_state" in missing_state_read
            and stale_best_action_command_ok(stale_bad_command_payload)
            and stale_bad_command_payload.get("current_paper_status", {}).get("best_action", {}).get("source_action_overridden") is True
            and stale_bad_command_payload.get("current_paper_status", {}).get("source_best_action", {}).get("command") == "python3 paper_trade_lane_monitor.py --signals-ledger paper_trades/phase7_current_paper_paper_trade_signals.csv"
            and "Right-now card is stale for its own as-of date" in stale_read
            and "refresh `./run_daily_portfolio_observation.sh`" in stale_read
        )
        return ok, f"fresh_fixture={freshness}; internally_stale_fixture={stale_freshness}; rollover_fixture={rollover_freshness}; cest_rollover_fixture={cest_rollover_freshness}; combined_stale_fixture={combined_freshness}; missing_state_fixture={missing_state_freshness}; bad_stale_command={stale_bad_command_payload.get('current_paper_status', {}).get('best_action', {}).get('command')}"


def run_missing_scan_output_operator_context_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-missing-output-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(right_now)
        mutated["best_action"] = {
            "headline": "Refresh the daily wrapper, primary lane scan-output artifact is missing",
            "lane_key": "primary",
            "lane": "Phase 7 current paper lane",
            "command": "./run_daily_portfolio_observation.sh",
            "why": "The primary lane scanner status was readable, but the scan-output artifact was missing after scanner status reported no_qualifiers; the pipeline used a safe empty [] fallback. Treat this as an artifact issue, not a clean no-qualifier observation.",
            "timing": "now",
        }
        mutated["ops"] = {
            "day_bucket": "ISSUE, MISSING SCAN OUTPUT",
            "takeaway": "Primary lane scan-output artifact was missing after scanner status reported no_qualifiers; pipeline used a safe empty [] fallback, so this is not a clean no-qualifier observation.",
        }

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        context = payload.get("current_paper_status", {}).get("operator_status_context", {})
        read_gate = payload.get("operator_read_gate", {})
        markdown = summary_builder.render_markdown(payload)
        ok = (
            context.get("missing_scan_output_artifact_issue") is True
            and context.get("wrapper_refresh_action") is True
            and read_gate.get("has_missing_scan_output_artifact_issue") is True
            and read_gate.get("requires_refresh_before_evidence_read") is True
            and read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and read_gate.get("not_forward_performance_evidence") is True
            and context.get("ops_day_bucket") == "ISSUE, MISSING SCAN OUTPUT"
            and "not a clean no-qualifier observation" in str(context.get("read") or "")
            and "Operator read gate:" in markdown
            and "refresh/recheck" in str(read_gate.get("read") or "").lower()
            and "Refresh the daily wrapper, primary lane scan-output artifact is missing" in markdown
            and "ISSUE, MISSING SCAN OUTPUT" in markdown
            and "not a clean no-qualifier observation" in markdown
            and payload.get("evidence_boundary", {}).get("operator_issue_context_is_not_performance_proof") is True
        )
        return ok, f"operator_context={context}; operator_read_gate={read_gate}"


def run_no_bet_recommendation_context_fixture() -> tuple[bool, str]:
    context = summary_builder.build_primary_recommendation_context(
        {
            "recent_run_context": (
                "Latest run context: the latest run logged signals but produced no BET recommendations "
                "(1 recommendation(s), 1 raw hit(s))."
            )
        },
        {"ops": {"takeaway": "Signals were logged but nothing reached a bet-ready state."}},
    )
    read = str(context.get("read") or "")
    ok = (
        context.get("latest_context_has_no_bet_recommendations") is True
        and context.get("not_forward_performance_evidence") is True
        and context.get("not_bet_readiness_evidence_by_itself") is True
        and "latest recommendation context is a qualifying scanner observation with no BET recommendation" in read
        and "latest open-row context" not in read
        and "not a bet-ready ticket" in read
        and "settle only from actual result/payout evidence" in read
        and "do not interpret the open row as forward performance" in read
    )
    return ok, f"recommendation_context={context}"


def run_scanner_failure_recommendation_context_fixture() -> tuple[bool, str]:
    context = summary_builder.build_primary_recommendation_context(
        {
            "recent_run_context": (
                "Latest run context: scanner failed before producing signals. Detail: 403 Client Error: Forbidden "
                "for url: https://brk0201-iapi-webservice.nyrabets.com/ListCards.ashx "
                "Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. "
                "Sidecar action: refresh_daily_wrapper_before_evidence_read. "
                "Recheck command: ./run_daily_portfolio_observation.sh."
            )
        },
        {"ops": {"takeaway": "Refresh the daily wrapper before using the best-action card."}},
    )
    read = str(context.get("read") or "")
    ok = (
        context.get("latest_context_has_scanner_failure_boundary") is True
        and context.get("latest_context_has_bet_ready_language") is False
        and context.get("not_forward_performance_evidence") is True
        and context.get("not_bet_readiness_evidence_by_itself") is True
        and "API-access-failure operator context only" in read
        and "not a no-target, clean-empty, or forward-performance read" in read
        and "Sidecar action: refresh_daily_wrapper_before_evidence_read." in read
        and "Recheck command: ./run_daily_portfolio_observation.sh." in read
        and "Use recommendation and settlement ledgers before interpreting bet readiness or forward performance." in read
        and "Treat this as operator context only" not in read
        and "latest recommendation context is a qualifying scanner observation" not in read
    )
    return ok, f"recommendation_context={context}"


def run_api_access_stale_cache_operator_context_fixture() -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="current-evidence-api-stale-cache-", dir=TMP_PARENT) as tmp:
        tmpdir = Path(tmp)
        scorecard_path = tmpdir / "forward_evidence_scorecard.json"
        right_now_path = tmpdir / "PAPER_TRADE_NOW.json"
        audit_path = tmpdir / "paper_trade_settlement_audit.json"

        scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        right_now = json.loads((BASE / "PAPER_TRADE_NOW.json").read_text(encoding="utf-8"))
        audit = json.loads((BASE / "out" / "paper_trade_settlement_audit.json").read_text(encoding="utf-8"))
        mutated = copy.deepcopy(right_now)
        mutated.setdefault("primary", {})["recent_run_context"] = (
            "Latest run context: scanner API-access failure HTTP 403 completed from stale cache. "
            "Treat this as API-access-failure operator context only, not a no-target, clean-empty, or forward-performance read. "
            "Stale-cache fallback used for cards; 2 stale-cache fallback(s); stale-cache fallback error HTTPError: "
            "403 Client Error: Forbidden for url: https://example.invalid/ListCards.ashx. "
            "Sidecar action: refresh_daily_wrapper_before_evidence_read. "
            "Recheck command: ./run_daily_portfolio_observation.sh."
        )
        mutated["ops"] = {
            "day_bucket": "ISSUE, API ACCESS STALE CACHE FALLBACK",
            "takeaway": (
                "API-access stale-cache fallback kept the lane routable, but the HTTP 403 and stale-cache "
                "count/kind/error context mean this is operational routing only."
            ),
        }
        mutated["best_action"] = {
            "headline": "Refresh the daily wrapper before using API stale-cache fallback",
            "lane_key": "primary",
            "lane": "Phase 7 current paper lane",
            "command": "./run_daily_portfolio_observation.sh",
            "why": "API-access stale-cache fallback needs a wrapper refresh before today's card is used as instruction or evidence.",
            "timing": "now",
        }

        write_fixture_json(scorecard_path, scorecard)
        write_fixture_json(right_now_path, mutated)
        write_fixture_json(audit_path, audit)
        payload = summary_builder.build_payload(
            generated_at="2026-05-25T18:12:00-04:00",
            scorecard_json_path=scorecard_path,
            right_now_json_path=right_now_path,
            settlement_audit_json_path=audit_path,
        )
        recommendation_context = payload.get("current_paper_status", {}).get("primary", {}).get("recommendation_context", {})
        operator_read_gate = payload.get("operator_read_gate", {})
        markdown = summary_builder.render_markdown(payload)
        read = str(recommendation_context.get("read") or "")
        reason_text = str(operator_read_gate.get("reason_text") or "")
        ok = (
            recommendation_context.get("latest_context_has_scanner_failure_boundary") is True
            and recommendation_context.get("latest_context_has_stale_cache_fallback") is True
            and operator_read_gate.get("has_api_access_failure_context") is True
            and operator_read_gate.get("has_stale_cache_fallback_context") is True
            and operator_read_gate.get("requires_refresh_before_evidence_read") is True
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("not_forward_performance_evidence") is True
            and "stale-cache fallback context is present" in reason_text
            and "Stale-cache fallback used for cards" in read
            and "2 stale-cache fallback(s)" in read
            and "stale-cache fallback error HTTPError" in read
            and "Sidecar action: refresh_daily_wrapper_before_evidence_read." in read
            and "Recheck command: ./run_daily_portfolio_observation.sh." in read
            and "Latest primary recommendation context: " + read in markdown
            and "stale-cache fallback context is present" in markdown
            and "not a no-target, clean-empty, or forward-performance read" in markdown
            and payload.get("evidence_boundary", {}).get("operator_issue_context_is_not_performance_proof") is True
        )
        return ok, f"recommendation_context={recommendation_context}; operator_read_gate={operator_read_gate}"


def validate() -> dict[str, Any]:
    tmp_parent = prepare_tmp_parent()
    scratch = {
        "tmp_parent": str(tmp_parent),
        "tmp_parent_is_project_local": tmp_parent.is_relative_to(BASE),
        "tmp_parent_cleared_before_fixture_run": True,
    }
    checks: list[dict[str, Any]] = []
    checks.append(check(SCRIPT.exists(), "summary script exists", str(SCRIPT.name)))
    checks.append(check(MD_OUTPUT.exists(), "markdown summary exists", str(MD_OUTPUT.name)))
    checks.append(check(JSON_OUTPUT.exists(), "JSON summary exists", str(JSON_OUTPUT.name)))
    checks.append(check(
        tmp_parent == TMP_PARENT and tmp_parent.is_relative_to(BASE) and tmp_parent.exists(),
        "fixture_scratch_root_project_local",
        f"current-evidence CLI/source/freshness fixtures write under project-local temporary root {tmp_parent}, cleared before fixture checks",
    ))
    checks.append(check(
        scratch["tmp_parent_is_project_local"] is True
        and scratch["tmp_parent_cleared_before_fixture_run"] is True
        and Path(scratch["tmp_parent"]) == TMP_PARENT,
        "fixture_scratch_metadata_published",
        "current-evidence validation publishes top-level project-local scratch metadata so parent/read-order surfaces can verify the cleared fixture root without parsing markdown prose",
    ))

    if not (SCRIPT.exists() and MD_OUTPUT.exists() and JSON_OUTPUT.exists()):
        status = "fail"
        payload: dict[str, Any] = {}
    else:
        payload = load_payload()
        markdown = MD_OUTPUT.read_text(encoding="utf-8")
        parity_ok, parity_detail = run_cli_parity(payload)
        checks.append(check(parity_ok, "saved outputs match timestamp-pinned CLI rerender", parity_detail))
        bad_generated_at_ok, bad_generated_at_detail = run_bad_generated_at_fixture()
        checks.append(check(
            bad_generated_at_ok,
            "timezone-naive generated_at CLI fixture fails before creating output directories or writing bridge outputs",
            bad_generated_at_detail,
        ))

        missing_snippets = [snippet for snippet in REQUIRED_MARKDOWN_SNIPPETS if snippet not in markdown]
        checks.append(check(not missing_snippets, "markdown carries the report-safe current read", "; ".join(missing_snippets)))
        generated_at = str(payload.get("generated_at") or "").strip()
        checks.append(check(
            has_timezone_aware_generated_at(payload)
            and f"Generated: `{generated_at}`" in markdown,
            "bridge generated_at is timezone-aware provenance metadata",
            generated_at,
        ))

        boundary = payload.get("evidence_boundary", {})
        boundary_flags = [
            "not_new_forward_evidence",
            "not_live_profitability_evidence",
            "not_promotion_readiness_evidence",
            "not_real_money_evidence",
            "source_files_are_reproducibility_metadata_only",
            "source_freshness_is_operator_readiness_not_performance_proof",
            "decision_gate_status_is_routing_context_not_performance_proof",
            "operator_issue_context_is_not_performance_proof",
            "operator_read_gate_is_operator_routing_not_performance_proof",
            "scorecard_audit_route_is_synchronization_metadata_only",
        ]
        missing_boundary = [flag for flag in boundary_flags if boundary.get(flag) is not True]
        checks.append(check(not missing_boundary, "JSON evidence boundary blocks overclaiming", "; ".join(missing_boundary)))
        checks.append(check(
            payload.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and boundary.get("valid_evidence_scope") == VALID_EVIDENCE_SCOPE
            and f"valid_evidence_scope={VALID_EVIDENCE_SCOPE}" in markdown,
            "source_current_evidence_summary_exposes_valid_scope",
            f"scope={payload.get('valid_evidence_scope')}; boundary_scope={boundary.get('valid_evidence_scope')}",
        ))

        frozen = payload.get("frozen_posture", {})
        anchor = frozen.get("anchor", {})
        companion = frozen.get("primary_companion", {})
        shadow = frozen.get("shadow_lead", {})
        checks.append(check(anchor.get("rule_id") == "OP_DURABLE_K7" and anchor.get("tier") == "ANCHOR", "frozen posture keeps OP_DURABLE_K7 anchor"))
        checks.append(check(companion.get("rule_id") == "CD_CORE_K8" and companion.get("tier") == "PAPER", "frozen posture keeps CD_CORE_K8 paper companion"))
        checks.append(check(shadow.get("rule_id") == "OP_REFINED_K7" and shadow.get("tier") == "WATCH", "frozen posture keeps OP_REFINED_K7 shadow/watch"))
        source_scorecard = json.loads((BASE / "forward_evidence_scorecard.json").read_text(encoding="utf-8"))
        source_ci_diagnostic = source_scorecard["ci_only_promotion_diagnostics"]["OP_REFINED_K7"]
        ci_only = payload.get("scorecard_ci_only_promotion_check", {})
        shadow_ci_only = (
            payload.get("current_paper_status", {}).get("shadow", {}).get("ci_only_promotion_check", {})
            if isinstance(payload.get("current_paper_status", {}).get("shadow", {}), dict)
            else {}
        )
        checks.append(check(
            ci_only.get("source") == "forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7"
            and ci_only.get("scorecard_ci_only_promotion_diagnostic") == source_ci_diagnostic
            and ci_only.get("candidate_rule_id") == "OP_REFINED_K7"
            and ci_only.get("current_anchor_rule_id") == "OP_DURABLE_K7"
            and ci_only.get("positive_ci_lower_bound_is_support_context") is True
            and ci_only.get("ci_only_promotion_allowed") is False
            and ci_only.get("not_promotion_readiness_evidence") is True
            and shadow.get("scorecard_ci_only_promotion_check") == ci_only
            and shadow_ci_only == ci_only
            and str(ci_only.get("read") or "") in markdown
            and str(ci_only.get("read") or "") in str(payload.get("summary", {}).get("current_read") or "")
            and "Scorecard CI-only source `forward_evidence_scorecard.json:ci_only_promotion_diagnostics.OP_REFINED_K7` says `ci_only_promotion_allowed=false`" in markdown
            and "OP_REFINED blockers from scorecard: " + "; ".join(ci_only.get("why_not", [])) + "." in markdown
            and "OP_REFINED required before review: " + summary_builder.keyed_items_text(ci_only.get("required_before_review")) + "." in markdown
            and "Does not count: " + "; ".join(ci_only.get("does_not_count", [])) + "." in markdown,
            "scorecard CI-only OP_REFINED diagnostic is source-matched in the current-evidence bridge",
            f"source={ci_only.get('source')}; allowed={ci_only.get('ci_only_promotion_allowed')}",
        ))

        primary = payload.get("current_paper_status", {}).get("primary", {})
        first_read = primary.get("first_read", {})
        portfolio_review = primary.get("portfolio_review", {})
        consistency = payload.get("source_consistency", {})
        audit = json.loads(SETTLEMENT_AUDIT_JSON.read_text(encoding="utf-8"))
        primary_audit_lane = summary_builder.lane_by_name(audit, "primary")
        primary_audit_gate = primary_audit_lane.get("promotion_gate", {}) if isinstance(primary_audit_lane, dict) else {}
        ledger_path = BASE / str(primary.get("ledger_path") or "paper_trades/phase7_current_paper_paper_trade_settlements.csv")
        settlement_summary = summary_builder.summarize_settlement_csv(ledger_path)
        roi_complete_sources = consistency.get("primary_roi_complete_settled_rows", {})
        expected_roi_complete = int(roi_complete_sources.get("settlement_csv_recomputed", 0) or 0)
        checks.append(check(
            primary.get("settled") == primary_audit_lane.get("settled_outcome_rows")
            and primary.get("roi_complete_settled") == expected_roi_complete
            and primary.get("roi_complete_settled") == primary_audit_lane.get("roi_complete_settled_rows")
            and primary.get("roi_complete_settled") == roi_complete_sources.get("paper_trade_now"),
            "primary paper sample count is source-derived from top card, audit, and CSV recompute",
            f"primary={primary.get('roi_complete_settled')}; audit={primary_audit_lane.get('roi_complete_settled_rows')}; csv={expected_roi_complete}",
        ))
        expected_open = int(primary.get("open_settlements", 0) or 0)
        expected_incomplete = int(primary.get("incomplete_settlements", 0) or 0)
        expected_roi_gap = int(primary.get("roi_gap_settlements", 0) or 0)
        open_sources = consistency.get("primary_open_settlement_rows", {})
        incomplete_sources = consistency.get("primary_incomplete_settlement_rows", {})
        roi_gap_sources = consistency.get("primary_roi_gap_settlement_rows", {})
        settlement_queue_read = str(primary.get("settlement_queue_read") or "")
        recommendation_context = primary.get("recommendation_context", {}) if isinstance(primary.get("recommendation_context"), dict) else {}
        recommendation_read = str(recommendation_context.get("read") or "")
        latest_run_context = str(recommendation_context.get("latest_run_context") or "")
        best_action_for_queue = payload.get("current_paper_status", {}).get("best_action", {})
        source_best_action_for_queue = payload.get("current_paper_status", {}).get("source_best_action", {})
        requires_refresh_for_right_now = bool(payload.get("source_freshness", {}).get("requires_refresh_before_right_now_use"))
        best_action_command = str(best_action_for_queue.get("command") or "") if isinstance(best_action_for_queue, dict) else ""
        best_action_headline = str(best_action_for_queue.get("headline") or "") if isinstance(best_action_for_queue, dict) else ""
        source_best_action_command = str(source_best_action_for_queue.get("command") or "") if isinstance(source_best_action_for_queue, dict) else ""
        queue_source_matched = (
            open_sources.get("paper_trade_now") == expected_open
            and open_sources.get("settlement_audit") == expected_open
            and incomplete_sources.get("paper_trade_now") == expected_incomplete
            and incomplete_sources.get("settlement_audit") == expected_incomplete
            and roi_gap_sources.get("paper_trade_now") == expected_roi_gap
            and roi_gap_sources.get("settlement_audit") == expected_roi_gap
        )
        if expected_open > 0:
            queue_instruction_ok = (
                "settlement-queue work only" in settlement_queue_read
                and "result/payout evidence" in settlement_queue_read
                and "Open rows do not change" in settlement_queue_read
                and (
                    (
                        not requires_refresh_for_right_now
                        and "paper_trade_settlement_helper.py list-open" in best_action_command
                        and "Settle" in best_action_headline
                    )
                    or (
                        requires_refresh_for_right_now
                        and "run_daily_portfolio_observation.sh" in best_action_command
                        and (
                            "run_daily_portfolio_observation.sh" in source_best_action_command
                            or (
                                "paper_trade_settlement_helper.py list-open" in source_best_action_command
                                and bool(best_action_for_queue.get("source_action_overridden"))
                            )
                        )
                    )
                )
            )
        elif expected_incomplete or expected_roi_gap:
            queue_instruction_ok = "need repair before interpretation" in settlement_queue_read
        else:
            queue_instruction_ok = "queue cleanliness is operability metadata only" in settlement_queue_read
        checks.append(check(
            queue_source_matched and queue_instruction_ok,
            "primary settlement queue is source-matched and settlement-first unless source freshness requires wrapper refresh",
            f"open={expected_open}; incomplete={expected_incomplete}; roi_gap={expected_roi_gap}; requires_refresh={requires_refresh_for_right_now}; command={best_action_command}; source_command={source_best_action_command}",
        ))
        open_details = primary.get("open_settlement_row_details", [])
        audit_open_details = primary_audit_lane.get("open_settlement_row_details", [])
        open_summary = str(primary.get("open_settlement_summary") or "")
        audit_open_summary = str(primary_audit_lane.get("open_settlement_summary") or "")
        if expected_open > 0:
            open_detail_ok = (
                isinstance(open_details, list)
                and open_details == audit_open_details
                and len(open_details) == expected_open
                and open_summary == audit_open_summary
                and open_summary in settlement_queue_read
                and open_summary in markdown
                and all(
                    str(row.get("signal_key") or "")
                    and str(row.get("rule_id") or "")
                    and str(row.get("race_id") or "")
                    and str(row.get("key_program") or "")
                    for row in open_details
                    if isinstance(row, dict)
                )
            )
        else:
            open_detail_ok = open_details == audit_open_details and open_summary == audit_open_summary
        checks.append(check(
            open_detail_ok,
            "primary open settlement row details mirror the settlement audit without becoming performance evidence",
            f"open={expected_open}; summary={open_summary}",
        ))
        no_bet_latest_context = "no BET recommendations" in latest_run_context or "nothing reached a bet-ready state" in str(recommendation_context.get("ops_takeaway") or "")
        if no_bet_latest_context:
            recommendation_context_ok = (
                recommendation_context.get("latest_context_has_no_bet_recommendations") is True
                and recommendation_context.get("not_forward_performance_evidence") is True
                and recommendation_context.get("not_bet_readiness_evidence_by_itself") is True
                and "latest recommendation context is a qualifying scanner observation with no BET recommendation, not a bet-ready ticket" in recommendation_read
                and "latest open-row context" not in recommendation_read
                and "settle only from actual result/payout evidence" in recommendation_read
                and "Latest primary recommendation context: " + recommendation_read in markdown
                and recommendation_read in str(payload.get("summary", {}).get("current_read") or "")
            )
        else:
            recommendation_context_ok = (
                recommendation_context.get("not_forward_performance_evidence") is True
                and recommendation_context.get("not_bet_readiness_evidence_by_itself") is True
                and "Latest primary recommendation context: " + recommendation_read in markdown
                and ("operator context only" in recommendation_read or "do not treat the recommendation context itself as forward performance" in recommendation_read)
            )
        checks.append(check(
            recommendation_context_ok,
            "latest primary recommendation context separates recommendation-state routing from settlement rows, bet readiness, and forward evidence",
            f"latest_context={latest_run_context}; read={recommendation_read}",
        ))
        api_route_required = (
            "API-access-failure" in latest_run_context
            or "Sidecar action: refresh_daily_wrapper_before_evidence_read" in latest_run_context
            or "Recheck command: ./run_daily_portfolio_observation.sh" in latest_run_context
        )
        operator_read_gate = payload.get("operator_read_gate", {})
        api_route_ok = not api_route_required or (
            "Sidecar action: refresh_daily_wrapper_before_evidence_read." in latest_run_context
            and "Recheck command: ./run_daily_portfolio_observation.sh." in latest_run_context
            and "Sidecar action: refresh_daily_wrapper_before_evidence_read." in recommendation_read
            and "Recheck command: ./run_daily_portfolio_observation.sh." in recommendation_read
            and operator_read_gate.get("has_api_access_failure_context") is True
            and operator_read_gate.get("requires_refresh_before_evidence_read") is True
            and operator_read_gate.get("current_top_card_counts_as_no_target_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_clean_empty_evidence") is False
            and operator_read_gate.get("not_forward_performance_evidence") is True
            and "Operator read gate: " + str(operator_read_gate.get("read") or "") in markdown
            and str(operator_read_gate.get("read") or "") in str(payload.get("summary", {}).get("current_read") or "")
            and "Latest primary recommendation context: " + recommendation_read in markdown
            and recommendation_read in str(payload.get("summary", {}).get("current_read") or "")
            and "no-target, clean-empty, or forward-performance read" in recommendation_read
            and "Use recommendation and settlement ledgers before interpreting bet readiness or forward performance." in recommendation_read
        )
        checks.append(check(
            api_route_ok,
            "scanner/API-access recommendation context preserves sidecar action and wrapper recheck route",
            (
                f"required={api_route_required}; "
                f"has_action={'Sidecar action: refresh_daily_wrapper_before_evidence_read.' in recommendation_read}; "
                f"has_recheck={'Recheck command: ./run_daily_portfolio_observation.sh.' in recommendation_read}; "
                f"operator_read_gate={operator_read_gate}"
            ),
        ))
        checks.append(check(
            primary.get("hit_count") == settlement_summary["hit_count"]
            and primary.get("miss_count") == settlement_summary["miss_count"],
            "current settled outcomes match the primary settlement CSV recompute",
            f"hits={primary.get('hit_count')}; misses={primary.get('miss_count')}",
        ))
        checks.append(check(approx_equal(primary.get("hit_rate"), settlement_summary["hit_rate"]), "current observed hit rate is source-derived from settlement CSV"))
        checks.append(check(approx_equal(primary.get("flat_ticket_roi"), settlement_summary["flat_ticket_roi"]), "current observed flat-ticket ROI is source-derived from settlement CSV"))
        checks.append(check(
            approx_equal(primary.get("actual_cost_sum"), settlement_summary["actual_cost_sum"])
            and approx_equal(primary.get("actual_return_sum"), settlement_summary["actual_return_sum"]),
            "current cost/return sums match settlement CSV recompute",
        ))
        expected_primary_status_line = (
            f"- Current primary paper: `{primary['roi_complete_settled']}/{first_read.get('threshold')}` ROI-complete settled rows, "
            f"`{primary['open_settlements']}` open rows, `{primary['incomplete_settlements']}` incomplete rows, "
            f"hit rate `{summary_builder.pct(primary['hit_rate'])}`, flat-ticket ROI `{summary_builder.pct(primary['flat_ticket_roi'])}` "
            f"on {summary_builder.money(primary['actual_cost_sum'])} cost / {summary_builder.money(primary['actual_return_sum'])} return."
        )
        expected_primary_source_line = (
            f"- Primary ROI-complete rows: `PAPER_TRADE_NOW={roi_complete_sources['paper_trade_now']}`, "
            f"`settlement_audit={roi_complete_sources['settlement_audit']}`, "
            f"`csv_recomputed={roi_complete_sources['settlement_csv_recomputed']}`."
        )
        cost_return_sources = consistency.get("primary_cost_return_sums", {})
        expected_cost_return_line = (
            f"- Cost/return sums: audit {summary_builder.money(cost_return_sources['settlement_audit_cost'])} cost / "
            f"{summary_builder.money(cost_return_sources['settlement_audit_return'])} return; CSV recompute "
            f"{summary_builder.money(cost_return_sources['settlement_csv_cost'])} cost / "
            f"{summary_builder.money(cost_return_sources['settlement_csv_return'])} return."
        )
        checks.append(check(
            expected_primary_status_line in markdown
            and expected_primary_source_line in markdown
            and expected_cost_return_line in markdown,
            "markdown primary paper and source-consistency counts are source-derived",
            f"expected primary line={expected_primary_status_line}",
        ))
        checks.append(check(consistency.get("overall_match") is True, "source consistency says top card, audit, and CSV recompute agree"))
        freshness = payload.get("source_freshness", {})
        calendar_context = payload.get("calendar_context", {})
        refresh_boundary = (
            freshness.get("refresh_action_boundary")
            if isinstance(freshness.get("refresh_action_boundary"), dict)
            else {}
        )
        generated_date = str(freshness.get("generated_date") or "")
        generated_reference_date = str(freshness.get("generated_reference_date") or "")
        comparison_date = str(freshness.get("staleness_comparison_date") or "")
        source_as_of_date = str(freshness.get("right_now_as_of_date") or "")
        expected_stale_vs_generated = bool(comparison_date and source_as_of_date and source_as_of_date < comparison_date)
        expected_internal_stale = bool(freshness.get("right_now_internal_is_stale"))
        freshness_state = freshness.get("right_now_freshness_state")
        expected_state_valid = freshness_state in {"current_run_date", "stale_past_run", "future_run_date", "unknown_run_date"}
        expected_requires_refresh = expected_stale_vs_generated or expected_internal_stale or not expected_state_valid
        if not expected_state_valid:
            expected_refresh_reason = "right_now_freshness_state_missing_or_invalid"
        elif expected_internal_stale and expected_stale_vs_generated:
            expected_refresh_reason = "right_now_internal_and_source_stale"
        elif expected_internal_stale:
            expected_refresh_reason = "right_now_internal_stale"
        elif expected_stale_vs_generated:
            expected_refresh_reason = "source_as_of_older_than_bridge"
        else:
            expected_refresh_reason = "source_current_for_bridge"
        expected_internal_age_days = max(
            summary_builder.iso_date_delta_days(str(freshness.get("right_now_run_date") or ""), source_as_of_date) or 0,
            0,
        )
        expected_source_age_days = max(summary_builder.iso_date_delta_days(source_as_of_date, comparison_date) or 0, 0)
        expected_refresh_age_days = max(
            expected_internal_age_days if expected_internal_stale else 0,
            expected_source_age_days if expected_stale_vs_generated else 0,
            0,
        )
        checks.append(check(
            freshness.get("is_stale_vs_generated_date") is expected_stale_vs_generated
            and freshness.get("requires_refresh_before_right_now_use") is expected_requires_refresh
            and freshness.get("right_now_run_date")
            and source_as_of_date
            and generated_date,
            "source freshness compares right-now source date and internal stale card state to bridge reference date",
            f"as_of={source_as_of_date}; generated={generated_date}; reference={comparison_date}; expected_source_stale={expected_stale_vs_generated}; internal_stale={expected_internal_stale}",
        ))
        expected_driver_line = (
            f"- Stale versus bridge reference date: `{expected_stale_vs_generated}`; "
            f"refresh before right-now use: `{expected_requires_refresh}`."
        )
        expected_internal_stale_only_read = (
            not expected_stale_vs_generated
            and expected_internal_stale
            and "Right-now card is stale for its own as-of date" in str(freshness.get("read") or "")
            and "also older than bridge reference date" not in str(freshness.get("read") or "")
        )
        checks.append(check(
            freshness.get("requires_refresh_reason") == expected_refresh_reason
            and expected_driver_line in markdown
            and (
                not expected_requires_refresh
                or expected_stale_vs_generated
                or expected_internal_stale_only_read
                or not expected_state_valid
            ),
            "source freshness separates bridge-date freshness from internal stale-card refresh driver",
            (
                f"reason={freshness.get('requires_refresh_reason')}; expected={expected_refresh_reason}; "
                f"source_stale={expected_stale_vs_generated}; internal_stale={expected_internal_stale}; "
                f"driver_line={expected_driver_line}"
            ),
        ))
        expected_staleness_age_line = (
            f"- Staleness age: source-vs-bridge `{expected_source_age_days}` day(s); "
            f"right-now internal `{expected_internal_age_days}` day(s); "
            f"refresh age `{expected_refresh_age_days}` day(s)."
        )
        checks.append(check(
            freshness.get("right_now_internal_stale_age_days") == expected_internal_age_days
            and freshness.get("source_stale_age_days_vs_bridge") == expected_source_age_days
            and freshness.get("refresh_age_days") == expected_refresh_age_days
            and expected_staleness_age_line in markdown,
            "source freshness publishes structured staleness age without changing evidence class",
            expected_staleness_age_line,
        ))
        checks.append(check(
            refresh_boundary.get("command") == "./run_daily_portfolio_observation.sh"
            and refresh_boundary.get("required_before_right_now_instruction_use") is expected_requires_refresh
            and refresh_boundary.get("source_action_counts_as_current_instruction_before_refresh") is (not expected_requires_refresh)
            and refresh_boundary.get("wrapper_refresh_can_update_operator_surfaces") is True
            and refresh_boundary.get("wrapper_refresh_can_settle_open_rows_by_itself") is False
            and refresh_boundary.get("wrapper_refresh_counts_as_roi_complete_evidence_by_itself") is False
            and refresh_boundary.get("clean_empty_refresh_counts_as_forward_performance") is False
            and refresh_boundary.get("missing_or_invalid_artifact_counts_as_clean_quiet_day") is False
            and refresh_boundary.get("not_forward_performance_evidence") is True
            and refresh_boundary.get("not_promotion_readiness_evidence") is True
            and refresh_boundary.get("not_live_profitability_evidence") is True
            and refresh_boundary.get("not_real_money_evidence") is True
            and "wrapper refresh can update operator surfaces" in str(refresh_boundary.get("read") or "")
            and "by itself it does not settle open rows" in str(refresh_boundary.get("read") or "")
            and str(refresh_boundary.get("read") or "") in markdown,
            "source freshness publishes wrapper-refresh boundary without turning reruns into evidence",
            str(refresh_boundary),
        ))
        expected_refresh_text_fields = set(summary_builder.REFRESH_ACTION_BOUNDARY_TEXT_FIELDS)
        expected_refresh_bool_fields = set(summary_builder.REFRESH_ACTION_BOUNDARY_BOOL_FIELDS)
        actual_refresh_fields = set(refresh_boundary)
        missing_refresh_text_fields = sorted(expected_refresh_text_fields - actual_refresh_fields)
        missing_refresh_bool_fields = sorted(expected_refresh_bool_fields - actual_refresh_fields)
        non_text_refresh_fields = sorted(
            field
            for field in expected_refresh_text_fields
            if not isinstance(refresh_boundary.get(field), str) or not str(refresh_boundary.get(field)).strip()
        )
        non_bool_refresh_fields = sorted(
            field
            for field in expected_refresh_bool_fields
            if not isinstance(refresh_boundary.get(field), bool)
        )
        checks.append(check(
            not missing_refresh_text_fields
            and not missing_refresh_bool_fields
            and not non_text_refresh_fields
            and not non_bool_refresh_fields
            and set(summary_builder.REFRESH_ACTION_BOUNDARY_TEXT_FIELDS) == {
                "command",
                "valid_use",
                "read",
            }
            and set(summary_builder.REFRESH_ACTION_BOUNDARY_BOOL_FIELDS) == {
                "required_before_right_now_instruction_use",
                "source_action_counts_as_current_instruction_before_refresh",
                "wrapper_refresh_can_update_operator_surfaces",
                "wrapper_refresh_can_settle_open_rows_by_itself",
                "wrapper_refresh_counts_as_roi_complete_evidence_by_itself",
                "clean_empty_refresh_counts_as_forward_performance",
                "missing_or_invalid_artifact_counts_as_clean_quiet_day",
                "not_forward_performance_evidence",
                "not_promotion_readiness_evidence",
                "not_live_profitability_evidence",
                "not_real_money_evidence",
            },
            "refresh_action_boundary_schema_fields_are_complete_and_typed",
            (
                f"missing_text={missing_refresh_text_fields}; missing_bool={missing_refresh_bool_fields}; "
                f"non_text={non_text_refresh_fields}; non_bool={non_bool_refresh_fields}"
            ),
        ))
        checks.append(check(
            generated_reference_date
            and freshness.get("generated_reference_timezone") == "America/New_York"
            and comparison_date == generated_reference_date
            and freshness.get("staleness_comparison_source") == "generated_reference_date"
            and freshness.get("not_forward_performance_evidence") is True
            and calendar_context.get("generated_local_date") == generated_date
            and calendar_context.get("generated_reference_date") == generated_reference_date
            and calendar_context.get("generated_reference_timezone") == "America/New_York"
            and calendar_context.get("right_now_run_date") == freshness.get("right_now_run_date")
            and calendar_context.get("right_now_as_of_date") == source_as_of_date
            and calendar_context.get("staleness_comparison_date") == comparison_date
            and calendar_context.get("staleness_comparison_source") == "generated_reference_date"
            and calendar_context.get("requires_refresh_before_right_now_use") is expected_requires_refresh
            and calendar_context.get("not_forward_performance_evidence") is True
            and calendar_context.get("not_live_profitability_evidence") is True
            and calendar_context.get("not_promotion_readiness_evidence") is True
            and calendar_context.get("not_real_money_evidence") is True
            and str(calendar_context.get("read") or "") in markdown,
            "calendar context exposes New York reference date without changing evidence class",
            f"generated={generated_date}; reference={generated_reference_date}; comparison={comparison_date}; calendar={calendar_context}",
        ))
        checks.append(check(
            freshness.get("right_now_freshness_state_valid") is expected_state_valid
            and freshness_state == payload.get("current_paper_status", {}).get("run_freshness", {}).get("freshness_state"),
            "source freshness preserves structured right-now freshness_state",
            f"state={freshness_state}; valid={freshness.get('right_now_freshness_state_valid')}",
        ))
        freshness_read = str(freshness.get("read") or "")
        checks.append(check(
            (
                "refresh `./run_daily_portfolio_observation.sh` before treating the best-action card as today's operator instruction" in freshness_read
                if expected_requires_refresh
                else "report/navigation context rather than performance evidence" in freshness_read
            ),
            "source freshness gives the correct operator-readiness instruction",
            freshness_read,
        ))
        expected_reason = (
            "right_now_internal_and_source_stale" if expected_internal_stale and expected_stale_vs_generated
            else "right_now_internal_stale" if expected_internal_stale
            else "source_as_of_older_than_bridge" if expected_stale_vs_generated
            else "right_now_freshness_state_missing_or_invalid" if not expected_state_valid
            else "source_current_for_bridge"
        )
        checks.append(check(
            freshness.get("requires_refresh_reason") == expected_reason,
            "source freshness reason separates internal staleness, date-rollover staleness, combined stale state, and missing freshness_state",
            f"expected={expected_reason}; actual={freshness.get('requires_refresh_reason')}",
        ))
        best_action = payload.get("current_paper_status", {}).get("best_action", {})
        checks.append(check(
            stale_best_action_command_ok(payload),
            "stale source freshness forces the best-action command to the daily wrapper",
            f"requires_refresh={freshness.get('requires_refresh_before_right_now_use')}; command={best_action.get('command') if isinstance(best_action, dict) else None}",
        ))
        checks.append(check(
            roi_complete_sources.get("paper_trade_now") == primary.get("roi_complete_settled")
            and roi_complete_sources.get("settlement_audit") == primary_audit_lane.get("roi_complete_settled_rows")
            and roi_complete_sources.get("settlement_csv_recomputed") == settlement_summary["roi_complete_rows_from_csv"],
            "primary ROI-complete count is cross-checked across top card, audit, and CSV recompute",
            str(roi_complete_sources),
        ))
        checks.append(check(
            approx_equal(cost_return_sources.get("settlement_audit_cost"), primary_audit_lane.get("roi_complete_cost_sum"))
            and approx_equal(cost_return_sources.get("settlement_csv_cost"), settlement_summary["actual_cost_sum"])
            and approx_equal(cost_return_sources.get("settlement_audit_return"), primary_audit_lane.get("roi_complete_return_sum"))
            and approx_equal(cost_return_sources.get("settlement_csv_return"), settlement_summary["actual_return_sum"]),
            "primary cost/return sums are cross-checked between settlement audit and CSV recompute",
        ))
        timestamp_gap_sources = consistency.get("primary_settled_ts_gap_rows", {})
        audit_ts_reason_counts = {
            str(reason): int(count or 0)
            for reason, count in (primary_audit_lane.get("roi_gap_reason_counts", {}).items() if isinstance(primary_audit_lane.get("roi_gap_reason_counts"), dict) else [])
            if "settled_ts" in str(reason)
        }
        checks.append(check(
            timestamp_gap_sources.get("settlement_audit") == sum(audit_ts_reason_counts.values())
            and timestamp_gap_sources.get("settlement_csv_recomputed") == settlement_summary["settled_ts_gap_rows_from_csv"]
            and consistency.get("primary_settled_ts_gap_reason_counts", {}).get("settlement_audit") == audit_ts_reason_counts
            and consistency.get("primary_settled_ts_gap_reason_counts", {}).get("settlement_csv_recomputed") == settlement_summary["settled_ts_gap_reason_counts"],
            "primary settled_ts gaps are cross-checked between settlement audit and CSV recompute",
            str(consistency.get("primary_settled_ts_gap_reason_counts", {})),
        ))
        upstream = consistency.get("settlement_audit_upstream_sources", {})
        audit_source_files = audit.get("source_files", {}) if isinstance(audit.get("source_files"), dict) else {}
        expected_upstream_labels = list(summary_builder.EXPECTED_AUDIT_UPSTREAM_SOURCE_LABELS)
        upstream_details: list[str] = []
        upstream_disk_ok = True
        for label in expected_upstream_labels:
            fp = audit_source_files.get(label, {})
            ok, detail = audit_upstream_fingerprint_matches_disk(fp) if isinstance(fp, dict) else (False, f"not dict: {fp}")
            upstream_disk_ok = upstream_disk_ok and ok
            upstream_details.append(f"{label}: {detail}")
        checks.append(check(
            upstream.get("all_match") is True
            and upstream.get("not_forward_performance_evidence") is True
            and upstream.get("expected_labels") == expected_upstream_labels
            and set(upstream.get("labels", [])) == set(expected_upstream_labels)
            and upstream.get("missing_labels") == []
            and upstream.get("malformed_labels") == []
            and upstream.get("drifted_labels") == []
            and upstream.get("matching_count") == upstream.get("expected_count") == len(expected_upstream_labels)
            and upstream.get("source_files") == audit_source_files
            and upstream_disk_ok
            and str(upstream.get("read") or "") in markdown,
            "settlement-audit upstream source fingerprints match scorecard/rules/signals/settlements on disk",
            " | ".join(upstream_details),
        ))
        primary_rule_progress = {
            str(row.get("rule_id")): int(row.get("roi_complete_settled_rows", 0) or 0)
            for row in primary.get("rule_progress", [])
        }
        expected_primary_rule_progress = {
            str(row.get("rule_id")): int(row.get("roi_complete_settled_rows", 0) or 0)
            for row in primary_audit_gate.get("rule_progress", [])
        }
        op_primary_rows = expected_primary_rule_progress.get("OP_DURABLE_K7", 0)
        cd_primary_rows = expected_primary_rule_progress.get("CD_CORE_K8", 0)
        if op_primary_rows == 0 and cd_primary_rows > 0:
            expected_rule_context = "Current settled paper context is CD-only, so it should not be counted as OP-anchor forward evidence."
        elif op_primary_rows > 0 and cd_primary_rows == 0:
            expected_rule_context = "Current settled paper context is OP-only; keep CD companion reads separate until CD has ROI-complete rows."
        elif op_primary_rows > 0 and cd_primary_rows > 0:
            expected_rule_context = "Current settled paper context spans OP and CD; keep OP-anchor and CD-companion reads rule-specific."
        else:
            expected_rule_context = "Current primary paper has no ROI-complete rule-specific settled rows yet."
        expected_rule_mix_read = (
            f"Primary rule mix: OP_DURABLE_K7 has {op_primary_rows} ROI-complete settled row(s); "
            f"CD_CORE_K8 has {cd_primary_rows}. {expected_rule_context}"
        )
        rule_mix_read = primary.get("rule_mix_read", "")
        checks.append(check(
            primary_rule_progress == expected_primary_rule_progress
            and rule_mix_read == expected_rule_mix_read
            and expected_rule_mix_read in markdown,
            "primary rule mix read is source-derived from settlement-audit per-rule coverage",
            f"expected={expected_rule_mix_read}; actual={rule_mix_read}",
        ))
        anchor_gap = primary.get("anchor_settlement_gap", {}) if isinstance(primary.get("anchor_settlement_gap"), dict) else {}
        anchor_review_threshold = int(
            payload.get("decision_gate_minimums", {}).get("anchor_displacement_min_roi_complete_settled_observations")
            or first_read.get("threshold")
            or 30
        )
        expected_anchor_gap_read = (
            f"OP-anchor settlement gap: OP_DURABLE_K7 has {op_primary_rows} ROI-complete settled row(s); "
            f"CD_CORE_K8 has {cd_primary_rows}. "
            f"Need {max(anchor_review_threshold - op_primary_rows, 0)} more OP_DURABLE_K7 ROI-complete row(s) before the "
            f"{anchor_review_threshold}-row same-candidate anchor-review floor is even count-complete. "
            "CD companion rows do not reduce that OP-anchor gap."
        )
        checks.append(check(
            anchor_gap.get("anchor_rule_id") == "OP_DURABLE_K7"
            and anchor_gap.get("companion_rule_id") == "CD_CORE_K8"
            and anchor_gap.get("anchor_roi_complete_settled_rows") == op_primary_rows
            and anchor_gap.get("companion_roi_complete_settled_rows") == cd_primary_rows
            and anchor_gap.get("lane_roi_complete_settled_rows") == primary.get("roi_complete_settled")
            and anchor_gap.get("open_settlement_rows") == expected_open
            and anchor_gap.get("same_candidate_anchor_review_floor") == anchor_review_threshold
            and anchor_gap.get("anchor_rows_needed_for_same_candidate_review") == max(anchor_review_threshold - op_primary_rows, 0)
            and anchor_gap.get("anchor_specific_review_ready") is (op_primary_rows >= anchor_review_threshold)
            and anchor_gap.get("current_sample_is_cd_only") is (op_primary_rows == 0 and cd_primary_rows > 0)
            and anchor_gap.get("companion_rows_count_as_anchor_evidence") is False
            and anchor_gap.get("not_forward_performance_evidence") is True
            and anchor_gap.get("not_promotion_readiness_evidence") is True
            and anchor_gap.get("not_live_profitability_evidence") is True
            and anchor_gap.get("not_real_money_evidence") is True
            and anchor_gap.get("read") == expected_anchor_gap_read
            and expected_anchor_gap_read in markdown
            and expected_anchor_gap_read in str(payload.get("summary", {}).get("current_read") or ""),
            "OP-anchor settlement gap keeps CD companion rows out of the OP-anchor evidence count",
            expected_anchor_gap_read,
        ))
        open_queue = (
            primary.get("open_settlement_queue_by_rule")
            if isinstance(primary.get("open_settlement_queue_by_rule"), dict)
            else {}
        )
        expected_open_rule_counts: dict[str, int] = {}
        for row in open_details:
            if not isinstance(row, dict):
                continue
            rule_id = str(row.get("rule_id") or "").strip() or "UNKNOWN"
            expected_open_rule_counts[rule_id] = expected_open_rule_counts.get(rule_id, 0) + 1
        expected_open_rule_counts.setdefault("OP_DURABLE_K7", 0)
        expected_open_rule_counts.setdefault("CD_CORE_K8", 0)
        expected_open_rule_counts = dict(sorted(expected_open_rule_counts.items()))
        expected_open_rows_with_rule_id = sum(expected_open_rule_counts.values())
        expected_open_rows_without_rule_id = max(expected_open - expected_open_rows_with_rule_id, 0)
        expected_other_open_rows = sum(
            count
            for rule_id, count in expected_open_rule_counts.items()
            if rule_id not in {"OP_DURABLE_K7", "CD_CORE_K8"}
        )
        expected_open_queue_state = "closed" if expected_open == 0 else "open"
        expected_open_queue_context = "no open primary settlement rows" if expected_open == 0 else open_summary
        expected_open_queue_detail_read = (
            f"Open settlement queue by rule: OP_DURABLE_K7 has {expected_open_rule_counts.get('OP_DURABLE_K7', 0)} open row(s); "
            f"CD_CORE_K8 has {expected_open_rule_counts.get('CD_CORE_K8', 0)}; other primary rules have {expected_other_open_rows}; "
            f"{expected_open_rows_without_rule_id} open row(s) lack published rule IDs. "
            "Open rows are settlement workflow only and do not count as ROI-complete rows or OP-anchor evidence."
        )
        expected_open_queue_read = (
            f"Settlement queue state: {expected_open_queue_state}; {expected_open_queue_context}; detail: "
            f"{expected_open_queue_detail_read}"
        )
        checks.append(check(
            open_queue.get("anchor_rule_id") == "OP_DURABLE_K7"
            and open_queue.get("companion_rule_id") == "CD_CORE_K8"
            and open_queue.get("open_rows_by_rule") == expected_open_rule_counts
            and open_queue.get("total_open_rows") == expected_open
            and open_queue.get("published_open_row_detail_count") == len(open_details)
            and open_queue.get("open_rows_with_published_rule_id") == expected_open_rows_with_rule_id
            and open_queue.get("open_rows_without_published_rule_id") == expected_open_rows_without_rule_id
            and open_queue.get("anchor_open_rows") == expected_open_rule_counts.get("OP_DURABLE_K7", 0)
            and open_queue.get("companion_open_rows") == expected_open_rule_counts.get("CD_CORE_K8", 0)
            and open_queue.get("other_open_rule_rows") == expected_other_open_rows
            and open_queue.get("open_settlement_queue_state") == expected_open_queue_state
            and open_queue.get("open_settlement_context") == expected_open_queue_context
            and open_queue.get("detail_read") == expected_open_queue_detail_read
            and open_queue.get("current_open_queue_is_cd_only") is (
                expected_open_rule_counts.get("OP_DURABLE_K7", 0) == 0
                and expected_open_rule_counts.get("CD_CORE_K8", 0) > 0
                and expected_other_open_rows == 0
            )
            and open_queue.get("open_rows_count_as_roi_complete") is False
            and open_queue.get("open_rows_count_as_anchor_evidence") is False
            and open_queue.get("not_forward_performance_evidence") is True
            and open_queue.get("not_promotion_readiness_evidence") is True
            and open_queue.get("not_live_profitability_evidence") is True
            and open_queue.get("not_real_money_evidence") is True
            and open_queue.get("read") == expected_open_queue_read
            and expected_open_queue_read in markdown
            and expected_open_queue_read in str(payload.get("summary", {}).get("current_read") or ""),
            "open settlement queue state/by rule keeps source-published queue detail as settlement workflow rather than OP-anchor evidence",
            expected_open_queue_read,
        ))
        checks.append(check(
            first_read.get("threshold") == primary_audit_gate.get("min_roi_complete_settled_lane_total")
            and first_read.get("current") == primary_audit_gate.get("active_first_read_count")
            and first_read.get("remaining") == max(int(first_read.get("threshold", 0) or 0) - int(first_read.get("current", 0) or 0), 0)
            and first_read.get("ready") is (int(first_read.get("current", 0) or 0) >= int(first_read.get("threshold", 0) or 0)),
            "first-read gate is source-derived from the primary anchor_displacement audit gate",
            str(first_read),
        ))
        checks.append(check(
            portfolio_review.get("threshold") == primary_audit_gate.get("portfolio_review_settled_lane_total")
            and portfolio_review.get("current") == primary_audit_gate.get("active_first_read_count")
            and portfolio_review.get("remaining") == max(int(portfolio_review.get("threshold", 0) or 0) - int(portfolio_review.get("current", 0) or 0), 0)
            and portfolio_review.get("ready") is (int(portfolio_review.get("current", 0) or 0) >= int(portfolio_review.get("threshold", 0) or 0)),
            "portfolio-review gate is source-derived from the primary audit gate",
            str(portfolio_review),
        ))

        shadow_status = payload.get("current_paper_status", {}).get("shadow", {})
        shadow_audit_lane = summary_builder.lane_by_name(audit, "shadow")
        shadow_audit_gate = shadow_audit_lane.get("promotion_gate", {}) if isinstance(shadow_audit_lane, dict) else {}
        expected_rule_progress = shadow_audit_gate.get("rule_progress", []) if isinstance(shadow_audit_gate, dict) else []
        expected_rule_progress_read = render_shadow_rule_progress(expected_rule_progress)
        rule_progress = shadow_status.get("rule_progress", [])
        weakest_shadow = min((int(row.get("roi_complete_settled_rows", 0) or 0) for row in rule_progress), default=0)
        checks.append(check(
            shadow_status.get("roi_complete_settled") == shadow_audit_lane.get("roi_complete_settled_rows")
            and weakest_shadow == shadow_audit_gate.get("active_first_read_count")
            and shadow_audit_gate.get("active_first_read_min_settled") == 20,
            "shadow promotion coverage is sourced from the settlement-audit per-rule gate",
            f"bridge_lane_total={shadow_status.get('roi_complete_settled')}; audit_lane_total={shadow_audit_lane.get('roi_complete_settled_rows')}; weakest_rule={weakest_shadow}; audit_gate={shadow_audit_gate.get('active_first_read_progress')}",
        ))
        shadow_gate_read = str(shadow_status.get("promotion_gate_read") or "")
        current_read = str(payload.get("summary", {}).get("current_read") or "")
        review_floor_bits = [
            "20-row count is a review floor, not a promotion entitlement",
            "scorecard tiers remain binding",
            "negative-holdout/SKIP rules still need cleaner split-aware evidence",
        ]
        checks.append(check(
            all(bit in shadow_gate_read for bit in review_floor_bits)
            and all(bit in current_read for bit in review_floor_bits),
            "current bridge carries Phase 8 shadow review-floor and scorecard-tier caution",
            shadow_gate_read,
        ))
        shadow_rule_progress_read = str(shadow_status.get("rule_progress_read") or "")
        checks.append(check(
            expected_rule_progress_read
            and shadow_rule_progress_read == expected_rule_progress_read
            and expected_rule_progress_read in markdown
            and compact_shadow_rule_progress(rule_progress) == compact_shadow_rule_progress(expected_rule_progress),
            "current bridge mirrors settlement-audit per-rule Phase 8 shadow tier/progress coverage",
            f"expected={expected_rule_progress_read}; actual={shadow_rule_progress_read}",
        ))

        gates = payload.get("decision_gate_minimums", {})
        checks.append(check(gates.get("anchor_displacement_min_roi_complete_settled_observations") == 30, "anchor-displacement gate is 30 ROI-complete observations"))
        checks.append(check(gates.get("phase8_promotion_review_min_roi_complete_settled_observations") == 20, "Phase 8 review gate is 20 per candidate"))
        checks.append(check(gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") == 100, "real-money discussion gate is 100 usable-ROI observations"))
        expected_gate_values = {
            "anchor_displacement_min_roi_complete_settled_observations": 30,
            "phase8_promotion_review_min_roi_complete_settled_observations": 20,
            "real_money_discussion_min_total_settled_observations_with_usable_roi": 100,
        }
        expected_threshold_sources = {
            "anchor_displacement": "forward_evidence_scorecard.json:decision_gate_minimums.anchor_displacement.min_roi_complete_settled_observations",
            "phase8_promotion_review": "forward_evidence_scorecard.json:decision_gate_minimums.phase8_promotion_review.min_roi_complete_settled_observations",
            "real_money_discussion": "forward_evidence_scorecard.json:decision_gate_minimums.real_money_discussion.min_total_settled_observations_with_usable_roi",
        }
        checks.append(check(
            gates.get("source_values_match_scorecard") is True
            and gates.get("top_card_values") == expected_gate_values
            and gates.get("scorecard_values") == expected_gate_values
            and gates.get("effective_values") == expected_gate_values
            and gates.get("effective_values_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and gates.get("threshold_sources") == expected_threshold_sources
            and gates.get("real_money_discussion_also_requires") == [
                "positive paper ROI",
                "concentration checks",
                "payout-distribution sanity checks",
                "no BAQ-as-BEL substitution",
            ]
            and gates.get("real_money_no_baq_as_bel_required") is True
            and gates.get("mismatched_fields") == []
            and gates.get("missing_top_card_fields") == []
            and "Gate source alignment: `True`" in markdown
            and "Canonical gate values used by the bridge: anchor `30`; Phase 8 `20`; real-money `100`" in markdown
            and "Real-money prerequisites: `positive paper ROI; concentration checks; payout-distribution sanity checks; no BAQ-as-BEL substitution`; no-BAQ-as-BEL required = `True`" in markdown
            and all(source in markdown for source in expected_threshold_sources.values()),
            "decision-gate minimums are source-matched to exact scorecard JSON keys",
            f"top_card={gates.get('top_card_values')}; scorecard={gates.get('scorecard_values')}; sources={gates.get('threshold_sources')}",
        ))
        scorecard_audit_route = payload.get("scorecard_audit_route", {})
        expected_audit_route_read = (
            "Use `SCORECARD_RANKING_CONTRACT_AUDIT.md` / `scorecard_ranking_contract_audit.json` plus "
            "`python3 validate_scorecard_ranking_contract_audit.py` to check copied 30/20/100 gate floors, "
            "tier-first ranking, OP_REFINED CI-only support context, generated-at timezone provenance, and "
            "no-BAQ-as-BEL prerequisite drift across report-facing surfaces."
        )
        expected_audit_gate_floor_snapshot = {
            **expected_gate_values,
            "real_money_no_baq_as_bel_required": True,
        }
        checks.append(check(
            scorecard_audit_route.get("markdown_path") == "SCORECARD_RANKING_CONTRACT_AUDIT.md"
            and scorecard_audit_route.get("json_path") == "scorecard_ranking_contract_audit.json"
            and scorecard_audit_route.get("validator_command") == "python3 validate_scorecard_ranking_contract_audit.py"
            and scorecard_audit_route.get("gate_floor_source") == "forward_evidence_scorecard.json:decision_gate_minimums"
            and scorecard_audit_route.get("gate_floor_snapshot") == expected_audit_gate_floor_snapshot
            and scorecard_audit_route.get("route_read") == expected_audit_route_read
            and scorecard_audit_route.get("artifacts_present") is True
            and scorecard_audit_route.get("not_forward_performance_evidence") is True
            and scorecard_audit_route.get("not_settled_roi_evidence") is True
            and scorecard_audit_route.get("not_promotion_readiness_evidence") is True
            and scorecard_audit_route.get("not_live_profitability_evidence") is True
            and scorecard_audit_route.get("not_bankroll_guidance") is True
            and scorecard_audit_route.get("not_real_money_evidence") is True
            and expected_audit_route_read in markdown
            and expected_audit_route_read in str(payload.get("summary", {}).get("current_read") or "")
            and "Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`):" in markdown
            and "Scorecard audit route (`current_evidence_summary.json.scorecard_audit_route`):" in str(payload.get("summary", {}).get("current_read") or "")
            and "This route is synchronization metadata only, not current paper evidence." in markdown,
            "current bridge routes copied gate/ranking/CI-only/timezone/no-BAQ drift checks to the scorecard audit",
            str(scorecard_audit_route),
        ))
        gate_progress = payload.get("decision_gate_progress", {}) if isinstance(payload.get("decision_gate_progress"), dict) else {}
        expected_primary_threshold = int(first_read.get("threshold") or 30)
        expected_phase8_threshold = int(gates.get("phase8_promotion_review_min_roi_complete_settled_observations") or 20)
        expected_real_money_threshold = int(gates.get("real_money_discussion_min_total_settled_observations_with_usable_roi") or 100)
        expected_shadow_gate_rows = []
        for row in expected_rule_progress:
            if not isinstance(row, dict):
                continue
            current_rows = int(row.get("roi_complete_settled_rows", 0) or 0)
            expected_shadow_gate_rows.append(
                {
                    "rule_id": str(row.get("rule_id") or ""),
                    "scorecard_tier": row.get("scorecard_tier"),
                    "current_rows": current_rows,
                    "threshold": expected_phase8_threshold,
                    "remaining": max(expected_phase8_threshold - current_rows, 0),
                    "ready": current_rows >= expected_phase8_threshold,
                    "promotion_progress": row.get("promotion_progress"),
                }
            )
        expected_weakest_shadow_rows = min((row["current_rows"] for row in expected_shadow_gate_rows), default=0)
        expected_weakest_shadow_rule_ids = [
            row["rule_id"]
            for row in expected_shadow_gate_rows
            if row["current_rows"] == expected_weakest_shadow_rows
        ]
        expected_primary_gate_read = (
            f"Primary first-read gate: {primary.get('roi_complete_settled')}/{expected_primary_threshold} "
            f"ROI-complete primary rows; {max(expected_primary_threshold - int(primary.get('roi_complete_settled', 0) or 0), 0)} more needed."
        )
        expected_phase8_gate_read = (
            f"Phase 8 promotion-review gate: weakest current shadow coverage is {expected_weakest_shadow_rows}/{expected_phase8_threshold} "
            f"for {', '.join(expected_weakest_shadow_rule_ids) if expected_weakest_shadow_rule_ids else 'no published shadow rows'}; "
            "the floor is per candidate and is not a promotion entitlement."
        )
        expected_real_money_read = (
            f"Real-money discussion floor: primary bridge currently has {primary.get('roi_complete_settled')}/{expected_real_money_threshold} "
            "ROI-complete rows, before concentration, payout-distribution, positive-ROI, and no-BAQ-as-BEL prerequisites."
        )
        expected_gate_progress_read = (
            f"Gate progress: primary first-read {primary.get('roi_complete_settled')}/{expected_primary_threshold}; "
            f"OP anchor same-candidate {op_primary_rows}/{anchor_review_threshold}; "
            f"Phase 8 weakest shadow {expected_weakest_shadow_rows}/{expected_phase8_threshold}; "
            f"real-money discussion floor {primary.get('roi_complete_settled')}/{expected_real_money_threshold}. "
            "All remain uncleared and are routing context only."
        )
        checks.append(check(
            gate_progress.get("source_path") == "forward_evidence_scorecard.json"
            and gate_progress.get("source_json_path") == "decision_gate_minimums"
            and gate_progress.get("valid_use") == "machine-readable current gate progress for report routing and no-overclaim checks"
            and gate_progress.get("not_forward_performance_evidence") is True
            and gate_progress.get("not_promotion_readiness_evidence") is True
            and gate_progress.get("not_live_profitability_evidence") is True
            and gate_progress.get("not_real_money_evidence") is True
            and gate_progress.get("gate_status") == "all_uncleared"
            and gate_progress.get("all_gates_ready") is False
            and gate_progress.get("read") == expected_gate_progress_read
            and expected_gate_progress_read in str(payload.get("summary", {}).get("current_read") or ""),
            "decision-gate progress block publishes current 30/20/100 readiness as non-evidence routing metadata",
            gate_progress.get("read"),
        ))
        primary_gate_progress = gate_progress.get("primary_first_read", {})
        anchor_gate_progress = gate_progress.get("op_anchor_same_candidate_review", {})
        phase8_gate_progress = gate_progress.get("phase8_promotion_review", {})
        real_money_gate_progress = gate_progress.get("real_money_discussion", {})
        checks.append(check(
            primary_gate_progress.get("gate_source") == "anchor_displacement"
            and primary_gate_progress.get("current_rows") == primary.get("roi_complete_settled")
            and primary_gate_progress.get("threshold") == expected_primary_threshold
            and primary_gate_progress.get("remaining") == max(expected_primary_threshold - int(primary.get("roi_complete_settled", 0) or 0), 0)
            and primary_gate_progress.get("ready") is False
            and primary_gate_progress.get("rows_counted") == "primary ROI-complete settled rows"
            and primary_gate_progress.get("read") == expected_primary_gate_read
            and expected_primary_gate_read in markdown,
            "decision-gate progress primary first-read mirrors source primary ROI-complete count",
            str(primary_gate_progress),
        ))
        checks.append(check(
            anchor_gate_progress.get("gate_source") == "anchor_displacement"
            and anchor_gate_progress.get("candidate_rule_id") == "OP_DURABLE_K7"
            and anchor_gate_progress.get("current_rows") == op_primary_rows
            and anchor_gate_progress.get("threshold") == anchor_review_threshold
            and anchor_gate_progress.get("remaining") == max(anchor_review_threshold - op_primary_rows, 0)
            and anchor_gate_progress.get("ready") is (op_primary_rows >= anchor_review_threshold)
            and anchor_gate_progress.get("companion_rule_id") == "CD_CORE_K8"
            and anchor_gate_progress.get("companion_rows") == cd_primary_rows
            and anchor_gate_progress.get("companion_rows_count_as_anchor_evidence") is False
            and anchor_gate_progress.get("read") == expected_anchor_gap_read
            and "OP same-candidate anchor review:" in markdown
            and "companion rows count as anchor evidence = `False`" in markdown,
            "decision-gate progress keeps OP-anchor same-candidate gate separate from CD companion rows",
            str(anchor_gate_progress),
        ))
        checks.append(check(
            phase8_gate_progress.get("gate_source") == "phase8_promotion_review"
            and phase8_gate_progress.get("threshold_per_candidate") == expected_phase8_threshold
            and phase8_gate_progress.get("weakest_current_rows") == expected_weakest_shadow_rows
            and phase8_gate_progress.get("weakest_rule_ids") == expected_weakest_shadow_rule_ids
            and phase8_gate_progress.get("ready") is False
            and phase8_gate_progress.get("per_rule") == expected_shadow_gate_rows
            and phase8_gate_progress.get("read") == expected_phase8_gate_read
            and expected_phase8_gate_read in markdown,
            "decision-gate progress publishes per-rule Phase 8 weakest shadow coverage instead of lane-total promotion",
            str(phase8_gate_progress),
        ))
        checks.append(check(
            real_money_gate_progress.get("gate_source") == "real_money_discussion"
            and real_money_gate_progress.get("current_primary_roi_complete_rows") == primary.get("roi_complete_settled")
            and real_money_gate_progress.get("threshold") == expected_real_money_threshold
            and real_money_gate_progress.get("remaining_against_primary_review") == max(expected_real_money_threshold - int(primary.get("roi_complete_settled", 0) or 0), 0)
            and real_money_gate_progress.get("ready") is False
            and real_money_gate_progress.get("also_requires") == gates.get("real_money_discussion_also_requires")
            and real_money_gate_progress.get("no_baq_as_bel_required") is True
            and real_money_gate_progress.get("read") == expected_real_money_read
            and expected_real_money_read in markdown,
            "decision-gate progress keeps real-money discussion behind 100-row plus prerequisite floor",
            str(real_money_gate_progress),
        ))

        do_not_do = set(payload.get("do_not_do", []))
        checks.append(check(REQUIRED_DO_NOT_DO.issubset(do_not_do), "do-not-do list blocks promotion, BAQ/BEL, XGBoost, and real-money shortcuts"))
        expected_sample_caution = (
            f"do not treat {primary.get('roi_complete_settled')} settled misses as promotion-grade forward evidence"
            if primary.get("roi_complete_settled") == settlement_summary["miss_count"] and settlement_summary["hit_count"] == 0
            else f"do not treat the {primary.get('roi_complete_settled')} ROI-complete settled-row sample as promotion-grade forward evidence"
        )
        checks.append(check(
            expected_sample_caution in do_not_do
            and f"- {expected_sample_caution}" in markdown,
            "do-not-do sample caution is source-derived from current settled outcomes",
            expected_sample_caution,
        ))

        excluded = payload.get("current_paper_status", {}).get("preflight_excluded_track_summary")
        checks.append(check(excluded == "BAQ (not treated as BEL)", "BAQ is explicitly not treated as BEL"))

        contract = payload.get("rebuild_validation_contract", {})
        expected_upstream_refresh_order = [
            {
                "order": 1,
                "command": "python3 paper_trade_settlement_audit.py",
                "reason": (
                    "refresh settlement-audit source fingerprints after scorecard, rules, signals, or "
                    "settlement-ledger byte changes"
                ),
            },
            {
                "order": 2,
                "command": "python3 current_evidence_summary.py",
                "reason": "rebuild the bridge from the refreshed scorecard, right-now card, settlement audit, and CSV recompute",
            },
            {
                "order": 3,
                "command": "python3 validate_current_evidence_summary.py",
                "reason": "confirm source fingerprint parity, gate-source alignment, and non-evidence boundaries before quoting the bridge",
            },
        ]
        checks.append(check(
            contract.get("rebuild_command") == "python3 current_evidence_summary.py"
            and contract.get("prerequisite_rebuild_command") == "python3 paper_trade_settlement_audit.py"
            and contract.get("upstream_refresh_order") == expected_upstream_refresh_order
            and contract.get("requires_settlement_audit_refresh_before_bridge_when_source_bytes_change") is True
            and contract.get("upstream_refresh_order_valid_use") == (
                "reproducible rebuild order for current bridge provenance after scorecard/rules/ledger byte changes"
            )
            and contract.get("direct_validation_command") == "python3 validate_current_evidence_summary.py"
            and contract.get("broader_rollup_commands_after_report_surface_edits") == [
                "python3 validate_report_surfaces.py --reuse-existing-child-json",
                "python3 validate_project_surfaces.py --reuse-existing-child-json",
            ]
            and contract.get("direct_output_paths") == ["CURRENT_EVIDENCE_SUMMARY.md", "current_evidence_summary.json"]
            and contract.get("validation_output_paths") == [
                "out/status_validation/current_evidence_summary/current_evidence_summary_validation.md",
                "out/status_validation/current_evidence_summary/current_evidence_summary_validation.json",
            ]
            and contract.get("green_checks_are_reproducibility_metadata_only") is True
            and contract.get("requires_source_consistency_before_quoting_current_totals") is True
            and contract.get("requires_source_freshness_before_right_now_instruction_use") is True
            and contract.get("upstream_refresh_order_is_provenance_metadata_only") is True
            and contract.get("not_settled_roi_or_real_money_evidence") is True,
            "rebuild and validation contract pins direct commands and metadata-only boundary",
        ))

        sources = payload.get("source_files", {})
        missing_source_labels = [label for label in SOURCE_FILE_LABELS if label not in sources]
        malformed_source_labels = [
            label for label in SOURCE_FILE_LABELS
            if label in sources and (
                sources[label].get("bytes", 0) <= 0
                or not isinstance(sources[label].get("sha256"), str)
                or len(sources[label].get("sha256")) != 64
            )
        ]
        checks.append(check(
            not missing_source_labels and not malformed_source_labels,
            "source fingerprints are present for every bridge input",
            f"missing={missing_source_labels}; malformed={malformed_source_labels}",
        ))
        fingerprint_details: list[str] = []
        fingerprint_ok = True
        for label in SOURCE_FILE_LABELS:
            fp = sources.get(label, {})
            ok, detail = source_fingerprint_matches_disk(fp) if isinstance(fp, dict) else (False, f"not dict: {fp}")
            fingerprint_ok = fingerprint_ok and ok
            fingerprint_details.append(f"{label}: {detail}")
        checks.append(check(
            fingerprint_ok,
            "source fingerprints match actual input files on disk",
            " | ".join(fingerprint_details),
        ))
        parsed_fingerprint_rows = parse_source_fingerprints_table(markdown)
        checks.append(check(
            set(parsed_fingerprint_rows) == set(SOURCE_FILE_LABELS)
            and all(
                parsed_fingerprint_rows[label].get("path") == sources[label].get("path")
                and parsed_fingerprint_rows[label].get("bytes") == sources[label].get("bytes")
                and parsed_fingerprint_rows[label].get("sha256") == sources[label].get("sha256")
                for label in SOURCE_FILE_LABELS
                if label in sources and label in parsed_fingerprint_rows
            ),
            "markdown source fingerprint table exactly matches JSON source_files",
            f"parsed_rows={sorted(parsed_fingerprint_rows)}",
        ))

        source_mismatch_ok, source_mismatch_detail = run_source_mismatch_fixture()
        checks.append(check(source_mismatch_ok, "source mismatch fixture fails closed instead of reporting source consistency", source_mismatch_detail))

        stale_audit_ok, stale_audit_detail = run_stale_settlement_audit_source_fingerprint_fixture()
        checks.append(check(
            stale_audit_ok,
            "stale settlement-audit upstream source fingerprints fail before bridge artifacts",
            stale_audit_detail,
        ))

        gate_mismatch_ok, gate_mismatch_detail = run_gate_source_mismatch_fixture()
        checks.append(check(gate_mismatch_ok, "gate-source mismatch fixture reports scorecard drift instead of silently quoting copied thresholds", gate_mismatch_detail))

        gate_missing_ok, gate_missing_detail = run_gate_source_missing_top_card_fixture()
        checks.append(check(gate_missing_ok, "missing top-card gate fields fail closed to scorecard-sourced bridge floors", gate_missing_detail))

        malformed_gate_ok, malformed_gate_detail = run_malformed_scorecard_gate_fails_before_artifacts_fixture()
        checks.append(check(
            malformed_gate_ok,
            "malformed scorecard gate floors fail before current-evidence artifacts",
            malformed_gate_detail,
        ))

        missing_ci_only_ok, missing_ci_only_detail = run_missing_scorecard_ci_only_diagnostic_fixture()
        checks.append(check(
            missing_ci_only_ok,
            "missing scorecard OP_REFINED CI-only diagnostic fails before current-evidence artifacts",
            missing_ci_only_detail,
        ))

        csv_timestamp_gap_ok, csv_timestamp_gap_detail = run_csv_timestamp_gap_fixture()
        checks.append(check(csv_timestamp_gap_ok, "CSV recompute excludes bad settled_ts and non-positive cost rows from ROI-complete counts", csv_timestamp_gap_detail))

        fresh_source_ok, fresh_source_detail = run_fresh_source_fixture()
        checks.append(check(fresh_source_ok, "freshness fixture distinguishes same-day fresh source, midnight rollover, combined stale reasons, missing freshness_state, and stale lane-only command override", fresh_source_detail))

        missing_output_context_ok, missing_output_context_detail = run_missing_scan_output_operator_context_fixture()
        checks.append(check(missing_output_context_ok, "missing scan-output operator context stays operational and non-evidence in current bridge", missing_output_context_detail))

        no_bet_context_ok, no_bet_context_detail = run_no_bet_recommendation_context_fixture()
        checks.append(check(no_bet_context_ok, "true no-BET recommendation context is not described as open-row context", no_bet_context_detail))

        scanner_failure_context_ok, scanner_failure_context_detail = run_scanner_failure_recommendation_context_fixture()
        checks.append(check(
            scanner_failure_context_ok,
            "scanner/API-failure recommendation context keeps one specific operator boundary",
            scanner_failure_context_detail,
        ))

        api_stale_cache_context_ok, api_stale_cache_context_detail = run_api_access_stale_cache_operator_context_fixture()
        checks.append(check(
            api_stale_cache_context_ok,
            "API-access stale-cache fallback context stays explicit in current bridge",
            api_stale_cache_context_detail,
        ))

        operator_context = payload.get("current_paper_status", {}).get("operator_status_context", {})
        operator_read_gate = payload.get("operator_read_gate", {})
        operator_read_requires_refresh = operator_read_gate.get("requires_refresh_before_evidence_read")
        checks.append(check(
            isinstance(operator_context, dict)
            and operator_context.get("not_forward_performance_evidence") is True
            and operator_context.get("valid_use") == "operator routing and source-readiness context only"
            and ("routing metadata" in str(operator_context.get("read") or "") or "operator readiness" in str(operator_context.get("read") or ""))
            and isinstance(operator_read_gate, dict)
            and operator_read_gate == payload.get("current_paper_status", {}).get("operator_read_gate")
            and operator_read_gate.get("valid_use") == "operator instruction/evidence-read gating only"
            and operator_read_gate.get("gate_status") in {
                "current_operator_routing_context_only",
                "refresh_required_before_evidence_read",
            }
            and isinstance(operator_read_requires_refresh, bool)
            and operator_read_gate.get("not_forward_performance_evidence") is True
            and operator_read_gate.get("not_promotion_readiness_evidence") is True
            and operator_read_gate.get("not_live_profitability_evidence") is True
            and operator_read_gate.get("not_real_money_evidence") is True
            and operator_read_gate.get("current_top_card_counts_as_settled_roi_evidence") is False
            and operator_read_gate.get("current_top_card_counts_as_bet_readiness_evidence") is False
            and "Operator read gate: " + str(operator_read_gate.get("read") or "") in markdown,
            "saved operator context is routing metadata, not performance evidence",
            f"operator_context={operator_context}; operator_read_gate={operator_read_gate}",
        ))

        decision_read = payload.get("decision_read", "")
        expected_decision_read = (
            f"TOO EARLY: primary paper is {primary.get('roi_complete_settled')}/{first_read.get('threshold')} ROI-complete "
            f"with {first_read.get('remaining')} more needed before a first statistical read; current settled sample is report context only."
            if not first_read.get("ready")
            else "FIRST READ READY: review hit rate, ROI, concentration, payout sanity, and frozen hierarchy before any posture change."
        )
        checks.append(check(
            decision_read == expected_decision_read
            and expected_decision_read in markdown,
            "decision read is source-derived and report-safe",
            decision_read,
        ))

    checks.append(check(
        VALID_EVIDENCE_SCOPE == summary_builder.VALID_EVIDENCE_SCOPE,
        "direct_validation_report_exposes_current_evidence_valid_scope",
        f"direct validator report publishes valid_evidence_scope={VALID_EVIDENCE_SCOPE} as bridge/report-navigation metadata only",
    ))

    status = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    return {
        "suite": "current_evidence_summary",
        "status": status,
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": {
            "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
            "not_new_forward_evidence": True,
            "not_live_profitability_evidence": True,
            "not_promotion_readiness_evidence": True,
            "not_real_money_evidence": True,
            "source_files_are_reproducibility_metadata_only": True,
            "source_freshness_is_operator_readiness_not_performance_proof": True,
            "decision_gate_status_is_routing_context_not_performance_proof": True,
            "operator_issue_context_is_not_performance_proof": True,
            "operator_read_gate_is_operator_routing_not_performance_proof": True,
        },
        "total_checks": len(checks),
        "check_count": len(checks),
        "checks": checks,
        "scratch": scratch,
        "summary": (
            "CURRENT_EVIDENCE_SUMMARY is source-matched to frozen scorecard + right-now paper-trade + settlement-audit inputs, "
            f"exposes valid_evidence_scope={VALID_EVIDENCE_SCOPE} on both source and validation surfaces, "
            "keeps OP_DURABLE_K7 / CD_CORE_K8 / OP_REFINED_K7 roles intact, derives current primary paper gates and rule-mix wording from source rows, "
            "publishes a structured OP-anchor settlement gap so CD companion rows cannot be counted as OP-anchor evidence, "
            "publishes a structured open-settlement queue state/by rule so source-published queue detail stays settlement workflow instead of ROI-complete or OP-anchor evidence, "
            "source-matches the bridge-published 30/20/100 gate minimums to exact forward_evidence_scorecard.json decision_gate_minimums keys, publishes scorecard-backed canonical gate values for the bridge, "
            "rejects boolean anchor and non-positive Phase 8 / real-money scorecard gate floors before writing current-evidence artifacts and preserves the no-BAQ-as-BEL real-money prerequisite, "
            "source-matches the OP_REFINED_K7 CI-only diagnostic to forward_evidence_scorecard.json so positive CI support remains shadow/watch context rather than a current-paper promotion trigger, "
            "lifts latest primary recommendation context so no-bet scanner observations cannot be mistaken for bet-ready tickets or forward evidence, "
            "mirrors settlement-audit open-row identity details plus per-rule shadow coverage without hard-coded current shadow counts, verifies source fingerprint byte/hash parity against the actual input files and markdown table, cross-checks top-card / settlement-audit / CSV counts, cost-return sums, settled_ts gap counts, and the open settlement queue, fixture-tests source mismatch, stale settlement-audit upstream fingerprints failing before bridge artifacts, gate-source mismatch, missing top-card gate fields, bad generated_at CLI provenance, CSV settled_ts gap exclusion from ROI-complete recomputes, same-day freshness, midnight date-rollover staleness, combined stale-reason behavior, missing right-now freshness_state failure, stale lane-only command override, missing scan-output operator context, true no-BET recommendation-context wording that must not be described as open-row context, scanner/API-failure recommendation-context wording that keeps one specific operator boundary plus the sidecar action/recheck route, and API-access stale-cache fallback wording that keeps fallback count/kind/error visible in the bridge operator-read gate, exposes whether the right-now source as-of date is stale versus the bridge reference date or whether the right-now card is internally stale, verifies stale best-action routing points to the daily wrapper while preserving inherited source actions as stale context, verifies fresh open-row best-action routing points to settlement, pins the direct rebuild/validation commands, verifies the canonical refresh_action_boundary command/valid-use/read text fields plus Boolean evidence flags are complete and typed at the source bridge, and marks the artifact as report/navigation and operator-routing context only rather than live profitability, promotion readiness, or real-money evidence."
            " It also publishes a structured staleness-age read and a New York reference-date calendar context so after-midnight non-US automation does not falsely stale a same-evening racing-date card while keeping calendar/freshness state as operator-readiness metadata only."
            if status == "pass"
            else "CURRENT_EVIDENCE_SUMMARY validation failed; inspect failed checks before using the bridge artifact."
        ),
    }


def render_markdown(result: dict[str, Any]) -> str:
    scratch = result.get("scratch", {}) if isinstance(result.get("scratch"), dict) else {}
    lines = [
        "# Current Evidence Summary Validation",
        "",
        f"Status: **{result['status']}**",
        f"Checks: {result['total_checks']}",
        f"valid_evidence_scope={result.get('valid_evidence_scope', '')}",
        f"Fixture scratch root: `{scratch.get('tmp_parent', '')}`",
        f"Fixture scratch root project-local: `{scratch.get('tmp_parent_is_project_local', False)}`",
        f"Fixture scratch root cleared before fixture run: `{scratch.get('tmp_parent_cleared_before_fixture_run', False)}`",
        "",
        result["summary"],
        "",
        "| Check | Status | Details |",
        "|---|---|---|",
    ]
    for item in result["checks"]:
        lines.append(f"| {item['name']} | {item['status']} | {item.get('details', '')} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    result = validate()
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    VALIDATION_MD.write_text(render_markdown(result) + "\n", encoding="utf-8")
    print(f"current_evidence_summary validation: {result['status']} ({result['total_checks']} checks)")
    print(f"Saved to: {VALIDATION_MD}")
    print(f"Saved to: {VALIDATION_JSON}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
