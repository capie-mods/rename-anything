"""Colour picker (CAPIE API level 8, CONTRACT section 19): a VM over the real effects.

:class:`~inline_checks.flag_cases.FlagVM` runs the hand-written picker and carrier
(``tools/inline_editor``) together with the generated preset and cosmetic lookups
(``mod/common/scripted_effects/rn_colour_catalog.txt``) over several countries:

* opening (mid grey without a layer, the layer's colour with one), every preset, the
  red/green/blue steppers with their 0..255 clamp, the preview frame;
* Apply: the gates in the spec's order (epoch header, ``capie_cap >= 8``,
  ``capie_colour = 1``, host switches, rights, cooldown), each refusal without a write on
  the target, and the carrier's exact CONTRACT 19.5 statement order, ``capie_cc_rev`` last;
* "Original colour": the same rules without CAPIE, nothing to do without a layer;
* the subject picker's rights, the daily cosmetic tag check, and a few mutations that the
  cases must catch.

The VM is not the HOI4 parser and proves nothing about the game, CAPIE or multiplayer.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

from inline_checks.constants import MOD, VM_TODAY
from inline_checks.flag_cases import FlagVM, Inputs, Ref, decode
from inline_checks.tree import declarations
from modgen.features.colours import PRESETS, preview_frame
from modgen.features.cooldown import COOLDOWN_DAYS

ERR = {
    "capie": 10,
    "cooldown": 11,
    "stale": 12,
    "setup": 13,
    "old": 15,
    "layer": 16,
    "rights": 20,
    "off": 21,
}
"""Colour picker error codes (temp ``rn_cv1_err``, stored as ``rn_cv1_st_err``)."""

API_LEVEL = 8
"""CAPIE API level of the colour layer."""

GREY = (128, 128, 128)
"""Starting colour of the picker when the target has no layer."""

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


def capie(vm: FlagVM, *, cap: int = API_LEVEL, colour: int = 1, epoch: Any = None) -> None:  # noqa: ANN401 - Decimal epoch
    """Put the CAPIE records of a colour editor's Apply into the temps.

    Args:
        vm: VM.
        cap: ``capie_cap``.
        colour: ``capie_colour``.
        epoch: ``capie_epoch``; the stored opening epoch by default.
    """
    root = vm.nations[vm.root]
    vm.temp = {
        "capie_cap": Decimal(cap),
        "capie_ver": Decimal(10600),
        "capie_colour": Decimal(colour),
        "capie_epoch": root.vars.get("rn_cp_epoch", Decimal(0)) if epoch is None else epoch,
        "capie_nf": Decimal(0),
    }


def open_own(vm: FlagVM) -> None:
    """Open the own picker as the politics tab does.

    Args:
        vm: VM.
    """
    vm.temp = {}
    vm.run("rn_cp_open_own")


def open_sub(vm: FlagVM, tag: str) -> None:
    """Open the subject picker from the diplomacy view of ``tag``.

    Args:
        vm: VM.
        tag: Selected country.
    """
    vm.temp = {}
    vm.scoped(tag, lambda: vm.run("rn_cp_open_sub"))


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


def picked(vm: FlagVM) -> tuple[int, int, int]:
    """Return the colour shown in the open picker.

    Args:
        vm: VM.

    Returns:
        ``(r, g, b)``.
    """
    v = vm.nations[vm.root].vars
    return int(v["rn_cp_r"]), int(v["rn_cp_g"]), int(v["rn_cp_b"])


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
    """Press "Original colour" (no CAPIE records); return the stored error.

    Args:
        vm: VM.

    Returns:
        ``rn_cv1_st_err``.
    """
    vm.temp = {}
    vm.run("rn_cp_reset")
    return root_err(vm)


# ----------------------------------------------------------------------------- picking


def run_picking(inp: ColourInputs) -> int:
    """Opening, every preset, the steppers, the clamp and the preview frame.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    vm = inp.vm()
    open_own(vm)
    root = vm.nations["FRA"]
    assert "rn_cp_open_own" in root.flags
    assert root.vars["rn_cp_target"] == Ref("FRA")
    assert picked(vm) == GREY
    assert root.vars["rn_cp_sel"] == 0
    assert "rn_cp_changed" not in root.flags, "Apply stays disabled until a change"
    cases = 1
    for n, p in enumerate(PRESETS, start=1):
        preset(vm, n)
        assert picked(vm) == p.rgb, p.english
        assert root.vars["rn_cp_sel"] == n
        assert root.vars["rn_cp_frame"] == preview_frame(p.rgb), p.english
        assert all(0 <= c <= 255 for c in p.rgb)  # noqa: PLR2004 - channel range
        cases += 1
    for bad in (0, len(PRESETS) + 1, -1):
        before = picked(vm)
        preset(vm, bad)
        assert picked(vm) == before, bad
        cases += 1
    # Steppers: a change leaves the preset; the clamp holds at both ends.
    preset(vm, 1)
    step(vm, 1, 1)
    assert picked(vm) == (201, 30, 45)
    assert root.vars["rn_cp_sel"] == 0
    step(vm, 1, -1)
    assert root.vars["rn_cp_sel"] == 1, "back on the preset"
    for _ in range(20):
        step(vm, 1, 16)
        step(vm, 2, -16)
    step(vm, 3, 16)
    assert picked(vm) == (255, 0, 61)
    assert root.vars["rn_cp_frame"] == preview_frame((255, 0, 61))
    for _ in range(20):
        step(vm, 3, -16)
    assert picked(vm)[2] == 0
    step(vm, 4, 16)
    assert picked(vm) == (255, 0, 0), "an unknown channel changes nothing"
    cases += 3
    # A closed picker ignores clicks.
    vm.temp = {}
    vm.run("rn_cp_close")
    preset(vm, 2)
    step(vm, 1, 1)
    assert "rn_cp_r" not in root.vars
    assert "rn_cp_open_own" not in root.flags
    return cases + 1


# ----------------------------------------------------------------------------- Apply, Restore


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
    """Apply's gates, the carrier order, the cooldown and "Original colour".

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
    vm.rules["rn_feature_colour"] = "RN_FEATURE_COLOUR_OFF"
    assert apply(vm) == ERR["off"]
    assert apply(vm, cap=7) == ERR["off"], "the switch wins over the CAPIE level"
    assert layer(vm, "FRA") is None
    vm.rules.pop("rn_feature_colour")
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
    # Cooldown: Apply and Restore refused, the layer stays; the next opening shows it.
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
    # "Original colour" after the cooldown, without CAPIE: the layer goes, rev last.
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
    # A closed picker: Apply and Restore are refused.
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


# ----------------------------------------------------------------------------- subject picker


def run_subject(inp: ColourInputs) -> int:
    """The subject picker: who may open it, rights at Apply, the switches, the target's cooldown.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    vm = inp.vm()
    open_sub(vm, "ITA")
    root = vm.nations["FRA"]
    assert "rn_cp_open_sub" not in root.flags, "a stranger cannot be opened"
    open_sub(vm, "POL")
    assert "rn_cp_open_sub" in root.flags
    assert root.vars["rn_cp_target"] == Ref("POL")
    preset(vm, 8)
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_OWN"
    assert apply(vm) == ERR["rights"]
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_SUBJECTS"
    vm.rules["rn_feature_subjects"] = "RN_FEATURE_SUBJECTS_OFF"
    assert apply(vm) == ERR["off"]
    vm.rules.pop("rn_feature_subjects")
    vm.nations["POL"].overlord = None
    assert apply(vm) == ERR["rights"], "freed while open"
    assert layer(vm, "POL") is None
    cases = 4
    vm.nations["POL"].overlord = "FRA"
    assert apply(vm) == 0
    assert layer(vm, "POL") == PRESETS[7].rgb
    assert layer(vm, "FRA") is None
    assert "rn_ip_cd_colour_until" in vm.nations["POL"].vars
    assert "rn_ip_cd_colour_until" not in root.vars, "cooldown on the target"
    cases += 1
    # Host rule in single player: any country; the switch "other countries" blocks opening.
    vm = inp.vm()
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_HOST"
    open_sub(vm, "ITA")
    preset(vm, 2)
    assert apply(vm) == 0
    assert layer(vm, "ITA") == PRESETS[1].rgb
    vm = inp.vm()
    vm.rules["rn_feature_subjects"] = "RN_FEATURE_SUBJECTS_OFF"
    open_sub(vm, "POL")
    assert "rn_cp_open_sub" not in vm.nations["FRA"].flags
    vm.rules.pop("rn_feature_subjects")
    vm.rules["rn_feature_colour"] = "RN_FEATURE_COLOUR_OFF"
    open_sub(vm, "POL")
    open_own(vm)
    assert not vm.nations["FRA"].flags & {"rn_cp_open_sub", "rn_cp_open_own"}
    return cases + 3


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
        vm.temp = {"rn_cc_r": Decimal(10), "rn_cc_g": Decimal(20), "rn_cc_b": Decimal(30)}
        vm.scoped("FRA", lambda vm=vm: vm.run("rn_country_colour_carrier_set"))
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
        effect: Effect name.
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
    mutant.effects[effect] = prune(mutant.effects[effect])
    assert removed, ("mutation matched nothing", effect)
    return mutant


def run_colour_mutations(inp: ColourInputs) -> int:
    """Remove one guard at a time; the Apply, subject or daily cases must then fail.

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
    ]
    rejected = 0
    for mutant in mutations:
        try:
            run_apply(mutant)
            run_picking(mutant)
            run_subject(mutant)
            run_daily(mutant)
        except AssertionError:
            rejected += 1
    assert rejected == len(mutations), ("colour mutations not caught", rejected, len(mutations))
    return rejected


def run_colour_cases() -> dict[str, int]:
    """Run every colour picker VM case.

    Returns:
        Case counts by group.
    """
    inp = ColourInputs()
    return {
        "colour_picking_cases": run_picking(inp),
        "colour_apply_cases": run_apply(inp),
        "colour_subject_cases": run_subject(inp),
        "colour_daily_cases": run_daily(inp),
        "colour_mutations_rejected": run_colour_mutations(inp),
    }
