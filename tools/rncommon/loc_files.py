"""The HOI4 localisation file format as the offline checks read it.

A localisation file starts with a UTF-8 byte order mark and an ``l_<language>:``
header; every other entry is one line `` KEY:N "value"`` with a single leading
space and an optional one-digit version ``N``.
"""

from __future__ import annotations

import re
from pathlib import Path

UTF8_BOM = b"\xef\xbb\xbf"
"""Byte order mark every HOI4 localisation file must start with."""

LOC_LINE = re.compile(r' (\S+?):\d? "(.*)"\s*$')
"""One `` KEY:N "value"`` line, matched from the start; key and value are captured."""


def loc_entries(path: str | Path) -> list[tuple[str, str]]:
    """Read every ``KEY: "value"`` entry of one localisation file in file order.

    Lines that do not match :data:`LOC_LINE` (header, comments, blank lines) are
    skipped. The file is decoded as UTF-8 with an optional BOM.

    Args:
        path: Localisation ``.yml`` file.

    Returns:
        ``(key, value)`` pairs; a key that repeats appears once per occurrence.
    """
    entries: list[tuple[str, str]] = []
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line in handle:
            match = LOC_LINE.match(line)
            if match:
                entries.append((match.group(1), match.group(2)))
    return entries
