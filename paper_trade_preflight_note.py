#!/usr/bin/env python3
"""
Generate a short preflight note for the current race day.

Purpose:
- explain whether primary paper-basket target tracks are racing today
- keep daily operator output honest on dead calendar days
- reuse the existing `superfecta_ops` card-check logic instead of inventing another path
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL 1.1.1\+.*")

from superfecta_ops import check_todays_cards_extended

BASE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE / "out" / "paper_trade_preflight_note.txt"
PREFLIGHT_VALID_EVIDENCE_SCOPE = "paper_trade_preflight_calendar_context_only"
PREFLIGHT_EVIDENCE_BOUNDARY = {
    "artifact_role": "paper-trade race-calendar preflight note",
    "valid_evidence_scope": PREFLIGHT_VALID_EVIDENCE_SCOPE,
    "not_current_day_scanner_result": True,
    "not_live_paper_trade_ledger": True,
    "not_settled_roi_evidence": True,
    "not_live_profitability_evidence": True,
    "not_promotion_readiness_evidence": True,
    "not_real_money_evidence": True,
    "not_baq_as_bel_evidence": True,
}
PREFLIGHT_EVIDENCE_BOUNDARY_TEXT = (
    "Preflight output is race-calendar context only; it can identify active-target, no-target, "
    "excluded-alias, or unknown-calendar states, but it is not a scanner result, live paper-trade ledger, "
    "settled ROI evidence, promotion readiness, live-profitability evidence, real-money support, or BAQ-as-BEL evidence."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a short preflight note for today's race calendar")
    p.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Optional file to save the note")
    return p.parse_args()


def build_payload() -> dict[str, object]:
    pf = check_todays_cards_extended()
    has_targets = bool(pf.get("has_targets"))
    relevant_tracks = list(pf.get("relevant_tracks") or [])
    shadow_tracks = list(pf.get("shadow_tracks") or [])
    excluded_tracks = list(pf.get("excluded_tracks") or [])
    total_cards = int(pf.get("total_cards") or 0)

    excluded_note = ""
    if excluded_tracks:
        excluded_note = f" Excluded track aliases present: {', '.join(excluded_tracks)} (not treated as BEL)."

    if pf.get("error"):
        calendar_state = "UNKNOWN"
        calendar_reason = "upstream_error"
        note = f"Preflight context: NYRA preflight check failed ({pf['error']}). Treat calendar state as unknown."
    elif not pf.get("api_ok"):
        calendar_state = "UNKNOWN"
        calendar_reason = "api_unreachable"
        note = "Preflight context: could not reach the NYRA preflight API, so calendar state is unknown."
    elif has_targets:
        calendar_state = "ACTIVE TARGETS"
        calendar_reason = "active_targets"
        tracks = ", ".join(relevant_tracks)
        note = f"Preflight context: primary paper-basket target tracks racing today: {tracks}."
        if shadow_tracks:
            note += f" Shadow-only tracks also present: {', '.join(shadow_tracks)}."
        note += excluded_note
    else:
        calendar_state = "NO TARGETS"
        calendar_reason = "no_targets"
        note = f"Preflight context: no primary paper-basket target tracks (OP / CD) are racing today across {total_cards} NYRA card(s)."
        if shadow_tracks:
            note += f" Shadow-only tracks present: {', '.join(shadow_tracks)}."
        note += excluded_note

    return {
        "date": pf.get("date"),
        "checked_at": pf.get("checked_at"),
        "api_ok": bool(pf.get("api_ok")),
        "calendar_state": calendar_state,
        "calendar_reason": calendar_reason,
        "has_targets": has_targets,
        "relevant_tracks": relevant_tracks,
        "relevant_track_count": len(relevant_tracks),
        "shadow_tracks": shadow_tracks,
        "shadow_track_count": len(shadow_tracks),
        "excluded_tracks": excluded_tracks,
        "excluded_track_count": len(excluded_tracks),
        "total_cards": total_cards,
        "error": pf.get("error"),
        "note": note,
        "valid_evidence_scope": PREFLIGHT_VALID_EVIDENCE_SCOPE,
        "evidence_boundary": PREFLIGHT_EVIDENCE_BOUNDARY,
        "evidence_boundary_text": PREFLIGHT_EVIDENCE_BOUNDARY_TEXT,
    }


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.format == "json":
        output = json.dumps(payload, indent=2) + "\n"
    else:
        output = str(payload["note"]) + "\n"

    if args.output:
        write_output(Path(args.output), output)
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
