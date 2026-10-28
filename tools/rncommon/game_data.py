"""Read-only access to the vanilla HOI4 data the generator and the checker need.

Two tools read the same vanilla files: ``tools/gen.py`` builds the state to
victory point (VP) table from them and ``tools/check.py`` compares the generated
table with them again. Both used to carry their own copy of the parser; this
module is now the single one.

File access goes through the :class:`GameData` protocol. Its production adapter
is :class:`GameInstallation`, a folder on disk. The protocol exists because the
installation is an external dependency that is absent on CI machines and in
unit tests: a test passes a small in-memory object with the same three methods
instead of a 1000-file Steam folder. The parsing functions below only see text,
never paths, so they are the same for both.

The parsing rules, unchanged from the original tools:

* ``history/states/*.txt`` files are read in sorted ``glob`` order with ``#``
  comments removed. The first ``id = <n>`` is the state ID; a file without one is
  reported and skipped. A later file wins on a duplicate ID.
* Each ``victory_points = { <province> <value> }`` adds its province once, in
  file order, and at most :data:`MAX_VP_SLOTS` provinces are kept. States without
  VPs stay in the table with an empty list.
* An English ``VICTORY_POINTS_<id>:`` line marks province ``<id>`` as named.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
"""Steam installation folder used when a tool gets no game path."""

MAX_VP_SLOTS = 5
"""Number of distinct VP provinces kept per state (the Cities tab has five rows)."""

COMMENT = re.compile(r"#[^\n]*")
"""A ``#`` comment up to the end of its line."""

STATE_ID = re.compile(r"\bid\s*=\s*(\d+)")
"""The ``id = <n>`` assignment of a state history file."""

VICTORY_POINT = re.compile(r"victory_points\s*=\s*\{\s*(\d+)\s+[-\d.]+\s*\}")
"""One ``victory_points = { <province> <value> }`` entry; the province is captured."""

VP_LOC_KEY = re.compile(r"\s*VICTORY_POINTS_(\d+):")
"""Start of an English ``VICTORY_POINTS_<province>:`` localisation line."""

StateIssueKind = Literal["missing_id", "duplicate_id"]
"""Kind of a problem found while reading the state history files."""


class GameData(Protocol):
    """Read-only view of a HOI4 installation.

    Implementations return text only; the parsing lives in this module so that
    every implementation is read the same way.
    """

    def has_state_history(self) -> bool:
        """Return whether the installation has a ``history/states`` folder.

        Returns:
            True when the folder exists.
        """
        ...

    def state_histories(self) -> Iterator[tuple[str, str]]:
        """Yield every state history file in sorted path order.

        Returns:
            An iterator of ``(display path, text)`` pairs. The display path is
            only used in messages.
        """
        ...

    def english_localisation_lines(self) -> Iterator[str]:
        """Yield every line of the English localisation files.

        Returns:
            An iterator over the lines, line endings included.
        """
        ...

    def interface_sprites_text(self) -> str:
        """Return all vanilla ``interface/*.gfx`` files concatenated.

        Returns:
            The sprite definitions as one string.
        """
        ...


class GameInstallation:
    """:class:`GameData` adapter for a HOI4 installation folder on disk.

    ``glob.glob`` with ``os.path.join`` is used on purpose instead of ``pathlib``:
    its string order and dot-file rules decide which file wins on a duplicate
    state ID, and its paths appear verbatim in the checker's findings.
    """

    def __init__(self, root: str) -> None:
        """Create the adapter.

        Args:
            root: Installation folder, as given on the command line.
        """
        self.root = root

    def has_state_history(self) -> bool:
        """Return whether ``history/states`` exists under the installation folder.

        Returns:
            True when the folder exists.
        """
        return os.path.isdir(os.path.join(self.root, "history", "states"))  # noqa: PTH112, PTH118

    def state_histories(self) -> Iterator[tuple[str, str]]:
        """Yield ``history/states/*.txt`` in sorted order, decoded leniently.

        Yields:
            ``(glob path, text)`` pairs; undecodable bytes become U+FFFD.
        """
        pattern = os.path.join(self.root, "history", "states", "*.txt")  # noqa: PTH118
        for path in sorted(glob.glob(pattern)):  # noqa: PTH207
            with Path(path).open(encoding="utf-8-sig", errors="replace") as handle:
                yield path, handle.read()

    def english_localisation_lines(self) -> Iterator[str]:
        """Yield the lines of ``localisation/english/*.yml`` in ``glob`` order.

        Yields:
            Each line, line ending included; undecodable bytes become U+FFFD.
        """
        pattern = os.path.join(self.root, "localisation", "english", "*.yml")  # noqa: PTH118
        for path in glob.glob(pattern):  # noqa: PTH207
            with Path(path).open(encoding="utf-8-sig", errors="replace") as handle:
                yield from handle

    def interface_sprites_text(self) -> str:
        """Return ``interface/*.gfx`` concatenated in ``glob`` order.

        Returns:
            The decoded text; undecodable bytes become U+FFFD.
        """
        parts = []
        for path in glob.glob(os.path.join(self.root, "interface", "*.gfx")):  # noqa: PTH118, PTH207
            with Path(path).open(encoding="utf-8", errors="replace") as handle:
                parts.append(handle.read())
        return "".join(parts)


@dataclass(frozen=True)
class StateIssue:
    """A problem met while reading the state history files."""

    kind: StateIssueKind
    """``missing_id`` (file without ``id``) or ``duplicate_id`` (ID seen before)."""

    detail: str
    """The file path for ``missing_id``, the state ID for ``duplicate_id``."""


@dataclass
class StateInventory:
    """Vanilla states with their VP provinces, in file order."""

    states: dict[int, list[int]] = field(default_factory=dict)
    """State ID to its first :data:`MAX_VP_SLOTS` distinct VP provinces."""

    issues: list[StateIssue] = field(default_factory=list)
    """Problems in the order they were met."""


def parse_state_history(text: str) -> tuple[int, list[int]] | None:
    """Parse one state history file.

    Args:
        text: File contents.

    Returns:
        The state ID and its distinct VP provinces in file order (not yet
        truncated), or None when the file has no ``id``.
    """
    text = COMMENT.sub("", text)
    match = STATE_ID.search(text)
    if not match:
        return None
    provinces: list[int] = []
    for province_text in VICTORY_POINT.findall(text):
        province = int(province_text)
        if province not in provinces:
            provinces.append(province)
    return int(match.group(1)), provinces


def read_state_inventory(histories: Iterable[tuple[str, str]]) -> StateInventory:
    """Build the state to VP-province inventory from state history files.

    Args:
        histories: ``(display path, text)`` pairs in reading order, as
            :meth:`GameData.state_histories` yields them.

    Returns:
        The inventory; a later file wins on a duplicate ID.
    """
    inventory = StateInventory()
    for path, text in histories:
        parsed = parse_state_history(text)
        if parsed is None:
            inventory.issues.append(StateIssue("missing_id", path))
            continue
        state_id, provinces = parsed
        if state_id in inventory.states:
            inventory.issues.append(StateIssue("duplicate_id", str(state_id)))
        inventory.states[state_id] = provinces[:MAX_VP_SLOTS]
    return inventory


def vp_key_ids(lines: Iterable[str]) -> set[str]:
    """Collect the province IDs that have an English ``VICTORY_POINTS_<id>`` key.

    Args:
        lines: English localisation lines.

    Returns:
        The IDs exactly as written (digit strings).
    """
    ids: set[str] = set()
    for line in lines:
        match = VP_LOC_KEY.match(line)
        if match:
            ids.add(match.group(1))
    return ids


HAS_DLC_NAMES = frozenset(
    {
        "Poland: United and Ready",
        "Together for Victory",
        "Death or Dishonor",
        "Waking the Tiger",
        "Man the Guns",
        "La Resistance",
        "Battle for the Bosporus",
        "No Step Back",
        "By Blood Alone",
        "Axis Armor Pack",
        "Arms Against Tyranny",
        "Trial of Allegiance",
        "Expansion Pass 1: Supporter Pack",
        "Gotterdammerung",
        "Graveyard of Empires",
        "No Compromise, No Surrender",
        "Peace For Our Time",
        "Thunder at Our Gates",
    }
)
"""The only names ``has_dlc`` accepts in HOI4 1.19.4.0 (exact, case-sensitive).

hoi4.exe compares the value against this fixed table (``FUN_1401b7030``, called by the has_dlc
parser; capie docs/research/ghidra-review-2026-10-28.md, R3). Any other name, e.g. a cosmetic
pack such as "Anniversary Pack", is a script error. Re-read the table after each game update.
"""
