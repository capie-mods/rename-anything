"""Tests of the CAPIE API level 8 feature: the country map colour.

They run the VM cases of ``inline_checks.colour_cases`` (the real effects of
``tools/inline_editor`` and the generated catalogs in ``mod/``) one group at a time, plus
checks of the generator's inputs: the palette, the game colour reader, the colour rule and
the removal of the party ideology name. ``tools/tests/check_inline_editor.py`` runs the same
VM cases.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from inline_checks import colour_cases
from inline_checks.constants import MOD, SOURCE
from modgen.features import colour_picker, colours, switches


@pytest.fixture(scope="module")
def colour_inputs() -> colour_cases.ColourInputs:
    """Load the colour picker's effects once.

    Returns:
        The inputs.
    """
    return colour_cases.ColourInputs()


# ----------------------------------------------------------------------------- generator


def test_presets_are_distinct_whole_channels() -> None:
    """64 to 96 presets in full rows, each channel a whole number 0..255, no colour twice."""
    rgbs = [p.rgb for p in colours.PRESETS]
    assert 64 <= len(rgbs) <= 96  # noqa: PLR2004 - the requested palette size
    assert len(rgbs) % colour_picker.GRID_COLUMNS == 0, "full rows, one hue group per row"
    assert len(set(rgbs)) == len(rgbs)
    assert all(isinstance(c, int) and 0 <= c <= colours.CHANNEL_MAX for rgb in rgbs for c in rgb)
    assert len({p.english for p in colours.PRESETS}) == len(rgbs)
    assert len({p.polish for p in colours.PRESETS}) == len(rgbs)


def test_parse_colours() -> None:
    """colors.txt entries: rgb, HSV (any case), a bare block, comments, and the last entry wins."""
    text = """
    GER = {
        color = HSV { 0.1 0.15 0.4 }   # a comment { }
        color_ui = rgb { 138 155 116 }
    }
    BEL = { color 	 = rgb { 193 171 8  }
            color_ui = rgb { 251 222 10 } }
    XXX = { color = { 1 2 3 } }
    BAD = { color = rgb { 1 2 } }
    OUT = { color = rgb { 1 2 300 } }
    ENG = { color = rgb { 1 1 1 } }
    ENG = { color = rgb { 201 56 93 } }
    """
    assert colours.parse_colours(text) == {
        "GER": (102, 96, 87),
        "BEL": (193, 171, 8),
        "XXX": (1, 2, 3),
        "ENG": (201, 56, 93),
    }


def test_hex_code() -> None:
    """``#RRGGBB`` with upper-case digits."""
    assert colours.hex_code((30, 90, 160)) == "#1E5AA0"
    assert colours.hex_code((0, 0, 255)) == "#0000FF"


def test_native_effect_and_code_loc() -> None:
    """The generated game colour lookup and the code texts."""
    natives = colours.NativeColours({"FRA": (57, 113, 228)}, {"FRA_x": (1, 2, 3)})
    lines = colours._native_effect(natives)  # noqa: SLF001 - the generator's own fragment
    text = "".join(lines)
    assert text.index("has_cosmetic_tag = FRA_x") < text.index("tag = FRA "), "cosmetic first"
    assert "set_temp_variable = { rn_cp_nr = 57 }" in text
    loc = colours.scripted_loc()
    for i in range(colours.CODE_MAX):
        assert f"name = RN_CP_IN_{i}\n" in loc
    for i in range(1, 7):
        assert f"name = RN_CP_HX{i}\n" in loc
    assert "RN_CP_IN_MSG" in loc


def test_keypad_layout() -> None:
    """16 digits, the separator, Delete and Clear; shortcuts are unique; the keys fit the window."""
    keys = colour_picker.keys()
    assert len(keys) == 16 + 3
    shortcuts = [k.shortcut for k in keys + colour_picker.shift_keys() if k.shortcut]
    assert len(shortcuts) == len(set(shortcuts))
    assert {"SPACE", "BACKSPACE", "shift+a", "0", "f"} <= set(shortcuts)
    for k in keys:
        w, h = colours.KEY_WIDE if k.wide else colours.KEY
        x, y = k.pos
        assert x >= 0, k
        assert x + w <= colour_picker.WIDTH, k
        assert y + h <= colour_picker.STATUS_Y, k


def test_colour_geometry() -> None:
    """Both colour windows fit their views; no two controls overlap."""
    colour_cases.check_colour_geometry()


def test_colour_rule() -> None:
    """The colour rule: default "own country and subjects", then own only, any country, off."""
    rules = switches.rules()
    block = rules[rules.index("rn_feature_colour = {") :]
    block = block[: block.index("\n}\n")]
    names = [line.split('"')[1] for line in block.splitlines() if "\t\tname = " in line]
    assert names == [
        "RN_FEATURE_COLOUR_ON",
        "RN_FEATURE_COLOUR_OWN",
        "RN_FEATURE_COLOUR_ANY",
        "RN_FEATURE_COLOUR_OFF",
    ]
    triggers = switches.triggers()
    assert "rn_feature_colour_own_only = {" in triggers
    assert "option = RN_FEATURE_COLOUR_ANY" in triggers
    for lang in ("english", "polish"):
        loc = switches.localisation(lang)
        for key in ("ON", "OWN", "OWN_DESC", "ANY", "ANY_DESC"):
            assert f" RN_RULE_FEATURE_COLOUR_{key}:0 " in loc, (lang, key)


def test_party_ideology_name_is_gone() -> None:
    """The ruling party ideology name (CONTRACT 20) is removed: no file, no switch, no writer."""
    assert not any(f.id == "subideology" for f in switches.FEATURES)
    for root in (MOD, SOURCE):
        assert not list(root.rglob("rn_subideology*")), root
        for path in root.rglob("*.txt"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            assert "capie_sn_" not in text, path
            assert "rnsi" not in text, path


# ----------------------------------------------------------------------------- VM cases


def test_colour_picking(colour_inputs: colour_cases.ColourInputs) -> None:
    """The start colour, presets, steppers, the clamp, the preview frame and the hex digits."""
    assert colour_cases.run_picking(colour_inputs) > len(colours.PRESETS)


def test_colour_code(colour_inputs: colour_cases.ColourInputs) -> None:
    """Hex and R G B codes, each refusal with its message, Delete, Clear and Apply."""
    assert colour_cases.run_code(colour_inputs) > len(colour_cases.CODES)


@pytest.mark.parametrize(("code", "state", "rgb"), colour_cases.CODES)
def test_colour_code_states(
    colour_inputs: colour_cases.ColourInputs,
    code: str,
    state: int,
    rgb: tuple[int, int, int] | None,
) -> None:
    """Each typed code gets its state; only a valid one changes the colour."""
    vm = colour_inputs.vm()
    colour_cases.open_own(vm)
    colour_cases.preset(vm, 1)
    colour_cases.type_code(vm, code)
    assert colour_cases.code_state(vm) == state
    assert colour_cases.reference(code.upper()) == (state, rgb)
    want = colour_cases.expected_colour(code.upper(), colours.PRESETS[0].rgb)
    assert colour_cases.picked(vm) == want
    assert (rgb is None) or want == rgb


def test_colour_apply_restore_cooldown_and_api_gate(
    colour_inputs: colour_cases.ColourInputs,
) -> None:
    """Apply's gates (API level 8, capie_colour, switch, rights, code, cooldown) and Reset."""
    assert colour_cases.run_apply(colour_inputs) > len(colour_cases.REJECTIONS)


@pytest.mark.parametrize(("cap", "colour", "err"), [(1, 1, 10), (7, 1, 15), (8, 0, 16), (9, 1, 0)])
def test_colour_api_level(
    colour_inputs: colour_cases.ColourInputs, cap: int, colour: int, err: int
) -> None:
    """Only CAPIE API level 8 or higher with the colour layer on can apply a colour."""
    vm = colour_inputs.vm()
    colour_cases.open_own(vm)
    colour_cases.preset(vm, 5)
    assert colour_cases.apply(vm, cap=cap, colour=colour) == err
    assert (colour_cases.layer(vm, "FRA") is None) == (err != 0)


def test_colour_restore_needs_no_capie(colour_inputs: colour_cases.ColourInputs) -> None:
    """A colour set earlier can be removed in a game without CAPIE."""
    vm = colour_inputs.vm()
    vm.temp = {"rn_cc_r": Decimal(1), "rn_cc_g": Decimal(2), "rn_cc_b": Decimal(3)}
    vm.scoped("FRA", lambda: vm.run("rn_country_colour_carrier_set"))
    colour_cases.open_own(vm)
    assert colour_cases.reset(vm) == 0
    assert colour_cases.layer(vm, "FRA") is None


RULE_MATRIX = {
    "RN_FEATURE_COLOUR_ON": {"FRA", "POL"},
    "RN_FEATURE_COLOUR_OWN": {"FRA"},
    "RN_FEATURE_COLOUR_ANY": {"FRA", "POL", "ITA"},
    "RN_FEATURE_COLOUR_OFF": set(),
}
"""Colour rule option to the countries whose colour the single player may change (FRA is the
player, POL its subject, ITA a stranger)."""


@pytest.mark.parametrize("option", sorted(RULE_MATRIX))
def test_colour_rule_matrix(colour_inputs: colour_cases.ColourInputs, option: str) -> None:
    """Whose picker opens and applies under each option of the colour rule (single player)."""
    for tag in ("FRA", "POL", "ITA"):
        allowed = tag in RULE_MATRIX[option]
        vm = colour_inputs.vm()
        vm.rules[colour_cases.RULE] = option
        if tag == "FRA":
            colour_cases.open_own(vm)
        else:
            colour_cases.open_sub(vm, tag)
        flag = "rn_cp_open_own" if tag == "FRA" else "rn_cp_open_sub"
        assert colour_cases.is_open(vm, flag) == allowed, (option, tag)
        if allowed:
            colour_cases.preset(vm, 7)
            assert colour_cases.apply(vm) == 0, (option, tag)
            assert colour_cases.layer(vm, tag) == colours.PRESETS[6].rgb


def test_colour_rule_cases(colour_inputs: colour_cases.ColourInputs) -> None:
    """Rights at Apply, multiplayer host, the switches; the diplomatic action's structure."""
    assert colour_cases.run_subject(colour_inputs) > 0
    colour_cases.check_action()


def test_colour_my_colour(colour_inputs: colour_cases.ColourInputs) -> None:
    """A subject's "My colour": the overlord's layer, else its game colour, else error 18."""
    assert colour_cases.run_mine(colour_inputs) > 0


def test_colour_daily(colour_inputs: colour_cases.ColourInputs) -> None:
    """The daily cosmetic tag check."""
    assert colour_cases.run_daily(colour_inputs) > 0


def test_colour_mutations_are_caught(colour_inputs: colour_cases.ColourInputs) -> None:
    """Removing any guard of Apply, Reset, the rule, My colour, the code or the carrier fails."""
    assert colour_cases.run_colour_mutations(colour_inputs) > 0
