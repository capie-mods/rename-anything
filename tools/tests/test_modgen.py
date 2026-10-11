"""Unit tests of the generator slices in ``tools/modgen``.

Run with ``uv run pytest``. Most tests use a small made-up state table. The
last test regenerates the whole mod into memory from the real game files and
compares it with ``mod/`` byte for byte; it is skipped when the HOI4
installation is not present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from modgen import build
from modgen.charset import CHARS, CODE, DISPLAY_ORDER, FORBIDDEN, LAST_CODE, PL_UPPER
from modgen.common import LANGS, MAXLEN, MOD, STATE_BUCKET, VP_SLOTS, slots_expr
from modgen.features import cities, cooldown, inline_editor, input_window, localisation
from modgen.features.text_buffers import INPUT_BUFFER, slot_tables
from modgen.features.textures import gen_textures, tga
from modgen.gui import btn, gridbox, txt
from modgen.output import DiskSink, MemorySink, encode_text
from modgen.script import defined_text
from rncommon.game_data import (
    DEFAULT_GAME,
    GameInstallation,
    read_state_inventory,
    vp_key_ids,
)

SAMPLE_STATES = {1: [10, 11], 64: [700], 65: [], 130: [5, 6, 7, 8, 9]}
"""Small state table spanning three ID buckets, with an empty and a full state."""

SAMPLE_KEYS = {10, 700, 5}
"""Provinces of :data:`SAMPLE_STATES` that have a vanilla name key."""

TGA_HEADER_SIZE = 18
"""Size of the TGA header."""

BYTES_PER_PIXEL = 4
"""BGRA pixel size."""


def test_charset_is_complete_and_safe() -> None:
    """Codes 1..84 are dense, invertible and free of forbidden characters."""
    assert sorted(CHARS) == list(range(1, LAST_CODE + 1))
    assert all(CODE[c] == code for code, c in CHARS.items())
    assert not FORBIDDEN & set(CHARS.values())
    assert sorted(DISPLAY_ORDER) == list(range(1, LAST_CODE + 1))
    assert CHARS[LAST_CODE] == PL_UPPER[-1]


def test_defined_text_format() -> None:
    """The builder writes the exact block layout of the generated files."""
    block = defined_text("RN_X", [("check_variable = { a = 1 }", "K1")], "K0")
    assert block == (
        "defined_text = {\n\tname = RN_X\n"
        "\ttext = { trigger = { check_variable = { a = 1 } } localization_key = K1 }\n"
        "\ttext = { localization_key = K0 }\n}\n"
    )


def test_slot_tables_cover_every_slot_and_code() -> None:
    """One block per slot, each with the length guard, every code and a fallback."""
    text = slot_tables([INPUT_BUFFER])
    assert text.count("defined_text = {") == MAXLEN
    assert text.count("localization_key = RN_CH_") == MAXLEN * (LAST_CODE + 2)
    assert "NOT = { check_variable = { rn_len > 31 } }" in text


def test_slots_expr() -> None:
    """A buffer expression concatenates all slots in order."""
    expr = slots_expr("B")
    assert expr.startswith("[ROOT.RN_B_0][ROOT.RN_B_1]")
    assert expr.endswith(f"[ROOT.RN_B_{MAXLEN - 1}]")


def test_gui_builders() -> None:
    """Element builders omit empty attributes and keep the two-tab indentation."""
    assert txt("n", 1, 2, "K").startswith('\t\tinstantTextBoxType = { name = "n"')
    button = btn("b", 3, 4, "GFX_x")
    assert "buttonText" not in button
    assert "shortcut" not in button
    assert 'shortcut = "RETURN"' in btn("b", 3, 4, "GFX_x", shortcut="RETURN")
    assert "slotsize = { width = 10 height = 5 }" in gridbox("g", (0, 0), (10, 50), 5)


def test_vp_lookup_uses_buckets_and_fallback_names() -> None:
    """Only buckets with a VP in the slot get a branch; unnamed VPs get ``#<id>``."""
    loc = cities.vp_name_loc(SAMPLE_STATES, SAMPLE_KEYS)
    assert f"rn_sel_state_id < {STATE_BUCKET}" in loc
    assert "RN_VpName_0_1" in loc
    assert "RN_VpName_4_2" in loc
    assert "RN_VpName_4_0" not in loc
    assert "localization_key = RN_PROVNAME_11" in loc
    assert "localization_key = VICTORY_POINTS_10" in loc
    names = cities.missing_name_entries(SAMPLE_STATES, SAMPLE_KEYS)
    assert names == [f' RN_PROVNAME_{p}: "#{p}"\n' for p in (6, 7, 8, 9, 11)]


def test_load_selected_state_effect() -> None:
    """One branch per state, in table order, with a literal ID and the VP slots."""
    effect = cities.load_selected_state_effect(SAMPLE_STATES)
    assert effect.count("limit = { state = ") == len(SAMPLE_STATES)
    assert "\tif = { limit = { state = 1 }" in effect
    assert "set_variable = { rn_vp_cnt = 0 } }" in effect
    assert f"rn_vp_{VP_SLOTS - 1} = 9" in effect


def test_keyboard_layout() -> None:
    """Every key has a unique name and every letter has a shift twin."""
    keys = input_window.keyboard_keys()
    names = [key[0] for key in keys]
    assert len(names) == len(set(names))
    shifts = [key for key in keys if key[3] == input_window.INVISIBLE_SPRITE]
    assert len(shifts) == len("abcdefghijklmnopqrstuvwxyz")
    assert input_window.key_id("'") == "apos"


def test_cooldown_tooltips_and_wait_texts() -> None:
    """Both categories get every day count and a "more than" text in both languages."""
    loc = cooldown.tooltip_loc()
    assert loc.count("defined_text = {") == len(cooldown.CATEGORIES)
    assert f"rn_cd_left < {cooldown.MORE_THAN_LIMIT}" in loc
    english = cooldown.wait_entries("english")
    polish = cooldown.wait_entries("polish")
    per_category = cooldown.COOLDOWN_LABEL_LIMIT + 1
    assert len(english) == len(polish) == per_category * len(cooldown.CATEGORIES)
    assert '"§RNext state rename possible in 1 day.§!"' in english[0]
    assert "1 dzień" in polish[0]
    assert "ponad 30 dni" in polish[per_category - 1]


def test_cooldown_days_reach_the_effect() -> None:
    """The single cooldown constant is the value of ``rn_cd_days``."""
    assert f"rn_cd_days = {cooldown.COOLDOWN_DAYS} }}" in cooldown.effects()


def test_yml_escape_rejects_quotes() -> None:
    """A double quote inside a UI string is an error, a lone quote is accepted."""
    assert localisation.yml_escape('"') == '"'
    with pytest.raises(ValueError, match="double quote"):
        localisation.yml_escape('a "b"')


def test_localisation_files_share_keys_across_languages() -> None:
    """Every language has the same UI keys; the character table differs only in its header."""
    english = localisation.ui_loc("english").splitlines()[1:]
    polish = localisation.ui_loc("polish").splitlines()[1:]
    assert [line.split(":")[0] for line in english] == [line.split(":")[0] for line in polish]
    chars = {
        lang: localisation.chars_loc(lang, SAMPLE_STATES, SAMPLE_KEYS).split("\n", 1)[1]
        for lang in LANGS
    }
    assert len(set(chars.values())) == 1


def test_inline_editor_copy_covers_every_language() -> None:
    """Script files get the header and cooldown; localisation goes to every language."""
    files = inline_editor.gen_inline_editor()
    assert len({f.relative for f in files}) == len(files)
    scripts = [f for f in files if not f.bom]
    assert all(f.text.startswith("# GENERATED by tools/gen.py from ") for f in scripts)
    assert not any(inline_editor.TOKEN_PREFIX in f.text for f in scripts)
    languages = {f.relative.split("/")[1] for f in files if f.bom}
    assert languages == set(LANGS)


def test_tga_encoding() -> None:
    """A TGA is an 18-byte header plus BGRA rows."""
    image = tga(2, 1, lambda x, _y: (x, 2, 3, 4))
    assert len(image) == TGA_HEADER_SIZE + 2 * BYTES_PER_PIXEL
    assert image[TGA_HEADER_SIZE:] == bytes((3, 2, 0, 4, 3, 2, 1, 4))
    assert set(gen_textures()) >= {"rn_key.tga", "rn_backspace_icon.tga"}


def test_sinks_encode_the_same(tmp_path: Path) -> None:
    """Disk and memory sinks store identical bytes; CRLF becomes LF and BOMs are added.

    Args:
        tmp_path: Temporary folder from pytest.
    """
    memory, disk = MemorySink(), DiskSink(tmp_path)
    for sink in (memory, disk):
        sink.write_text("a/b.yml", "x\r\ny", bom=True)
        sink.write_bytes("c.bin", b"\x00")
    assert memory.files["a/b.yml"] == encode_text("x\ny", bom=True) == b"\xef\xbb\xbfx\ny"
    assert (tmp_path / "a" / "b.yml").read_bytes() == memory.files["a/b.yml"]
    assert (tmp_path / "c.bin").read_bytes() == b"\x00"


def test_build_writes_every_file_once() -> None:
    """A run on the sample table produces the legacy files and both loc files per language."""
    sink = MemorySink()
    build.write_all(sink, SAMPLE_STATES, SAMPLE_KEYS)
    for name in (build.SCRIPTED_LOC_FILE, build.EFFECTS_FILE, build.GUI_FILE, build.GFX_FILE):
        assert name in sink.files
    for lang in LANGS:
        assert f"localisation/{lang}/rename_anything_l_{lang}.yml" in sink.files
    gui = sink.files[build.GUI_FILE].decode("utf-8")
    assert gui.count("{") == gui.count("}")
    summary = build.summary(SAMPLE_STATES, SAMPLE_KEYS)
    assert summary == "states: 4, states with VPs: 3, VP slots: 8, VPs without loc key: 5"


@pytest.mark.skipif(
    not GameInstallation(DEFAULT_GAME).has_state_history(), reason="HOI4 is not installed"
)
def test_generator_reproduces_committed_mod() -> None:
    """Regenerate into memory and compare with ``mod/`` byte for byte."""
    game = GameInstallation(DEFAULT_GAME)
    states = dict(sorted(read_state_inventory(game.state_histories()).states.items()))
    keys = {int(i) for i in vp_key_ids(game.english_localisation_lines())}
    sink = MemorySink()
    build.write_all(sink, states, keys)
    for relative, data in sink.files.items():
        assert (MOD / Path(relative)).read_bytes() == data, relative
