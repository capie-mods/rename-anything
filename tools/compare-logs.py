#!/usr/bin/env python3
"""Compare HOI4 error logs by message and occurrence count, ignoring only timestamps.

Usage: python tools/compare-logs.py baseline.log after.log [--output report.json]
This is evidence of a bounded log comparison, not proof of absence of all game bugs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

PREFIX = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\[(?:no_game_date|\d{4}\.\d{2}\.\d{2}\.\d{2})\]")


def messages(path: Path) -> Counter[str]:
    # Older interrupted log snapshots contain zero-filled regions, not messages.
    text = path.read_bytes().replace(b"\x00", b"").decode("utf-8-sig", errors="replace")
    return Counter(PREFIX.sub("", line).rstrip() for line in text.splitlines() if line.strip())


def compare(baseline: Path, after: Path) -> dict:
    before_messages, after_messages = messages(baseline), messages(after)
    added = after_messages - before_messages
    removed = before_messages - after_messages
    return {
        "baseline": str(baseline.resolve()), "after": str(after.resolve()),
        "normalization": "Strip HH:MM:SS + HOI4 game-date prefix, trailing whitespace and NUL bytes only.",
        "baseline_occurrences": before_messages.total(),
        "after_occurrences": after_messages.total(),
        "added_occurrences": added.total(), "removed_occurrences": removed.total(),
        "added": [{"count": count, "message": message} for message, count in sorted(added.items())],
        "removed": [{"count": count, "message": message} for message, count in sorted(removed.items())],
        "limitation": "Only the supplied logs and exercised actions are covered; startup baseline must match game, DLC and mods.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = compare(args.baseline, args.after)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
