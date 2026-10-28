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
from modgen.features import (
    cities,
    cooldown,
    flag_picker,
    flags,
    inline_editor,
    input_window,
    legacy_field,
    localisation,
    portraits,
    refresh,
    switches,
)
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
    """``rn_cd_days`` takes the in-place editor's length, the single source read from the game rule."""
    effects = cooldown.effects()
    assert "rn_ip_cooldown_days = yes" in effects
    assert "set_temp_variable = { rn_cd_days = temp_var:rn_ip_cd_days }" in effects


def test_cooldown_rule_default_is_the_constant() -> None:
    """The default branch of ``rn_ip_cooldown_days`` is :data:`COOLDOWN_DAYS`; every rule option has a branch."""
    from modgen.features.inline_editor import gen_inline_editor

    files = {f.relative: f.text for f in gen_inline_editor()}
    source = files["common/scripted_effects/rn_inline_cooldown.txt"]
    body = source[source.index("rn_ip_cooldown_days = {") :]
    body = body[: body.index("\n}\n")]
    assert f"else = {{\n\t\tset_temp_variable = {{ rn_ip_cd_days = {cooldown.COOLDOWN_DAYS} }}" in body
    rules = files["common/game_rules/rn_rules.txt"]
    for option, days in (("RN_COOLDOWN_OFF", 0), ("RN_COOLDOWN_1", 1), ("RN_COOLDOWN_15", 15), ("RN_COOLDOWN_30", 30)):
        assert f'name = "{option}"' in rules
        assert f"option = {option} }} }}\n\t\tset_temp_variable = {{ rn_ip_cd_days = {days} }}" in body


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
    build.write_all(
        sink,
        states,
        keys,
        flags.read_catalog(DEFAULT_GAME),
        portraits.read_catalog(DEFAULT_GAME),
    )
    assert flags.CATALOG_EFFECTS in sink.files
    for relative, data in sink.files.items():
        assert (MOD / Path(relative)).read_bytes() == data, relative


SAMPLE_FLAGS = [
    "POL_neutrality",
    "POL_fascism",
    "POL_KINGDOM_neutrality",
    "POL_KINGDOM_RUS",
    "GER",
    "GER_fascism",
    "SCA_UNIFIED_neutrality",
    "bad.name",
]
"""Flag stems of the sample catalog: tag variants, cosmetic variants, an "Other" key, a bad name."""


def test_flag_packing_follows_the_contract() -> None:
    """``POL_`` packs as CONTRACT 17.3 shows; a path character is refused."""
    assert flags.pack("POL_") == [174694, 258048]
    assert flags.pack("abc") == [1 * 4096 + 2 * 64 + 3]
    with pytest.raises(ValueError, match="not a flag stem"):
        flags.pack("gfx/flags")
    assert flags.split_stem("POL_KINGDOM_neutrality") == ("POL_KINGDOM", "neutrality")
    assert flags.split_stem("GER") == ("GER", None)


def test_flag_catalog_pools_labels_and_letters() -> None:
    """Pools follow design 2.2, labels name game keys only, letters follow English names."""
    english = {
        "POL": "Poland",
        "GER": "Germany",
        "POL_KINGDOM_neutrality": "Kingdom of Poland",
        "fascism": "Fascist",
        "neutrality": "Non-Aligned",
    }
    cat = flags.build_catalog(
        SAMPLE_FLAGS, SAMPLE_FLAGS, ["POL", "GER"], english, ["POL_KINGDOM", "OTHER"]
    )
    assert "bad.name" not in cat.stems
    index = cat.index
    by_tag = {g.tag: [cat.stems[i - 1] for i in g.indices] for g in cat.groups}
    assert by_tag["POL"] == [
        "POL_fascism",
        "POL_neutrality",
        "POL_KINGDOM_neutrality",
        "POL_KINGDOM_RUS",
    ]
    assert by_tag["GER"] == ["GER", "GER_fascism"]
    assert by_tag[""] == ["SCA_UNIFIED_neutrality"]
    assert cat.groups[-1].tag == ""
    assert cat.labels[index["POL_fascism"] - 1] == "$POL$ ($fascism$)"
    assert cat.labels[index["POL_KINGDOM_RUS"] - 1] == "$POL$ 4"
    assert cat.labels[index["SCA_UNIFIED_neutrality"] - 1] == "$RN_FP_OTHER_FLAG$ 1 ($neutrality$)"
    assert not any(s in label for s in cat.stems for label in cat.labels if f"${s}$" not in label)
    assert cat.letters[flags.LETTERS.index("G")] == ("GER",)
    assert cat.letters[flags.LETTERS.index("P")] == ("POL",)
    assert {"POL_KINGDOM", "OTHER", "SCA_UNIFIED"} <= set(cat.cosmetics)
    assert flags.fingerprint(cat.stems) == flags.fingerprint(list(cat.stems))
    assert flags.fingerprint(cat.stems) != flags.fingerprint(cat.stems[1:])


def test_flag_picker_layout_constants() -> None:
    """The grid ends left of the Apply column and the rows fill the same rectangle."""
    assert flag_picker.GRID_X + flag_picker.GRID_W < flag_picker.APPLY_X
    assert flag_picker.ROW[0] * flag_picker.ROW_COLUMNS == flag_picker.GRID_W
    rows_h = flag_picker.ROW[1] * flag_picker.ROW_ROWS
    assert rows_h == flag_picker.CELL[1] * flag_picker.GRID_ROWS
    assert flag_picker.letter_x(len(flags.LETTERS)) + flag_picker.LETTER_W <= flag_picker.OTHER_X
    assert flag_picker.OTHER_X + flag_picker.OTHER_W <= flag_picker.WIDTH


GATED_GUIS = (
    "rn_main_country_gui",
    "rn_main_chars_gui",
    "rn_main_states_gui",
    "rn_main_cities_gui",
    "rn_input_gui",
)
"""Legacy scripted GUIs that update only when the refresh counter changes."""

ENTRY_EFFECTS = ("rn_open_main", "rn_close_all", "rn_set_tab", "rn_open_input", "rn_cancel_input")
"""Hand-written effects that other entry points (decision, state view) call; each bumps the gate."""


def _gui_blocks(text: str) -> dict[str, str]:
    """Split the scripted GUI file into its top-level GUI blocks.

    Args:
        text: Contents of the scripted GUI file.

    Returns:
        GUI name to its block text.
    """
    blocks: dict[str, str] = {}
    lines = text.splitlines(keepends=True)
    name = ""
    for line in lines:
        if line.startswith("\t") and not line.startswith("\t\t") and line.rstrip().endswith("{"):
            name = line.strip().split(" ")[0]
            blocks[name] = ""
        if name:
            blocks[name] += line
    return blocks


def _click_bodies(block: str) -> dict[str, str]:
    """Return the body of every click effect of one scripted GUI block.

    Args:
        block: Text of one scripted GUI.

    Returns:
        Click effect name to the text between its braces.
    """
    bodies = {}
    for line_start, line in _line_offsets(block):
        name = line.strip().split(" ", 1)[0]
        if not name.endswith("_click") or "= {" not in line:
            continue
        opening = line_start + line.index("{")
        depth = 0
        for i in range(opening, len(block)):
            depth += {"{": 1, "}": -1}.get(block[i], 0)
            if depth == 0:
                bodies[name] = block[opening + 1 : i]
                break
    return bodies


def _line_offsets(text: str) -> list[tuple[int, str]]:
    """Return every line with the offset where it starts.

    Args:
        text: Any text.

    Returns:
        ``(offset, line)`` pairs.
    """
    out = []
    offset = 0
    for line in text.splitlines(keepends=True):
        out.append((offset, line))
        offset += len(line)
    return out


def test_every_keyboard_key_bumps_after_changing_the_buffer() -> None:
    """Each key (digits, letters, Polish letters, shift twins, Caps, Backspace, Space, Clear).

    Its click effect in the input window runs the key's own effect first and
    the refresh bump last.
    """
    bodies = _click_bodies(_gui_blocks(build.scripted_gui())["rn_input_gui"])
    keys = input_window.keyboard_keys()
    assert {f"{name}_click" for name, *_ in keys} <= set(bodies)
    assert len([k for k in keys if k[0].startswith("rn_key_pl")]) == len(PL_UPPER)
    for name, *_rest, effect in keys:
        body = bodies[f"{name}_click"].strip()
        assert body == f"{effect} {refresh.TOUCH}", name
    for name in ("rn_cancel_click", "rn_apply_click"):
        assert bodies[name].strip().endswith(refresh.TOUCH), name


def test_refresh_gate_covers_every_click() -> None:
    """Gated GUIs carry ``dirty`` and every click effect bumps the counter on ROOT last."""
    blocks = _gui_blocks(build.scripted_gui())
    assert set(GATED_GUIS) | {"rn_state_view_gui", legacy_field.MODEL} == set(blocks)
    # The CAPIE field window is not gated (CAPIE reads it), but it bumps the gate after
    # Apply and the mode switch, because the keyboard window it hands over to is gated.
    field = _click_bodies(blocks[legacy_field.MODEL])
    assert "dirty" not in blocks[legacy_field.MODEL]
    for click in (f"{legacy_field.MODEL}_apply_click", "rn_lg_use_keyboard_click"):
        assert field[click].strip().endswith(f"{refresh.TOUCH_EFFECT} = yes"), click
    touch = refresh.TOUCH
    for name in GATED_GUIS:
        block = blocks[name]
        assert refresh.dirty_line() in block, name
        bodies = _click_bodies(block)
        assert bodies, name
        for click, body in bodies.items():
            # Last statement, once: the window refreshes only after every change (PID45148).
            assert body.rstrip().endswith(touch), (name, click)
            assert body.count(touch) == 1, (name, click)
            assert body.rstrip()[: -len(touch)].strip(), (name, click)
    view = blocks["rn_state_view_gui"]
    assert "dirty" not in view, "the state view scope changes without an effect"
    assert touch in view, "the state view reset bumps the player's gate"


def test_refresh_gate_counter_and_daily_on_action() -> None:
    """The counter wraps before the variable range and the daily on-action is limited."""
    effect = refresh.touch_effect()
    assert f"add_to_variable = {{ {refresh.DIRTY_VARIABLE} = 1 }}" in effect
    assert f"{refresh.DIRTY_VARIABLE} > {refresh.DIRTY_WRAP}" in effect
    assert refresh.TOUCH_EFFECT + " = {" in build.effects(SAMPLE_STATES)
    daily = refresh.on_actions()
    assert "on_daily = {" in daily
    assert "limit = { is_ai = no has_country_flag = rn_open }" in daily
    sink = MemorySink()
    build.write_all(sink, SAMPLE_STATES, SAMPLE_KEYS)
    assert refresh.ON_ACTIONS_FILE in sink.files


def test_hand_written_entries_bump_the_gate_and_character_apply_is_light() -> None:
    """Entry effects bump the gate; a character Apply rebuilds only the character list."""
    hand = (MOD / "common" / "scripted_effects" / "rename_anything_effects.txt").read_text(
        encoding="utf-8"
    )
    for name in ENTRY_EFFECTS:
        body = hand.split(f"\n{name} = {{", 1)[1].split("\n}", 1)[0]
        last = body.rstrip().splitlines()[-1].split("#", 1)[0].strip()
        assert last == f"{refresh.TOUCH_EFFECT} = yes", name
        assert body.count(f"{refresh.TOUCH_EFFECT} = yes") == 1, name
    lists = hand.split("\nrn_refresh_lists = {", 1)[1].split("\n}", 1)[0]
    chars = hand.split("\nrn_refresh_chars = {", 1)[1].split("\n}", 1)[0]
    assert "rn_refresh_chars = yes" in lists
    assert "every_owned_state" in lists
    assert "every_owned_state" not in chars
    assert chars.count("every_character") == 2  # noqa: PLR2004 - leader first, then the rest
    apply = input_window.apply_input_effect()
    assert "rn_refresh_chars = yes" in apply
    assert "rn_refresh_lists" not in apply


def test_legacy_field_follows_the_capie_grammar() -> None:
    """The field mode is a CAPIE v1.1 grammar editor and the two modes exclude each other."""
    blocks = _gui_blocks(build.scripted_gui())
    field = blocks[legacy_field.MODEL]
    keyboard = blocks["rn_input_gui"]
    flag = legacy_field.KEYBOARD_FLAG
    assert (
        f"visible = {{ has_country_flag = rn_input NOT = {{ has_country_flag = {flag} }} }}"
        in field
    )
    assert f"visible = {{ has_country_flag = rn_input has_country_flag = {flag} }}" in keyboard
    assert f"{legacy_field.EPOCH_CARRIER}_visible = {{ always = no }}" in field
    assert "rn_apply_click" in keyboard
    assert "rn_lg_use_field_click" in keyboard
    gui = build.gui()
    window = gui.split(f'name = "{legacy_field.MODEL}"', 1)[1].split("\n\t}\n", 1)[0]
    assert f'editBoxType = {{ name = "{legacy_field.FIELD}"' in window
    assert "ignore_enter = yes" in window
    assert f'name = "{legacy_field.MODEL}_apply"' in window
    assert 'shortcut = "RETURN"' in window
    assert f'name = "{legacy_field.EPOCH_CARRIER}"' in window
    assert "[?ROOT.rn_lg_epoch|0]" in window


def test_host_switches_cover_every_feature() -> None:
    """One rule, one trigger and one tooltip line per feature; texts in English and Polish."""
    rules, triggers, loc = switches.rules(), switches.triggers(), switches.scripted_loc()
    english, polish = switches.localisation("english"), switches.localisation("polish")
    ids = {f.id for f in switches.FEATURES}
    assert {"country", "leader", "party", "flag", "portrait", "states"} <= ids
    for f in switches.FEATURES:
        up = f.id.upper()
        assert f"rn_feature_{f.id} = {{" in rules
        assert f"{switches.trigger_name(f.id)} = {{" in triggers
        assert f"name = RN_FEAT_{up}\n" in loc
        for text in (english, polish):
            assert f' RN_RULE_FEATURE_{up}:0 "Rename Anything: ' in text
            assert f" RN_FEAT_{up}_ALLOWED:0 " in text
    assert "\tdesc =" not in rules.replace("\t\tdesc =", "")
    assert "Host wyłączył tę opcję w tej grze." in polish
    assert "The host has turned this off for this game." in english
