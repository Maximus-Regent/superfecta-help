#!/usr/bin/env python3
"""
Generate a short preflight note for the current race day.

Purpose:
- explain whether active-basket tracks are racing today
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
    total_cards = int(pf.get("total_cards") or 0)

    if pf.get("error"):
        note = f"Preflight context: NYRA preflight check failed ({pf['error']}). Treat calendar state as unknown."
    elif not pf.get("api_ok"):
        note = "Preflight context: could not reach the NYRA preflight API, so calendar state is unknown."
    elif has_targets:
        tracks = ", ".join(relevant_tracks)
        note = f"Preflight context: active-basket tracks racing today: {tracks}."
        if shadow_tracks:
            note += f" Shadow-only tracks also present: {', '.join(shadow_tracks)}."
    else:
        note = f"Preflight context: no active-basket tracks (OP / CD) are racing today across {total_cards} NYRA card(s)."
        if shadow_tracks:
            note += f" Shadow-only tracks present: {', '.join(shadow_tracks)}."

    return {
        "date": pf.get("date"),
        "checked_at": pf.get("checked_at"),
        "api_ok": bool(pf.get("api_ok")),
        "has_targets": has_targets,
        "relevant_tracks": relevant_tracks,
        "shadow_tracks": shadow_tracks,
        "total_cards": total_cards,
        "error": pf.get("error"),
        "note": note,
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
