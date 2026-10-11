#!/usr/bin/env python3
"""Compare two HOI4 log files by message text and occurrence count.

The script answers one question about a test run: which log messages appeared,
or appeared more often, in the "after" log than in the "baseline" log, and which
ones went away. It is used on ``error.log`` or ``game.log`` pairs taken from a
fresh game start and from the same game after exercising a mod feature.

Inputs are two log paths given on the command line. Each file is read as bytes,
NUL bytes are dropped (older interrupted snapshots contain zero-filled regions),
and the rest is decoded as UTF-8 with an optional BOM; undecodable bytes become
U+FFFD. Every non-blank line then loses its ``[HH:MM:SS][date]`` prefix, where
the date is either ``no_game_date`` or an in-game ``YYYY.MM.DD.HH`` stamp, and
its trailing whitespace. Nothing else is normalized, so file names, line
numbers and object IDs inside a message still have to match exactly.

Both logs become multisets (``collections.Counter``) of normalized messages.
The report lists the multiset differences in both directions, sorted by message
text, together with total and per-direction occurrence counts, the absolute
paths of both inputs, the normalization rule and a fixed limitation note. The
report is printed to stdout as indented JSON and, with ``--output``, also
written to that file as UTF-8.

The comparison is bounded. It covers only the two supplied logs and the actions
exercised between them. A clean result does not show that the game has no
bugs, and it is only meaningful when both logs come from the same game build,
DLC set and mod list. Message order and timing are ignored on purpose.

Usage::

    python tools/compare-logs.py baseline.log after.log [--output report.json]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

HELP_DESCRIPTION = (
    "Compare HOI4 error logs by message and occurrence count, ignoring only timestamps.\n"
    "\n"
    "Usage: python tools/compare-logs.py baseline.log after.log [--output report.json]\n"
    "This is evidence of a bounded log comparison, not proof of absence of all game bugs.\n"
)
"""Text shown by ``--help``; kept verbatim so the CLI help output stays unchanged."""

PREFIX = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\[(?:no_game_date|\d{4}\.\d{2}\.\d{2}\.\d{2})\]")
"""Regex for the HOI4 ``[HH:MM:SS][game date]`` line prefix that is stripped before comparing."""


def messages(path: Path) -> Counter[str]:
    """Read one log and count its normalized, non-blank messages.

    Args:
        path: Log file to read.

    Returns:
        A counter mapping each normalized message to its number of occurrences.
    """
    # Older interrupted log snapshots contain zero-filled regions, not messages.
    text = path.read_bytes().replace(b"\x00", b"").decode("utf-8-sig", errors="replace")
    return Counter(PREFIX.sub("", line).rstrip() for line in text.splitlines() if line.strip())


def compare(baseline: Path, after: Path) -> dict[str, object]:
    """Build the JSON-ready comparison report for two logs.

    Args:
        baseline: Log captured before the exercised actions.
        after: Log captured after the exercised actions.

    Returns:
        The report dictionary with occurrence totals and the added and removed
        messages, each list sorted by message text.
    """
    before_messages, after_messages = messages(baseline), messages(after)
    added = after_messages - before_messages
    removed = before_messages - after_messages
    return {
        "baseline": str(baseline.resolve()),
        "after": str(after.resolve()),
        "normalization": (
            "Strip HH:MM:SS + HOI4 game-date prefix, trailing whitespace and NUL bytes only."
        ),
        "baseline_occurrences": before_messages.total(),
        "after_occurrences": after_messages.total(),
        "added_occurrences": added.total(),
        "removed_occurrences": removed.total(),
        "added": [{"count": count, "message": message} for message, count in sorted(added.items())],
        "removed": [
            {"count": count, "message": message} for message, count in sorted(removed.items())
        ],
        "limitation": (
            "Only the supplied logs and exercised actions are covered; "
            "startup baseline must match game, DLC and mods."
        ),
    }


def main() -> None:
    """Parse the command line, print the report and optionally write it to a file."""
    parser = argparse.ArgumentParser(description=HELP_DESCRIPTION)
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
