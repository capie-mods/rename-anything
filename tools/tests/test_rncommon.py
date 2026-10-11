"""Unit tests of the shared helpers in ``tools/rncommon``.

Run with ``uv run pytest``. The game data tests use an in-memory
:class:`~rncommon.game_data.GameData` implementation, so no HOI4 installation
is needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rncommon.game_data import (
    MAX_VP_SLOTS,
    StateIssue,
    parse_state_history,
    read_state_inventory,
    vp_key_ids,
)
from rncommon.hashing import sha256_file
from rncommon.loc_files import LOC_LINE, loc_entries

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
"""SHA-256 of zero bytes."""


class FakeGame:
    """In-memory :class:`~rncommon.game_data.GameData` for tests."""

    def __init__(self, histories: list[tuple[str, str]], loc_lines: list[str]) -> None:
        """Store the fake files.

        Args:
            histories: ``(path, text)`` state history files in reading order.
            loc_lines: English localisation lines.
        """
        self.histories = histories
        self.loc_lines = loc_lines

    def has_state_history(self) -> bool:
        """Report a state history folder when there is at least one file.

        Returns:
            Whether any history was given.
        """
        return bool(self.histories)

    def state_histories(self) -> Iterator[tuple[str, str]]:
        """Yield the stored histories.

        Yields:
            ``(path, text)`` pairs.
        """
        yield from self.histories

    def english_localisation_lines(self) -> Iterator[str]:
        """Yield the stored localisation lines.

        Yields:
            Each line.
        """
        yield from self.loc_lines

    def interface_sprites_text(self) -> str:
        """Return no vanilla sprites.

        Returns:
            An empty string.
        """
        return ""


def test_parse_state_history_strips_comments_and_duplicates() -> None:
    """A commented-out VP is ignored and a repeated province counts once."""
    text = (
        "state = {\n id = 12 # comment id = 99\n"
        " victory_points = { 100 5 }\n # victory_points = { 200 1 }\n"
        " victory_points = { 100 2.5 }\n victory_points = { 300 -1 }\n}\n"
    )
    assert parse_state_history(text) == (12, [100, 300])


def test_parse_state_history_without_id() -> None:
    """A file without ``id`` is not a state."""
    assert parse_state_history("state = { victory_points = { 1 1 } }") is None


def test_read_state_inventory_keeps_order_limits_slots_and_reports_issues() -> None:
    """Issues come in file order, a later file wins and VPs are capped."""
    many = "".join(f"victory_points = {{ {p} 1 }}\n" for p in range(1, 9))
    game = FakeGame(
        [
            ("a.txt", "id = 5\n" + many),
            ("b.txt", "no id here"),
            ("c.txt", "id = 5\nvictory_points = { 42 1 }"),
            ("d.txt", "id = 3\n"),
        ],
        [],
    )
    inventory = read_state_inventory(game.state_histories())
    assert inventory.states == {5: [42], 3: []}
    assert list(inventory.states) == [5, 3]
    assert inventory.issues == [
        StateIssue("missing_id", "b.txt"),
        StateIssue("duplicate_id", "5"),
    ]
    first = read_state_inventory([("a.txt", "id = 1\n" + many)]).states[1]
    assert first == list(range(1, MAX_VP_SLOTS + 1))


def test_vp_key_ids_keeps_digits_as_written() -> None:
    """Keys are matched at the line start and returned as digit strings."""
    lines = [
        "l_english:\n",
        ' VICTORY_POINTS_7:0 "Warsaw"\n',
        ' VICTORY_POINTS_007: "Padded"\n',
        ' X_VICTORY_POINTS_8: "not a key"\n',
    ]
    assert vp_key_ids(lines) == {"7", "007"}


def test_loc_entries_and_line_pattern(tmp_path: Path) -> None:
    """Only well-formed entry lines are read, in order, with repeats kept.

    Args:
        tmp_path: Temporary folder from pytest.
    """
    path = tmp_path / "x_l_english.yml"
    path.write_bytes(
        b'\xef\xbb\xbfl_english:\n # comment\n KEY_A:0 "a"\n KEY_B: "b c"\n KEY_A: "again"\n'
    )
    assert loc_entries(path) == [("KEY_A", "a"), ("KEY_B", "b c"), ("KEY_A", "again")]
    assert LOC_LINE.match('KEY: "no leading space"') is None


def test_sha256_file_variants(tmp_path: Path) -> None:
    """Upper case and CRLF folding change only the spelling or the input.

    Args:
        tmp_path: Temporary folder from pytest.
    """
    crlf, lf, empty = tmp_path / "crlf.txt", tmp_path / "lf.txt", tmp_path / "empty"
    crlf.write_bytes(b"a\r\nb\r\n")
    lf.write_bytes(b"a\nb\n")
    empty.write_bytes(b"")
    assert sha256_file(empty) == EMPTY_SHA256
    assert sha256_file(empty, upper=True) == EMPTY_SHA256.upper()
    assert sha256_file(crlf) != sha256_file(lf)
    assert sha256_file(crlf, fold_crlf=True) == sha256_file(lf)
