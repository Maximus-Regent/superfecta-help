#!/usr/bin/env python3
"""
Validate copied current-operator run-context snippets across report-facing surfaces.

Purpose:
- catch stale "latest live scan ... across N cards and M races" copies after the
  daily wrapper or current-evidence bridge changes
- keep copied current-run context as operator routing metadata only
- avoid using a clean empty scan, copied count, or validation pass as forward
  performance, promotion readiness, live profitability, or real-money evidence
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
CURRENT_EVIDENCE_JSON = BASE / "current_evidence_summary.json"
OUT_DIR = BASE / "out" / "status_validation" / "current_operator_context_sync"
OUT_MD = OUT_DIR / "current_operator_context_sync_validation.md"
OUT_JSON = OUT_DIR / "current_operator_context_sync_validation.json"
REBUILD_COMMAND = "python3 validate_current_operator_context_sync.py"
VALID_EVIDENCE_SCOPE = "current_operator_context_sync_validation_only"

RUN_CONTEXT_RE = re.compile(
    r"Latest run context: the latest live scan completed cleanly and found no qualifying races "
    r"across (?P<cards>\d+) card\(s\) and (?P<races>\d+) race\(s\)\."
)

ACTIVE_SURFACES = [
    "PAPER_TRADE_NOW.txt",
    "PAPER_TRADE_NOW.md",
    "PAPER_TRADE_NOW.json",
    "CURRENT_EVIDENCE_SUMMARY.md",
    "current_evidence_summary.json",
    "README.md",
    "COLE_STATUS_AND_PLAN.md",
    "COLE_FULL_REPORT_2026-04-15.md",
    "WORKING_STATUS_REPORT_2026-04-15.md",
    "COLE_PRESENTATION_OUTLINE.md",
    "PAPER_TRADE_USAGE.md",
    "DAILY_ARTIFACT_GUIDE.md",
    "compare_main_approaches.md",
    "compare_main_approaches.json",
    "compare_main_approaches.csv",
    "OP_ANCHOR_METHOD_COMPARISON.md",
    "op_anchor_method_comparison.json",
    "OP_FAMILY_DECISION.md",
    "op_family_decision.csv",
    "CROSS_FAMILY_DECISION.md",
    "cross_family_decision_card.csv",
    "PORTFOLIO_DECISION_CARD.md",
    "portfolio_decision_card.csv",
    "METHOD_FAMILY_DECISION.md",
    "method_family_decision_card.csv",
    "FROZEN_PORTFOLIO_EVAL.md",
    "frozen_portfolio_eval_metadata.json",
    "AB_DOWNSTREAM_COMPARISON.md",
    "ab_downstream_comparison_results.json",
    "compare_recommender_scope_paths.md",
    "compare_recommender_scope_paths.json",
    "SCORECARD_RANKING_CONTRACT_AUDIT.md",
    "scorecard_ranking_contract_audit.json",
    "VALIDATION_QUICKSTART.md",
]

EVIDENCE_BOUNDARY: dict[str, Any] = {
    "artifact_role": "current-operator copied-context sync validator",
    "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
    "source_scope": [
        "current_evidence_summary.json current primary recommendation context",
        "report-facing markdown, JSON, text, and CSV surfaces that copy the current run-context line",
    ],
    "valid_use": "report-synchronization audit for copied current-run card/race counts",
    "not_new_forward_evidence": True,
    "not_current_day_scanner_result": True,
    "not_settled_roi_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_live_profitability_evidence": True,
    "not_bankroll_guidance": True,
    "not_real_money_evidence": True,
    "clean_empty_counts_are_operator_context_only": True,
}


def require(condition: bool, label: str, detail: str) -> dict[str, Any]:
    if not condition:
        raise AssertionError(f"{label}: {detail}")
    return {"check": label, "status": "pass", "detail": detail}


def file_fingerprint(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(BASE)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def load_source_context() -> dict[str, Any]:
    payload = json.loads(CURRENT_EVIDENCE_JSON.read_text(encoding="utf-8"))
    current_paper_status = payload.get("current_paper_status")
    if not isinstance(current_paper_status, dict):
        raise AssertionError("current_evidence_summary.json is missing current_paper_status")
    primary = current_paper_status.get("primary")
    if not isinstance(primary, dict):
        raise AssertionError("current_evidence_summary.json is missing current_paper_status.primary")
    recommendation = primary.get("recommendation_context")
    if not isinstance(recommendation, dict):
        raise AssertionError("current_evidence_summary.json is missing primary recommendation_context")

    latest_context = str(recommendation.get("latest_run_context") or "").strip()
    recommendation_read = str(recommendation.get("read") or "").strip()
    if not latest_context:
        latest_context = str(primary.get("recent_run_context") or "").strip()
    if not latest_context:
        raise AssertionError("current_evidence_summary.json is missing the latest primary run context")
    if not recommendation_read:
        raise AssertionError("current_evidence_summary.json is missing recommendation_context.read")
    if recommendation.get("not_forward_performance_evidence") is not True:
        raise AssertionError("recommendation_context must mark latest-run context as not forward-performance evidence")
    if recommendation.get("not_bet_readiness_evidence_by_itself") is not True:
        raise AssertionError("recommendation_context must mark latest-run context as not bet-readiness evidence by itself")

    match = RUN_CONTEXT_RE.search(latest_context)
    expected_counts = None
    if match:
        expected_counts = {
            "cards": int(match.group("cards")),
            "races": int(match.group("races")),
        }
    return {
        "source_path": CURRENT_EVIDENCE_JSON.name,
        "generated_at": payload.get("generated_at"),
        "latest_context": latest_context,
        "recommendation_read": recommendation_read,
        "expected_counts": expected_counts,
        "operator_read_gate": payload.get("operator_read_gate"),
        "source_fingerprint": file_fingerprint(CURRENT_EVIDENCE_JSON),
    }


def run_context_matches(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    line_starts = [0]
    for match in re.finditer(r"\n", text):
        line_starts.append(match.end())
    for match in RUN_CONTEXT_RE.finditer(text):
        line_no = 1
        for idx, start in enumerate(line_starts):
            if start > match.start():
                break
            line_no = idx + 1
        matches.append(
            {
                "line": line_no,
                "cards": int(match.group("cards")),
                "races": int(match.group("races")),
                "text": match.group(0),
            }
        )
    return matches


def build_surface_rows(source_context: dict[str, Any]) -> list[dict[str, Any]]:
    expected_counts = source_context.get("expected_counts")
    rows: list[dict[str, Any]] = []
    for rel_path in ACTIVE_SURFACES:
        path = BASE / rel_path
        if not path.exists():
            raise AssertionError(f"configured surface is missing: {rel_path}")
        text = path.read_text(encoding="utf-8")
        matches = run_context_matches(text)
        stale_matches: list[dict[str, Any]] = []
        for match in matches:
            if expected_counts is None:
                if match["text"] != source_context["latest_context"]:
                    stale_matches.append(match)
                continue
            if match["cards"] != expected_counts["cards"] or match["races"] != expected_counts["races"]:
                stale_matches.append(match)

        rows.append(
            {
                "surface": rel_path,
                "status": "pass" if not stale_matches else "fail",
                "copied_context_count": len(matches),
                "stale_context_count": len(stale_matches),
                "matches": matches,
                "stale_matches": stale_matches,
                "source_fingerprint": file_fingerprint(path),
            }
        )
    return rows


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_markdown(payload: dict[str, Any]) -> str:
    source = payload["source_context"]
    counts = source.get("expected_counts") or {}
    expected = (
        f"{counts.get('cards')} card(s) / {counts.get('races')} race(s)"
        if counts
        else "source latest-context text only"
    )
    lines = [
        "# Current Operator Context Sync Validation",
        "",
        f"Generated from: `{source['source_path']}`",
        f"Source generated_at: `{source.get('generated_at')}`",
        f"Expected copied context: {markdown_escape(source['latest_context'])}",
        f"Expected count pair: `{expected}`",
        "",
        "Evidence boundary: this validator checks copied operator-context counts only. It is not a current-day scanner result, settled ROI, promotion readiness, live profitability, bankroll guidance, or real-money evidence.",
        "",
        "## Surface Inventory",
        "",
        "| Status | Surface | Copied contexts | Stale contexts |",
        "|---|---:|---:|---:|",
    ]
    for row in payload["surface_rows"]:
        lines.append(
            f"| {row['status'].upper()} | `{markdown_escape(row['surface'])}` | "
            f"{row['copied_context_count']} | {row['stale_context_count']} |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Status | Check | Detail |",
            "|---|---|---|",
        ]
    )
    for check in payload["checks"]:
        lines.append(
            f"| {check['status'].upper()} | `{markdown_escape(check['check'])}` | "
            f"{markdown_escape(check['detail'])} |"
        )
    lines.extend(
        [
            "",
            f"Rebuild command: `{REBUILD_COMMAND}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_context = load_source_context()
    rows = build_surface_rows(source_context)
    total_copied_contexts = sum(row["copied_context_count"] for row in rows)
    total_stale_contexts = sum(row["stale_context_count"] for row in rows)
    surfaces_with_copies = [row["surface"] for row in rows if row["copied_context_count"] > 0]

    expected_counts = source_context.get("expected_counts")
    current_clean_text = source_context["latest_context"]
    negative_text = current_clean_text
    if expected_counts:
        stale_cards = max(int(expected_counts["cards"]) - 1, 0)
        negative_text = RUN_CONTEXT_RE.sub(
            (
                "Latest run context: the latest live scan completed cleanly and found no qualifying races "
                f"across {stale_cards} card(s) and {expected_counts['races']} race(s)."
            ),
            current_clean_text,
        )
    negative_matches = run_context_matches(negative_text)
    negative_is_stale = bool(
        expected_counts
        and negative_matches
        and (
            negative_matches[0]["cards"] != expected_counts["cards"]
            or negative_matches[0]["races"] != expected_counts["races"]
        )
    )

    checks = [
        require(
            expected_counts is None
            or (expected_counts["cards"] >= 0 and expected_counts["races"] >= 0),
            "source_context_count_pair_parseable",
            "current_evidence_summary.json latest primary run context publishes a parseable non-negative card/race count pair when it uses the clean-empty live-scan wording",
        ),
        require(
            total_copied_contexts > 0,
            "active_surfaces_include_copied_context",
            f"found {total_copied_contexts} copied current-run context snippet(s) across {len(surfaces_with_copies)} active surface(s)",
        ),
        require(
            total_stale_contexts == 0,
            "no_stale_copied_context_counts",
            "every copied clean-empty latest-run context count pair matches current_evidence_summary.json",
        ),
        require(
            source_context["source_fingerprint"]["bytes"] > 0
            and len(source_context["source_fingerprint"]["sha256"]) == 64,
            "current_evidence_source_fingerprint_published",
            "validation output fingerprints current_evidence_summary.json as copied-context provenance metadata only",
        ),
        require(
            negative_is_stale or expected_counts is None,
            "stale_count_fixture_would_fail",
            "in-process stale card-count fixture is distinguishable from the current source count pair",
        ),
    ]

    payload = {
        "suite_status": "pass",
        "valid_evidence_scope": VALID_EVIDENCE_SCOPE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "rebuild_command": REBUILD_COMMAND,
        "source_context": source_context,
        "surface_count": len(rows),
        "surfaces_with_copied_context_count": len(surfaces_with_copies),
        "total_copied_contexts": total_copied_contexts,
        "total_stale_contexts": total_stale_contexts,
        "surface_rows": rows,
        "check_count": len(checks),
        "checks": checks,
        "summary": {
            "suite_read": (
                f"current operator-context sync passed across {len(rows)} active surfaces; "
                f"{total_copied_contexts} copied latest-run snippet(s) match "
                f"current_evidence_summary.json and remain operator-context metadata only"
            )
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(build_markdown(payload), encoding="utf-8")
    print(f"PASS current operator-context sync: {total_copied_contexts} copied snippets, {total_stale_contexts} stale")
    print(f"Saved: {OUT_MD.relative_to(BASE)}")
    print(f"Saved: {OUT_JSON.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
