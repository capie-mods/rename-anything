"""Colour picker (CAPIE API level 8, CONTRACT section 19): a VM over the real effects.

:class:`~inline_checks.flag_cases.FlagVM` runs the hand-written picker and carrier
(``tools/inline_editor``) together with the generated preset, game colour and cosmetic
lookups (``mod/common/scripted_effects/rn_colour_catalog.txt``) over several countries:

* opening (the layer's colour, else the game's colour, else mid grey), every preset, the
  red/green/blue steppers (1, 10, 50) with their 0..255 clamp, the preview frame and the
  ``#RRGGBB`` digits;
* the colour code: hex and three numbers, every refusal (short, long, a letter among the
  numbers, above 255, not three numbers), Delete and Clear, the length cap, and Apply refusing
  an invalid code;
* Apply: the gates in the spec's order (epoch header, ``capie_cap >= 8``,
  ``capie_colour = 1``, host switches, rights, the typed code, cooldown), each refusal without
  a write on the target, and the carrier's exact CONTRACT 19.5 statement order,
  ``capie_cc_rev`` last;
* "Reset": the same rules without CAPIE, nothing to do without a layer;
* the colour rule (own country only; own country and subjects; any country for the host; off),
  the subject's "My colour" (the overlord's layer, else its game colour, else a refusal), the
  daily cosmetic tag check, and mutations that the cases must catch.

The VM is not the HOI4 parser and proves nothing about the game, CAPIE or multiplayer.
"""

from __future__ import annotations

import copy
import random
from decimal import Decimal
from typing import Any

from inline_checks.constants import ACTIONS_Y, MOD, PANEL_WIDTH, SOURCE, VM_TODAY
from inline_checks.fixtures import parse
from inline_checks.flag_cases import FlagVM, Inputs, Ref, decode
from inline_checks.geometry import disjoint, inside
from inline_checks.tree import declarations, get, walk, xy
from modgen.features import colour_picker
from modgen.features.colours import (
    CODE_MAX,
    KEY,
    KEY_SPRITE,
    KEY_WIDE,
    KEY_WIDE_SPRITE,
    MARK,
    MARK_SPRITE,
    PRESETS,
    PREVIEW_FRAME,
    PREVIEW_SPRITE,
    SEPARATOR,
    SWATCH,
    hex_code,
    preview_frame,
    swatch_sprite,
)
from modgen.features.cooldown import COOLDOWN_DAYS

ERR = {
    "capie": 10,
    "cooldown": 11,
    "stale": 12,
    "setup": 13,
    "old": 15,
    "layer": 16,
    "code": 17,
    "mine": 18,
    "rights": 20,
    "off": 21,
}
"""Colour picker error codes (temp ``rn_cv1_err``, stored as ``rn_cv1_st_err``)."""

API_LEVEL = 8
"""CAPIE API level of the colour layer."""

GREY = (128, 128, 128)
"""Starting colour of the picker for a country whose colour script cannot know."""

FRENCH_BLUE = (57, 113, 228)
"""France's colour in the game's ``colors.txt`` (and the "French blue" preset)."""

UNKNOWN = "ZZZ"
"""A tag without a colour in the game's files (another mod's country)."""

RULE = "rn_feature_colour"
"""The colour game rule."""

LAYER = ("capie_cc_r", "capie_cc_g", "capie_cc_b", "capie_cc_cos_len", "capie_cc_ver")
"""Scalar variables of the layer (``capie_cc_rev`` stays after a removal)."""

SET_ORDER = [
    "capie_cc_r",
    "capie_cc_g",
    "capie_cc_b",
    "clear_array:capie_cc_cos",
    "clear_variable:capie_cc_cos_len",
    "capie_cc_ver",
    "capie_cc_rev",
]
"""CONTRACT 19.5 order of a set without a known cosmetic tag (no snapshot)."""

CLEAR_ORDER = [
    "clear_variable:capie_cc_r",
    "clear_variable:capie_cc_g",
    "clear_variable:capie_cc_b",
    "clear_array:capie_cc_cos",
    "clear_variable:capie_cc_cos_len",
    "clear_variable:capie_cc_ver",
    "capie_cc_rev",
]
"""CONTRACT 19.5 order of a removal."""


class ColourInputs(Inputs):
    """The flag VM inputs plus the generated colour catalog effects."""

    def __init__(self) -> None:
        """Load the source, the flag catalog and the colour catalog."""
        super().__init__()
        self.effects.update(
            declarations(MOD / "common" / "scripted_effects", "rn_colour_catalog.txt")
        )


def capie(
    vm: FlagVM,
    *,
    cap: int = API_LEVEL,
    colour: int = 1,
    epoch: Any = None,  # noqa: ANN401 - Decimal epoch
    host: int | None = None,
) -> None:
    """Put the CAPIE records of a colour editor's Apply into the temps.

    Args:
        vm: VM.
        cap: ``capie_cap``.
        colour: ``capie_colour``.
        epoch: ``capie_epoch``; the stored opening epoch by default.
        host: ``capie_host`` (absent when None).
    """
    root = vm.nations[vm.root]
    vm.temp = {
        "capie_cap": Decimal(cap),
        "capie_ver": Decimal(10600),
        "capie_colour": Decimal(colour),
        "capie_epoch": root.vars.get("rn_cp_epoch", Decimal(0)) if epoch is None else epoch,
        "capie_nf": Decimal(0),
    }
    if host is not None:
        vm.temp["capie_host"] = Decimal(host)


def open_own(vm: FlagVM) -> None:
    """Open the own picker as the politics tab does.

    Args:
        vm: VM.
    """
    vm.temp = {}
    vm.run("rn_cp_open_own")


def open_sub(vm: FlagVM, tag: str) -> None:
    """Open the other-country picker from the diplomacy view of ``tag``.

    Args:
        vm: VM.
        tag: Selected country.
    """
    vm.temp = {}
    vm.scoped(tag, lambda: vm.run("rn_cp_open_sub"))


def is_open(vm: FlagVM, flag: str = "rn_cp_open_sub") -> bool:
    """Return whether a picker is open.

    Args:
        vm: VM.
        flag: ``rn_cp_open_sub`` or ``rn_cp_open_own``.

    Returns:
        The flag is set on the player.
    """
    return flag in vm.nations[vm.root].flags


def preset(vm: FlagVM, n: int) -> None:
    """Click preset ``n``.

    Args:
        vm: VM.
        n: Preset number (1-based).
    """
    vm.temp = {"rn_cp_pick": Decimal(n)}
    vm.run("rn_cp_pick_preset")


def step(vm: FlagVM, channel: int, by: int) -> None:
    """Click a stepper.

    Args:
        vm: VM.
        channel: 1 red, 2 green, 3 blue.
        by: The step.
    """
    vm.temp = {"rn_cp_ch": Decimal(channel), "rn_cp_d": Decimal(by)}
    vm.run("rn_cp_step")


def mine(vm: FlagVM) -> None:
    """Click "My colour".

    Args:
        vm: VM.
    """
    vm.temp = {}
    vm.run("rn_cp_pick_mine")


def type_code(vm: FlagVM, code: str) -> None:
    """Type a colour code on the keypad (a space is the separator).

    Args:
        vm: VM.
        code: Hex digits, decimal digits and spaces.
    """
    for ch in code:
        vm.temp = {"rn_cp_k": Decimal(SEPARATOR if ch == " " else int(ch, 16))}
        vm.run("rn_cp_key")


def key(vm: FlagVM, effect: str) -> None:
    """Press Delete (``rn_cp_key_back``) or Clear (``rn_cp_key_clear``).

    Args:
        vm: VM.
        effect: The key's effect.
    """
    vm.temp = {}
    vm.run(effect)


def code_state(vm: FlagVM) -> int:
    """Return what the typed code is (``rn_cp_in_st``).

    Args:
        vm: VM.

    Returns:
        0..6.
    """
    return int(vm.nations[vm.root].vars["rn_cp_in_st"])


def typed(vm: FlagVM) -> str:
    """Return the typed code as text.

    Args:
        vm: VM.

    Returns:
        Upper-case hex digits and spaces.
    """
    codes = vm.nations[vm.root].arrays.get("rn_cp_in", [])
    return "".join(" " if c == SEPARATOR else f"{int(c):X}" for c in codes)


def picked(vm: FlagVM) -> tuple[int, int, int]:
    """Return the colour shown in the open picker.

    Args:
        vm: VM.

    Returns:
        ``(r, g, b)``.
    """
    v = vm.nations[vm.root].vars
    return int(v["rn_cp_r"]), int(v["rn_cp_g"]), int(v["rn_cp_b"])


def shown_hex(vm: FlagVM) -> str:
    """Return the ``#RRGGBB`` the picker shows (the digits rn_cp_x1..6).

    Args:
        vm: VM.

    Returns:
        The hex code.
    """
    v = vm.nations[vm.root].vars
    return "#" + "".join(f"{int(v[f'rn_cp_x{i}']):X}" for i in range(1, 7))


def layer(vm: FlagVM, tag: str) -> tuple[int, int, int] | None:
    """Return a country's colour layer, or None.

    Args:
        vm: VM.
        tag: Country.

    Returns:
        ``(r, g, b)`` or None.
    """
    v = vm.nations[tag].vars
    if "capie_cc_ver" not in v:
        return None
    assert v["capie_cc_ver"] == 1
    return int(v["capie_cc_r"]), int(v["capie_cc_g"]), int(v["capie_cc_b"])


def set_layer(vm: FlagVM, tag: str, rgb: tuple[int, int, int]) -> None:
    """Give a country a colour layer through the carrier.

    Args:
        vm: VM.
        tag: Country.
        rgb: Colour.
    """
    vm.temp = {f"rn_cc_{c}": Decimal(v) for c, v in zip("rgb", rgb, strict=True)}
    vm.scoped(tag, lambda: vm.run("rn_country_colour_carrier_set"))


def root_err(vm: FlagVM) -> int:
    """Return the status error stored on ROOT.

    Args:
        vm: VM.

    Returns:
        ``rn_cv1_st_err`` or 0.
    """
    return int(vm.nations[vm.root].vars.get("rn_cv1_st_err", 0))


def layer_writes(vm: FlagVM, tag: str) -> list[str]:
    """Return the recorded writes of ``capie_cc_*`` on ``tag``, in order.

    Args:
        vm: VM.
        tag: Country.

    Returns:
        Write labels.
    """
    return [w for t, w in vm.writes if t == tag and "capie_cc_" in w]


def apply(vm: FlagVM, **kwargs: Any) -> int:  # noqa: ANN401 - capie() keywords
    """Press Apply with the given CAPIE records; return the stored error.

    Args:
        vm: VM.
        **kwargs: :func:`capie` keywords.

    Returns:
        ``rn_cv1_st_err``.
    """
    capie(vm, **kwargs)
    vm.run("rn_cp_apply")
    return root_err(vm)


def reset(vm: FlagVM) -> int:
    """Press "Reset" (no CAPIE records); return the stored error.

    Args:
        vm: VM.

    Returns:
        ``rn_cv1_st_err``.
    """
    vm.temp = {}
    vm.run("rn_cp_reset")
    return root_err(vm)


def native(vm: FlagVM, tag: str) -> tuple[int, int, int] | None:
    """Return the generated game colour of a country.

    Args:
        vm: VM.
        tag: Country.

    Returns:
        ``(r, g, b)`` or None when unknown.
    """
    vm.temp = {}
    vm.scoped(tag, lambda: vm.run("rn_cp_native"))
    if vm.temp["rn_cp_nk"] != 1:
        return None
    return int(vm.temp["rn_cp_nr"]), int(vm.temp["rn_cp_ng"]), int(vm.temp["rn_cp_nb"])


# ----------------------------------------------------------------------------- picking


def run_picking(inp: ColourInputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """Opening, every preset, the steppers, the clamp, the preview frame and the hex digits.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    vm = inp.vm()
    assert native(vm, "FRA") == FRENCH_BLUE, "the game's colour of France"
    assert PRESETS[[p.english for p in PRESETS].index("French blue")].rgb == FRENCH_BLUE
    open_own(vm)
    root = vm.nations["FRA"]
    assert "rn_cp_open_own" in root.flags
    assert root.vars["rn_cp_target"] == Ref("FRA")
    assert picked(vm) == FRENCH_BLUE, "opens at the game's colour"
    assert shown_hex(vm) == hex_code(FRENCH_BLUE)
    assert "rn_cp_changed" not in root.flags, "Apply stays disabled until a change"
    cases = 2
    for n, p in enumerate(PRESETS, start=1):
        preset(vm, n)
        assert picked(vm) == p.rgb, p.english
        assert root.vars["rn_cp_sel"] == n
        assert root.vars["rn_cp_frame"] == preview_frame(p.rgb), p.english
        assert shown_hex(vm) == hex_code(p.rgb), p.english
        cases += 1
    for bad in (0, len(PRESETS) + 1, -1):
        before = picked(vm)
        preset(vm, bad)
        assert picked(vm) == before, bad
        cases += 1
    # Steppers 1, 10 and 50: a change leaves the preset; the clamp holds at both ends.
    preset(vm, 1)
    step(vm, 1, 1)
    assert picked(vm) == (201, 30, 45)
    assert root.vars["rn_cp_sel"] == 0
    step(vm, 1, -1)
    assert root.vars["rn_cp_sel"] == 1, "back on the preset"
    step(vm, 2, 10)
    step(vm, 3, -10)
    assert picked(vm) == (200, 40, 35)
    for _ in range(6):
        step(vm, 1, 50)
        step(vm, 2, -50)
    step(vm, 3, 50)
    assert picked(vm) == (255, 0, 85)
    assert root.vars["rn_cp_frame"] == preview_frame((255, 0, 85))
    assert shown_hex(vm) == "#FF0055"
    for _ in range(3):
        step(vm, 3, -50)
    assert picked(vm)[2] == 0
    step(vm, 4, 50)
    assert picked(vm) == (255, 0, 0), "an unknown channel changes nothing"
    cases += 4
    # The start colour: a layer wins; a country the game files do not know starts mid grey.
    set_layer(vm, "FRA", (1, 2, 3))
    open_own(vm)
    assert picked(vm) == (1, 2, 3)
    vm2 = inp.vm(root=UNKNOWN)
    open_own(vm2)
    assert picked(vm2) == GREY
    assert shown_hex(vm2) == "#808080"
    cases += 2
    # A closed picker ignores clicks.
    vm.temp = {}
    vm.run("rn_cp_close")
    preset(vm, 2)
    step(vm, 1, 1)
    type_code(vm, "1")
    assert "rn_cp_r" not in root.vars
    assert not root.arrays.get("rn_cp_in")
    assert "rn_cp_open_own" not in root.flags
    return cases + 1


# ----------------------------------------------------------------------------- colour code

CODES: list[tuple[str, int, tuple[int, int, int] | None]] = [
    ("", 0, None),
    ("1E5AA0", 1, (30, 90, 160)),
    ("1e5aa0", 1, (30, 90, 160)),
    ("FFFFFF", 1, (255, 255, 255)),
    ("000000", 1, (0, 0, 0)),
    ("1E5AA", 2, None),
    ("1", 2, None),
    ("1E5AA0F", 3, None),
    ("FFFFFFFFFFF", 3, None),
    ("30 90 160", 1, (30, 90, 160)),
    ("0 0 0", 1, (0, 0, 0)),
    ("255 255 255", 1, (255, 255, 255)),
    ("007 08 9", 1, (7, 8, 9)),
    ("30 90 1A0", 4, None),
    ("A 1 1", 4, None),
    ("256 0 0", 5, None),
    ("30 300 160", 5, None),
    ("9999999 1 1", 5, None),
    ("30 90", 6, None),
    ("30 90 160 1", 6, None),
    ("30  90 160", 6, None),
    ("30  90", 6, None),
    (" 30 90 160", 6, None),
    ("30 90 160 ", 6, None),
    (" ", 6, None),
]
"""Typed code, expected ``rn_cp_in_st`` and the colour it is (None: not a valid colour)."""


def reference(code: str) -> tuple[int, tuple[int, int, int] | None]:  # noqa: PLR0911 - one per state
    """Return what a typed code is, by the rules the picker states (independent of the script).

    Args:
        code: Hex digits, decimal digits and spaces.

    Returns:
        ``(rn_cp_in_st, colour or None)``.
    """
    if not code:
        return 0, None
    if " " not in code:
        if len(code) != 6:  # noqa: PLR2004 - #RRGGBB
            return (2 if len(code) < 6 else 3), None  # noqa: PLR2004 - #RRGGBB
        r, g, b = (int(code[i : i + 2], 16) for i in (0, 2, 4))
        return 1, (r, g, b)
    if any(c not in "0123456789 " for c in code):
        return 4, None
    parts = code.split(" ")
    if any(int(p) > 255 for p in parts if p):  # noqa: PLR2004 - channel range
        return 5, None
    if len(parts) != 3 or not all(parts):  # noqa: PLR2004 - R G B
        return 6, None
    r, g, b = (int(p) for p in parts)
    return 1, (r, g, b)


def expected_colour(code: str, before: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return the picked colour after typing ``code`` key by key.

    Every valid prefix is picked at once; an invalid code keeps the last valid colour.

    Args:
        code: The typed code.
        before: The colour before typing.

    Returns:
        The colour.
    """
    colour = before
    for i in range(1, len(code) + 1):
        state, rgb = reference(code[:i])
        if state == 1 and rgb is not None:
            colour = rgb
    return colour


def fuzz_codes(count: int, seed: int = 19) -> list[str]:
    """Return reproducible random codes of up to :data:`CODE_MAX` characters.

    Args:
        count: How many.
        seed: Random seed.

    Returns:
        Codes made of hex digits and spaces (digits and spaces more often).
    """
    rng = random.Random(seed)  # noqa: S311 - reproducible test data, not security
    alphabet = "0123456789" * 3 + "ABCDEF" + " " * 6
    return [
        "".join(rng.choice(alphabet) for _ in range(rng.randint(1, CODE_MAX))) for _ in range(count)
    ]


def run_code(inp: ColourInputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """The colour code: hex and numbers, every refusal, Delete, Clear and Apply.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    table = [(code, state) for code, state, _ in CODES]
    for code, state, rgb in CODES:
        assert reference(code.upper()) == (state, rgb), ("table and rules disagree", code)
    table += [(code, reference(code)[0]) for code in fuzz_codes(120)]
    for code, state in table:
        vm = inp.vm()
        open_own(vm)
        preset(vm, 3)
        before = picked(vm)
        vm.nations["FRA"].flags.discard("rn_cp_changed")
        type_code(vm, code)
        assert typed(vm) == code.upper(), code
        assert code_state(vm) == state, (code, code_state(vm))
        want = expected_colour(code.upper(), before)
        assert picked(vm) == want, (code, picked(vm), want)
        assert shown_hex(vm) == hex_code(want), code
        changed = "rn_cp_changed" in vm.nations["FRA"].flags
        valid_prefix = any(reference(code.upper()[:i])[0] == 1 for i in range(1, len(code) + 1))
        assert changed == valid_prefix, code
        cases += 1
    vm = inp.vm()
    open_own(vm)
    root = vm.nations["FRA"]
    # A code that is a preset marks that preset.
    n = 41
    type_code(vm, hex_code(PRESETS[n - 1].rgb)[1:])
    assert root.vars["rn_cp_sel"] == n
    assert root.vars["rn_cp_frame"] == preview_frame(PRESETS[n - 1].rgb)
    # Delete and Clear.
    key(vm, "rn_cp_key_back")
    assert code_state(vm) == 2  # noqa: PLR2004 - five digits
    assert picked(vm) == PRESETS[n - 1].rgb, "an incomplete code keeps the colour"
    type_code(vm, "7")
    assert code_state(vm) == 1
    key(vm, "rn_cp_key_clear")
    assert typed(vm) == ""
    assert code_state(vm) == 0
    key(vm, "rn_cp_key_back")
    assert typed(vm) == "", "Delete on an empty code changes nothing"
    cases += 2
    # At most CODE_MAX characters; the rest is ignored.
    type_code(vm, "255 255 2550")
    assert typed(vm) == "255 255 255"
    assert len(typed(vm)) == CODE_MAX
    assert picked(vm) == (255, 255, 255)
    cases += 1
    # A preset, a stepper or "Clear" drops the typed code.
    type_code(vm, "12")
    preset(vm, 2)
    assert typed(vm) == ""
    assert code_state(vm) == 0
    type_code(vm, "12")
    step(vm, 1, 1)
    assert typed(vm) == ""
    cases += 1
    # Out-of-range keys type nothing.
    for bad in (-1, 17, 99):
        vm.temp = {"rn_cp_k": Decimal(bad)}
        vm.run("rn_cp_key")
        assert typed(vm) == "", bad
    cases += 1
    # Apply refuses an invalid code (17) and writes nothing; a valid one is applied.
    for code in ("1E5AA", "30 300 160", "30 90 1A0", "30 90"):
        vm = inp.vm()
        open_own(vm)
        preset(vm, 5)
        type_code(vm, code)
        vm.writes = []
        assert apply(vm) == ERR["code"], code
        assert layer(vm, "FRA") is None, code
        assert not layer_writes(vm, "FRA"), code
        assert is_open(vm, "rn_cp_open_own"), code
        cases += 1
    vm = inp.vm()
    open_own(vm)
    type_code(vm, "30 90 1600")
    assert code_state(vm) == 5  # noqa: PLR2004 - above 255
    key(vm, "rn_cp_key_back")
    assert apply(vm) == 0
    assert layer(vm, "FRA") == (30, 90, 160)
    vm = inp.vm()
    open_own(vm)
    type_code(vm, "1E5AA0")
    assert apply(vm) == 0
    assert layer(vm, "FRA") == (30, 90, 160)
    assert "rn_cp_in" not in vm.nations["FRA"].arrays, "closing drops the code"
    return cases + 2


# ----------------------------------------------------------------------------- Apply, Reset


REJECTIONS: list[tuple[str, dict[str, Any], int]] = [
    ("no CAPIE", {"cap": 1}, ERR["capie"]),
    ("CAPIE API level 7", {"cap": 7}, ERR["old"]),
    ("CAPIE API level 6", {"cap": 6, "colour": 0}, ERR["old"]),
    ("colour layer off", {"colour": 0}, ERR["layer"]),
    ("stale epoch", {"epoch": Decimal(99)}, ERR["stale"]),
    ("old epoch", {"epoch": Decimal(-1)}, ERR["stale"]),
    ("editor unavailable", {"epoch": Decimal(-2)}, ERR["setup"]),
]
"""Apply refused by the CAPIE header: label, :func:`capie` keywords, error."""


def run_apply(inp: ColourInputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """Apply's gates, the carrier order, the cooldown and "Reset".

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    vm = inp.vm()
    open_own(vm)
    root = vm.nations["FRA"]
    preset(vm, 13)
    for label, kwargs, err in REJECTIONS:
        before = copy.deepcopy(root.vars), copy.deepcopy(root.arrays)
        vm.writes = []
        assert apply(vm, **kwargs) == err, label
        assert layer(vm, "FRA") is None, label
        assert not layer_writes(vm, "FRA"), label
        assert "rn_ip_cd_colour_until" not in root.vars, label
        assert "rn_cp_open_own" in root.flags, ("the picker stays open", label)
        assert picked(vm) == PRESETS[12].rgb, label
        assert before[1] == root.arrays, label
        cases += 1
    # Host switch: wins over everything, even a valid CAPIE header.
    vm.rules[RULE] = "RN_FEATURE_COLOUR_OFF"
    assert apply(vm) == ERR["off"]
    assert apply(vm, cap=7) == ERR["off"], "the switch wins over the CAPIE level"
    assert layer(vm, "FRA") is None
    vm.rules.pop(RULE)
    cases += 2
    # Apply: the exact CONTRACT 19.5 order, rev last; cooldown; the picker closes.
    vm.writes = []
    assert apply(vm) == 0
    assert layer(vm, "FRA") == PRESETS[12].rgb
    assert layer_writes(vm, "FRA") == SET_ORDER, layer_writes(vm, "FRA")
    assert root.vars["capie_cc_rev"] == 1
    assert root.vars["rn_cc_mine"] == 1
    assert root.vars["rn_ip_cd_colour_until"] == VM_TODAY + COOLDOWN_DAYS
    assert "rn_cp_open_own" not in root.flags
    assert "rn_cp_r" not in root.vars
    cases += 1
    # Cooldown: Apply and Reset refused, the layer stays; the next opening shows it.
    open_own(vm)
    assert picked(vm) == PRESETS[12].rgb
    assert root.vars["rn_cp_sel"] == 13  # noqa: PLR2004 - the applied preset
    preset(vm, 1)
    vm.writes = []
    assert apply(vm) == ERR["cooldown"]
    assert reset(vm) == ERR["cooldown"]
    assert layer(vm, "FRA") == PRESETS[12].rgb
    assert not layer_writes(vm, "FRA")
    cases += 2
    # The cooldown rule: no cooldown at all.
    vm2 = inp.vm()
    vm2.rules["rn_rename_cooldown"] = "RN_COOLDOWN_OFF"
    open_own(vm2)
    preset(vm2, 3)
    assert apply(vm2) == 0
    open_own(vm2)
    preset(vm2, 4)
    assert apply(vm2) == 0, "no cooldown under RN_COOLDOWN_OFF"
    assert layer(vm2, "FRA") == PRESETS[3].rgb
    cases += 1
    # "Reset" after the cooldown, without CAPIE: the layer goes, rev last.
    root.vars["rn_ip_cd_colour_until"] = Decimal(VM_TODAY)
    vm.writes = []
    assert reset(vm) == 0
    assert layer(vm, "FRA") is None
    assert not any(k in root.vars for k in LAYER)
    assert "rn_cc_mine" not in root.vars
    assert layer_writes(vm, "FRA") == CLEAR_ORDER, layer_writes(vm, "FRA")
    assert root.vars["rn_ip_cd_colour_until"] == VM_TODAY + COOLDOWN_DAYS
    assert "rn_cp_open_own" not in root.flags
    cases += 1
    # Without a layer it changes nothing and starts no cooldown.
    vm = inp.vm()
    open_own(vm)
    vm.writes = []
    assert reset(vm) == 0
    assert not layer_writes(vm, "FRA")
    assert "rn_ip_cd_colour_until" not in vm.nations["FRA"].vars
    assert "rn_cp_open_own" in vm.nations["FRA"].flags
    cases += 1
    # A closed picker: Apply and Reset are refused.
    vm = inp.vm()
    assert apply(vm) == ERR["stale"]
    vm.nations["FRA"].vars.update(capie_cc_ver=Decimal(1))
    assert reset(vm) == ERR["rights"]
    cases += 2
    return cases + run_carrier(inp)


def run_carrier(inp: ColourInputs) -> int:
    """The carrier alone: rounding and clamping, and the cosmetic snapshot.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for given, want in (
        ((300, -5, 127.6), (255, 0, 128)),
        ((0, 255, 0.4), (0, 255, 0)),
        ((12.5, 999, -0.4), (13, 255, 0)),
    ):
        vm = inp.vm()
        vm.temp = {f"rn_cc_{c}": Decimal(str(v)) for c, v in zip("rgb", given, strict=True)}
        vm.scoped("ITA", lambda vm=vm: vm.run("rn_country_colour_carrier_set"))
        assert layer(vm, "ITA") == want, given
        cases += 1
    # With a known cosmetic tag: the packed snapshot and its length come before ver and rev.
    cosmetic = inp.cat.cosmetics[0]
    vm = inp.vm()
    ita = vm.nations["ITA"]
    ita.cosmetic = cosmetic
    vm.temp = {"rn_cc_r": Decimal(1), "rn_cc_g": Decimal(2), "rn_cc_b": Decimal(3)}
    vm.writes = []
    vm.scoped("ITA", lambda: vm.run("rn_country_colour_carrier_set"))
    assert decode(ita.arrays["capie_cc_cos"], ita.vars["capie_cc_cos_len"]) == cosmetic
    order = [w for w in layer_writes(vm, "ITA") if w != "array:capie_cc_cos"]
    assert order[:3] == SET_ORDER[:3]
    assert order[-3:] == ["capie_cc_cos_len", "capie_cc_ver", "capie_cc_rev"], order
    return cases + 1


# ----------------------------------------------------------------------------- the colour rule


def run_subject(inp: ColourInputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """The colour rule: who may open another country's picker and Apply there; the switches.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    # Default (own country and subjects): the subject, not a stranger.
    vm = inp.vm()
    open_sub(vm, "ITA")
    root = vm.nations["FRA"]
    assert not is_open(vm), "a stranger cannot be opened"
    open_sub(vm, "FRA")
    assert not is_open(vm), "the own country uses the politics view"
    open_sub(vm, "POL")
    assert is_open(vm)
    assert root.vars["rn_cp_target"] == Ref("POL")
    preset(vm, 8)
    vm.rules[RULE] = "RN_FEATURE_COLOUR_OWN"
    assert apply(vm) == ERR["rights"], "own country only"
    vm.rules.pop(RULE)
    vm.rules["rn_feature_subjects"] = "RN_FEATURE_SUBJECTS_OFF"
    assert apply(vm) == ERR["off"]
    vm.rules.pop("rn_feature_subjects")
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_OWN"
    vm.nations["POL"].overlord = None
    assert apply(vm) == ERR["rights"], "freed while open"
    assert layer(vm, "POL") is None
    cases = 5
    vm.nations["POL"].overlord = "FRA"
    assert apply(vm) == 0, "the rename rule does not decide colours"
    assert layer(vm, "POL") == PRESETS[7].rgb
    assert layer(vm, "FRA") is None
    assert "rn_ip_cd_colour_until" in vm.nations["POL"].vars
    assert "rn_ip_cd_colour_until" not in root.vars, "cooldown on the target"
    cases += 1
    # Own country only: no subject opens; the own picker does.
    vm = inp.vm()
    vm.rules[RULE] = "RN_FEATURE_COLOUR_OWN"
    open_sub(vm, "POL")
    assert not is_open(vm)
    open_own(vm)
    assert is_open(vm, "rn_cp_open_own")
    cases += 1
    # Any country (host), single player: the player is the host.
    vm = inp.vm()
    vm.rules[RULE] = "RN_FEATURE_COLOUR_ANY"
    open_sub(vm, "ITA")
    preset(vm, 2)
    assert apply(vm) == 0
    assert layer(vm, "ITA") == PRESETS[1].rgb
    cases += 1
    # Any country in multiplayer: only the player CAPIE reports as host (capie_host = 1).
    vm = inp.vm()
    vm.rules[RULE] = "RN_FEATURE_COLOUR_ANY"
    vm.nation("GER").ai = False
    open_sub(vm, "ITA")
    assert not is_open(vm), "not the host"
    open_sub(vm, "POL")
    assert is_open(vm), "a subject still opens"
    vm.nations["FRA"].flags.add("rn_is_host")
    open_sub(vm, "ITA")
    assert is_open(vm)
    assert vm.nations["FRA"].vars["rn_cp_target"] == Ref("ITA")
    preset(vm, 6)
    assert apply(vm) == ERR["rights"], "the Apply did not carry capie_host"
    vm.nations["FRA"].flags.add("rn_is_host")
    open_sub(vm, "ITA")
    preset(vm, 6)
    assert apply(vm, host=1) == 0
    assert layer(vm, "ITA") == PRESETS[5].rgb
    cases += 3
    # Off, and "other countries" off: nothing opens.
    vm = inp.vm()
    vm.rules["rn_feature_subjects"] = "RN_FEATURE_SUBJECTS_OFF"
    open_sub(vm, "POL")
    assert not is_open(vm)
    vm.rules.pop("rn_feature_subjects")
    vm.rules[RULE] = "RN_FEATURE_COLOUR_OFF"
    open_sub(vm, "POL")
    open_own(vm)
    assert not vm.nations["FRA"].flags & {"rn_cp_open_sub", "rn_cp_open_own"}
    return cases + 2


def run_mine(inp: ColourInputs) -> int:
    """A subject's "My colour": the overlord's layer, else its game colour, else a refusal.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    # No layer on the overlord: its colour from the game's files.
    vm = inp.vm()
    open_sub(vm, "POL")
    mine(vm)
    assert picked(vm) == FRENCH_BLUE
    assert "rn_cp_changed" in vm.nations["FRA"].flags
    assert apply(vm) == 0
    assert layer(vm, "POL") == FRENCH_BLUE
    # The overlord's layer wins; the subject keeps a copy when the overlord changes later.
    vm = inp.vm()
    set_layer(vm, "FRA", (11, 22, 33))
    open_sub(vm, "POL")
    type_code(vm, "12")
    mine(vm)
    assert picked(vm) == (11, 22, 33)
    assert typed(vm) == "", "My colour drops the typed code"
    assert apply(vm) == 0
    set_layer(vm, "FRA", (44, 55, 66))
    assert layer(vm, "POL") == (11, 22, 33)
    cases = 2
    # An overlord whose colour is not known: error 18, the colour stays, nothing written.
    vm = inp.vm(root=UNKNOWN)
    vm.nations["POL"].overlord = UNKNOWN
    open_sub(vm, "POL")
    before = picked(vm)
    vm.writes = []
    mine(vm)
    assert root_err(vm) == ERR["mine"]
    assert picked(vm) == before
    assert not layer_writes(vm, "POL")
    assert is_open(vm)
    cases += 1
    # Not in the own picker, and not for a country that is not the player's subject.
    vm = inp.vm()
    open_own(vm)
    preset(vm, 9)
    mine(vm)
    assert picked(vm) == PRESETS[8].rgb
    vm = inp.vm()
    vm.rules[RULE] = "RN_FEATURE_COLOUR_ANY"
    open_sub(vm, "ITA")
    preset(vm, 9)
    mine(vm)
    assert picked(vm) == PRESETS[8].rgb
    cases += 2
    # Reset of the subject brings its own colour back (the layer goes).
    vm = inp.vm()
    set_layer(vm, "POL", (1, 1, 1))
    open_sub(vm, "POL")
    assert picked(vm) == (1, 1, 1)
    assert reset(vm) == 0
    assert layer(vm, "POL") is None
    return cases + 1


def check_action() -> None:
    """The diplomatic action "Change map colour" opens the picker through rn_cp_may_edit."""
    actions = get(
        declarations(SOURCE / "common" / "scripted_diplomatic_actions")[
            "scripted_diplomatic_actions"
        ],
        "rn_country_colour",
    )
    visible = get(actions, "visible")
    assert ("rn_cp_may_edit", "=", "yes") in visible
    assert ("NOT", "=", [("tag", "=", "ROOT")]) in visible
    assert ("ROOT", "=", [("is_ai", "=", "no")]) in visible
    assert get(actions, "complete_effect") == [("rn_cp_open_sub", "=", "yes")]
    tips = [
        get(v, "tooltip") for k, _, v in get(actions, "selectable") if k == "custom_trigger_tooltip"
    ]
    assert {"RN_FEAT_COLOUR_ALLOWED", "RN_FEAT_SUBJECTS_ALLOWED", "RN_EDITOR_FREE_TT"} <= set(tips)
    for k, v in (("requires_acceptance", "no"), ("cost", "0"), ("command_power", "0")):
        assert get(actions, k) == v, k


# ----------------------------------------------------------------------------- daily check


def run_daily(inp: ColourInputs) -> int:
    """The daily cosmetic tag check (no cooldown; this mod's and other layers).

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    known, known2 = inp.cat.cosmetics[0], inp.cat.cosmetics[1]
    #  cosmetic at Apply, cosmetic now, written by this mod, expected reset
    table = [
        (None, None, True, False),
        (None, known, True, True),
        (known, known, True, False),
        (known, known2, True, True),
        (known, None, True, True),
        (known, known2, False, True),
        (known, None, False, False),
    ]
    for at_apply, now, ours, want_reset in table:
        vm = inp.vm()
        target = vm.nations["FRA"]
        target.cosmetic = at_apply
        set_layer(vm, "FRA", (10, 20, 30))
        if not ours:
            target.vars.pop("rn_cc_mine")
        target.cosmetic = now
        vm.temp = {}
        vm.scoped("FRA", lambda vm=vm: vm.run("rn_cp_daily_check"))
        assert (layer(vm, "FRA") is None) == want_reset, (at_apply, now, ours)
        assert "rn_ip_cd_colour_until" not in target.vars, "the daily reset starts no cooldown"
    return len(table)


# ----------------------------------------------------------------------------- mutations


def mutated[T: Inputs](inp: T, effect: str, predicate: Any) -> T:  # noqa: ANN401 - node predicate
    """Return inputs whose ``effect`` lost every node matching ``predicate`` (at any depth).

    Args:
        inp: Inputs.
        effect: Effect or trigger name.
        predicate: Node predicate.

    Returns:
        Mutated inputs.
    """
    removed = 0

    def prune(nodes: list[Any]) -> list[Any]:
        """Drop matching nodes and recurse into blocks.

        Args:
            nodes: Effect nodes.

        Returns:
            The pruned copy.
        """
        nonlocal removed
        out = []
        for k, op, v in nodes:
            if predicate((k, op, v)):
                removed += 1
                continue
            out.append((k, op, prune(v) if isinstance(v, list) else v))
        return out

    mutant = copy.copy(inp)
    mutant.effects = copy.deepcopy(inp.effects)
    mutant.triggers = copy.deepcopy(inp.triggers)
    table = mutant.effects if effect in mutant.effects else mutant.triggers
    table[effect] = prune(table[effect])
    assert removed, ("mutation matched nothing", effect)
    return mutant


def run_colour_mutations(inp: ColourInputs) -> int:
    """Remove one guard at a time; the cases must then fail.

    Args:
        inp: Inputs.

    Returns:
        Number of rejected mutations.
    """
    mutations = [
        mutated(inp, "rn_cp_apply", lambda n: "capie_cap" in str(n) and n[0] == "if"),
        mutated(inp, "rn_cp_apply", lambda n: n[0] == "else_if"),
        mutated(inp, "rn_cp_apply", lambda n: n == ("rn_cp_switch", "=", "yes")),
        mutated(inp, "rn_cp_apply", lambda n: n == ("rn_cp_rights", "=", "yes")),
        mutated(inp, "rn_cp_apply", lambda n: "rn_cp_in_st" in str(n) and n[0] == "if"),
        mutated(inp, "rn_cp_apply", lambda n: "rn_cp_cooldown_active" in str(n) and n[0] == "if"),
        mutated(inp, "rn_cp_reset", lambda n: "rn_cp_cooldown_active" in str(n) and n[0] == "if"),
        mutated(
            inp,
            "rn_country_colour_carrier_set",
            lambda n: n == ("set_variable", "=", [("capie_cc_rev", "=", "1")]),
        ),
        mutated(inp, "rn_country_colour_carrier_set", lambda n: n[0] == "clamp_temp_variable"),
        mutated(inp, "rn_cp_step", lambda n: n[0] == "clamp_variable"),
        mutated(inp, "rn_cp_daily_check", lambda n: n[0] == "if"),
        mutated(inp, "rn_cp_may_edit", lambda n: "rn_feature_colour_own_only" in str(n)),
        mutated(
            inp, "rn_cp_may_edit", lambda n: n == ("ROOT", "=", [("rn_rights_host", "=", "yes")])
        ),
        mutated(inp, "rn_cp_open_sub", lambda n: n == ("rn_cp_may_edit", "=", "yes")),
        mutated(inp, "rn_cp_pick_mine", lambda n: n[0] == "var:rn_cp_target"),
        mutated(inp, "rn_cp_pick_mine", lambda n: n[0] == "else" and "rn_cp_native" in str(n)),
        mutated(inp, "rn_cp_code_parse", lambda n: "rn_cp_il" in str(n) and n[0] == "else_if"),
        mutated(inp, "rn_cp_code_numbers", lambda n: "rn_cp_acc" in str(n) and n[0] == "if"),
        mutated(inp, "rn_cp_code_number_end", lambda n: "rn_cp_dg" in str(n) and n[0] == "if"),
        mutated(inp, "rn_cp_key", lambda n: "rn_cp_in^num" in str(n) and n[0] == "check_variable"),
    ]
    rejected = 0
    for mutant in mutations:
        try:
            run_apply(mutant)
            run_picking(mutant)
            run_code(mutant)
            run_subject(mutant)
            run_mine(mutant)
            run_daily(mutant)
        except (AssertionError, KeyError):
            rejected += 1
    assert rejected == len(mutations), ("colour mutations not caught", rejected, len(mutations))
    return rejected


def run_colour_cases() -> dict[str, int]:
    """Run every colour picker VM case.

    Returns:
        Case counts by group.
    """
    inp = ColourInputs()
    check_action()
    check_colour_geometry()
    return {
        "colour_picking_cases": run_picking(inp),
        "colour_code_cases": run_code(inp),
        "colour_apply_cases": run_apply(inp),
        "colour_rule_cases": run_subject(inp),
        "colour_mine_cases": run_mine(inp),
        "colour_daily_cases": run_daily(inp),
        "colour_mutations_rejected": run_colour_mutations(inp),
    }


# ----------------------------------------------------------------------------- geometry


def _colour_sizes() -> dict[str, tuple[int, int]]:
    """Return the drawn size of every sprite the colour picker uses.

    Returns:
        Sprite to ``(width, height)``.
    """
    sizes = {swatch_sprite(n): SWATCH for n in range(1, len(PRESETS) + 1)}
    sizes.update(
        {
            MARK_SPRITE: MARK,
            KEY_SPRITE: KEY,
            KEY_WIDE_SPRITE: KEY_WIDE,
            PREVIEW_SPRITE: (PREVIEW_FRAME, PREVIEW_FRAME),
            "GFX_rn_hit_step": (colour_picker.STEP_W, 16),
            "GFX_button_94x31": (94, 31),
            "GFX_closebutton_16": (16, 16),
            "GFX_preset_button_save": (30, 30),
        }
    )
    return sizes


def check_colour_geometry() -> None:
    """Check both colour windows' layout.

    Each window fits its view and holds its elements; no two controls overlap (a shift+A..F
    button sits only under its own letter); the keypad is above the status line, the grid left
    of Apply, and only the other-country picker has "My colour".
    """
    tree = parse((MOD / "interface" / "rn_colour_picker.gui").read_text(encoding="utf-8-sig"))
    windows = {get(v, "name"): v for k, _, v in walk(tree) if k == "containerWindowType"}
    sizes = _colour_sizes()
    for picker in colour_picker.PICKERS:
        win = windows[picker.key]
        w, h = xy(win, "size")
        x, y = xy(win)
        assert (w, h) == (colour_picker.WIDTH, colour_picker.HEIGHT)
        assert x + w <= PANEL_WIDTH, picker.key
        if picker is colour_picker.OWN:
            assert y + h <= ACTIONS_Y, picker.key
        rects: dict[str, tuple[str, tuple[int, int, int, int]]] = {}
        for kind, _, body in win:
            if not isinstance(body, list) or not any(k == "position" for k, _, _ in body):
                continue
            ex, ey = xy(body)
            sprite = next((v for k, _, v in body if k in {"spriteType", "quadTextureSprite"}), "")
            if sprite:
                sw, sh = sizes[sprite]
                scale = float(get(body, "scale")) if any(k == "scale" for k, _, _ in body) else 1
                if sprite in {"GFX_preset_button_save", PREVIEW_SPRITE}:
                    sw, sh = round(sw * scale), round(sh * scale)
            else:
                sw, sh = int(get(body, "maxWidth")), int(get(body, "maxHeight"))
            rects[str(get(body, "name"))] = (str(kind), (ex, ey, ex + sw, ey + sh))
        frame = (0, 0, w, h)
        for name, (_, rect) in rects.items():
            assert inside(rect, frame), (picker.key, name, rect)
        controls = {n: r for n, (k, r) in rects.items() if k == "buttonType"}
        names = sorted(controls)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                shifted = {a, b} == {f"rn_cp_key_S{a[-1]}", f"rn_cp_key_{a[-1]}"}
                assert shifted or disjoint(controls[a], controls[b]), (picker.key, a, b)
        status = rects["rn_cp_status"][1]
        assert all(r[3] <= status[1] for n, r in controls.items() if n.startswith("rn_cp_key_"))
        apply_ = controls[f"{picker.key}_apply"]
        assert all(r[2] <= apply_[0] for n, r in controls.items() if n.startswith("rn_cp_sw_"))
        assert inside(rects["rn_cp_preview"][1], (0, 0, colour_picker.LEFT_W, h))
        assert ("rn_cp_mine" in controls) == (picker is colour_picker.SUBJECT)
