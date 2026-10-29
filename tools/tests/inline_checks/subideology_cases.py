"""Party ideology name (CAPIE API level 8, CONTRACT section 20): a VM over the real effects.

:class:`~inline_checks.flag_cases.FlagVM` runs the hand-written editor and carrier
(``tools/inline_editor``) and the generated on_actions
(``mod/common/on_actions/rn_subideology_on_actions.txt``) for the player's country and
its leader:

* opening and the host switch;
* Apply: the gates in order (epoch header, ``capie_cap >= 8``, ``capie_subideo = 1``,
  switch, rights, cooldown, the field), each refusal without a write on the country, the
  layer's codes, the leader pinned at Apply and ``capie_sn_rev`` as a new revision, last;
* "Restore name": the same rules without CAPIE, nothing to do without a name;
* the lapse: a party or government change, and daily a new country leader, removes the name
  without a cooldown; a layer another mod wrote is left alone;
* a few mutations that the cases must catch.

The VM is not the HOI4 parser and proves nothing about the game, CAPIE or multiplayer.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

from inline_checks.colour_cases import mutated
from inline_checks.constants import MAX_NAME, MOD, VM_TODAY
from inline_checks.fixtures import parse
from inline_checks.flag_cases import FlagVM, Inputs, Ref
from inline_checks.tree import get
from modgen.charset import CODE
from modgen.features.cooldown import COOLDOWN_DAYS

ERR = {
    "field": 1,
    "length": 4,
    "alphabet": 5,
    "capie": 10,
    "cooldown": 11,
    "stale": 12,
    "setup": 13,
    "old": 15,
    "layer": 16,
    "rights": 20,
    "off": 21,
}
"""Editor error codes (temp ``rn_cv1_err``, stored as ``rn_cv1_st_err``)."""

API_LEVEL = 8
"""CAPIE API level of the layer."""

LEADER = "FRA_L1"
"""VM tag of the country leader at Apply."""

NEXT_LEADER = "FRA_L2"
"""VM tag of a second character of the country."""

NAME = "Sanacja Łódzka"
"""A name with Polish letters."""

ON_ACTIONS = MOD / "common" / "on_actions" / "rn_subideology_on_actions.txt"
"""The generated lapse on_actions."""


class IdeologyInputs(Inputs):
    """The flag VM inputs plus the generated on_actions of the layer."""

    def __init__(self) -> None:
        """Load the source and the on_actions."""
        super().__init__()
        ((_, _, body),) = parse(ON_ACTIONS.read_text(encoding="utf-8-sig"))
        self.on_actions = {name: get(block, "effect") for name, _, block in body}

    def vm(self, root: str = "FRA", effects: dict[str, Any] | None = None) -> FlagVM:
        """Return the flag VM with two characters of the player, the first one leading.

        Args:
            root: Player tag.
            effects: Replacement effects (mutations).

        Returns:
            The VM.
        """
        vm = super().vm(root, effects)
        vm.nation(LEADER, leader=True)
        vm.nation(NEXT_LEADER)
        vm.nations[root].characters = [LEADER, NEXT_LEADER]
        return vm


def open_editor(vm: FlagVM) -> None:
    """Click the pencil of the ruling-party box.

    Args:
        vm: VM.
    """
    vm.temp = {}
    vm.run("rn_si_open")


def capie(  # noqa: PLR0913 - one keyword per CAPIE record
    vm: FlagVM,
    text: str = NAME,
    *,
    cap: int = API_LEVEL,
    subideo: int = 1,
    epoch: Any = None,  # noqa: ANN401 - Decimal epoch
    codes: list[int] | None = None,
    field_err: int = 0,
) -> None:
    """Put the CAPIE records of the editor's Apply into the temps.

    Args:
        vm: VM.
        text: Typed name.
        cap: ``capie_cap``.
        subideo: ``capie_subideo``.
        epoch: ``capie_epoch``; the stored opening epoch by default.
        codes: Character codes instead of ``text``.
        field_err: ``capie_f1_err``.
    """
    root = vm.nations[vm.root]
    codes = [CODE[c] for c in text] if codes is None else codes
    vm.temp = {
        "capie_cap": Decimal(cap),
        "capie_ver": Decimal(10600),
        "capie_subideo": Decimal(subideo),
        "capie_epoch": root.vars.get("rn_si_epoch", Decimal(0)) if epoch is None else epoch,
        "capie_nf": Decimal(1),
        "capie_f1_err": Decimal(field_err),
        "capie_f1_at": Decimal(0),
        "capie_f1_len": Decimal(len(codes)),
    }
    for i in range(MAX_NAME):
        vm.temp[f"capie_f1_{i}"] = Decimal(codes[i] if i < len(codes) else 0)


def apply(vm: FlagVM, text: str = NAME, **kwargs: Any) -> int:  # noqa: ANN401 - capie() keywords
    """Press Apply; return the stored error.

    Args:
        vm: VM.
        text: Typed name.
        **kwargs: :func:`capie` keywords.

    Returns:
        ``rn_cv1_st_err``.
    """
    capie(vm, text, **kwargs)
    vm.run("rn_si_apply")
    return int(vm.nations[vm.root].vars.get("rn_cv1_st_err", 0))


def reset(vm: FlagVM) -> int:
    """Press "Restore name" (no CAPIE records); return the stored error.

    Args:
        vm: VM.

    Returns:
        ``rn_cv1_st_err``.
    """
    vm.temp = {}
    vm.run("rn_si_reset")
    return int(vm.nations[vm.root].vars.get("rn_cv1_st_err", 0))


def name_of(vm: FlagVM) -> str | None:
    """Return the player's party ideology name, or None.

    Args:
        vm: VM.

    Returns:
        The text.
    """
    n = vm.nations[vm.root]
    if "capie_sn_ver" not in n.vars:
        return None
    assert n.vars["capie_sn_ver"] == 1
    by_code = {code: c for c, code in CODE.items()}
    return "".join(by_code[int(c)] for c in n.arrays["capie_sn_n"])


def layer_writes(vm: FlagVM) -> list[str]:
    """Return the recorded writes of ``capie_sn_*`` on the player, in order.

    Args:
        vm: VM.

    Returns:
        Write labels.
    """
    return [w for t, w in vm.writes if t == vm.root and "capie_sn_" in w]


def on_action(inp: IdeologyInputs, vm: FlagVM, name: str) -> None:
    """Run one on_action's effect for the player's country (ROOT = THIS = the country).

    Args:
        inp: Inputs.
        vm: VM.
        name: on_action.
    """
    vm.temp = {}
    vm.execute(inp.on_actions[name])


# ----------------------------------------------------------------------------- cases


def run_open(inp: IdeologyInputs) -> int:
    """Opening, the switch, and other windows blocking the editor.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    vm = inp.vm()
    open_editor(vm)
    root = vm.nations["FRA"]
    assert "rn_si_open" in root.flags
    first = root.vars["rn_si_epoch"]
    vm.run("rn_si_close")
    assert "rn_si_open" not in root.flags
    assert root.vars["rn_si_epoch"] == first + 1, "closing makes an older Apply stale"
    vm = inp.vm()
    vm.rules["rn_feature_subideology"] = "RN_FEATURE_SUBIDEOLOGY_OFF"
    open_editor(vm)
    assert "rn_si_open" not in vm.nations["FRA"].flags
    vm = inp.vm()
    vm.nations["FRA"].flags.add("rn_open")
    open_editor(vm)
    assert "rn_si_open" not in vm.nations["FRA"].flags, "the keyboard editor is open"
    return 3


REJECTIONS: list[tuple[str, str, dict[str, Any], int]] = [
    ("no CAPIE", NAME, {"cap": 1}, ERR["capie"]),
    ("CAPIE API level 7", NAME, {"cap": 7}, ERR["old"]),
    ("CAPIE API level 6", NAME, {"cap": 6, "subideo": 0}, ERR["old"]),
    ("layer off", NAME, {"subideo": 0}, ERR["layer"]),
    ("stale epoch", NAME, {"epoch": Decimal(99)}, ERR["stale"]),
    ("editor unavailable", NAME, {"epoch": Decimal(-3)}, ERR["setup"]),
    ("empty name", "", {}, ERR["length"]),
    ("field error", NAME, {"field_err": 2}, ERR["field"]),
    ("33 characters", "x" * (MAX_NAME + 1), {}, ERR["length"]),
    ("outside the alphabet", "", {"codes": [CODE["A"], 93]}, ERR["alphabet"]),
]
"""Apply refused: label, text, :func:`capie` keywords, error."""


def run_apply(inp: IdeologyInputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """Apply's gates, the layer and its revision, the cooldown and "Restore name".

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    vm = inp.vm()
    root = vm.nations["FRA"]
    root.vars["capie_sn_rev"] = Decimal(41)
    open_editor(vm)
    for label, text, kwargs, err in REJECTIONS:
        before = copy.deepcopy(root.arrays)
        vm.writes = []
        assert apply(vm, text, **kwargs) == err, label
        assert name_of(vm) is None, label
        assert not layer_writes(vm), label
        assert root.vars["capie_sn_rev"] == 41, label  # noqa: PLR2004 - untouched revision
        assert "rn_ip_cd_subideo_until" not in root.vars, label
        assert "rn_si_open" in root.flags, ("the editor stays open", label)
        assert before.get("rn_sn_leader") == root.arrays.get("rn_sn_leader"), label
        cases += 1
    vm.rules["rn_feature_subideology"] = "RN_FEATURE_SUBIDEOLOGY_OFF"
    assert apply(vm) == ERR["off"]
    assert apply(vm, cap=7) == ERR["off"], "the switch wins over the CAPIE level"
    vm.rules.pop("rn_feature_subideology")
    cases += 2
    # Apply: codes, ver, the pinned leader, a new revision as the last write; cooldown; closed.
    vm.writes = []
    assert apply(vm) == 0
    assert name_of(vm) == NAME
    assert root.vars["capie_sn_rev"] == 42  # noqa: PLR2004 - previous + 1
    writes = layer_writes(vm)
    assert writes[0] == "clear_array:capie_sn_n", writes
    assert writes[-2:] == ["capie_sn_ver", "capie_sn_rev"], writes
    assert writes.count("array:capie_sn_n") == len(NAME)
    assert root.arrays.get("rn_sn_leader") == [Ref(LEADER)]
    assert root.vars["rn_ip_cd_subideo_until"] == VM_TODAY + COOLDOWN_DAYS
    assert "rn_si_open" not in root.flags
    assert "rn_cv1_st_err" not in root.vars
    cases += 1
    # Cooldown: Apply and Restore refused, the name stays.
    open_editor(vm)
    vm.writes = []
    assert apply(vm, "Inna") == ERR["cooldown"]
    assert reset(vm) == ERR["cooldown"]
    assert name_of(vm) == NAME
    assert not layer_writes(vm)
    cases += 2
    # "Restore name" after the cooldown, without CAPIE: the layer goes, a new revision last.
    root.vars["rn_ip_cd_subideo_until"] = Decimal(VM_TODAY)
    vm.writes = []
    assert reset(vm) == 0
    assert name_of(vm) is None
    assert not root.arrays.get("capie_sn_n")
    assert not root.arrays.get("rn_sn_leader")
    assert layer_writes(vm) == [
        "clear_array:capie_sn_n",
        "clear_variable:capie_sn_ver",
        "capie_sn_rev",
    ]
    assert root.vars["capie_sn_rev"] == 43  # noqa: PLR2004 - previous + 1
    assert root.vars["rn_ip_cd_subideo_until"] == VM_TODAY + COOLDOWN_DAYS
    assert "rn_si_open" not in root.flags
    cases += 1
    # Without a name, Restore changes nothing and starts no cooldown; a missing rev reads 0.
    vm = inp.vm()
    open_editor(vm)
    vm.writes = []
    assert reset(vm) == 0
    assert not layer_writes(vm)
    assert "rn_ip_cd_subideo_until" not in vm.nations["FRA"].vars
    assert apply(vm, "x" * MAX_NAME) == 0, "32 characters fit"
    assert vm.nations["FRA"].vars["capie_sn_rev"] == 1
    cases += 2
    # A closed editor (the epoch still matches): Apply and Restore are not allowed.
    vm = inp.vm()
    vm.nations["FRA"].vars["rn_si_epoch"] = Decimal(3)
    assert apply(vm) == ERR["rights"]
    vm.nations["FRA"].vars["capie_sn_ver"] = Decimal(1)
    assert reset(vm) == ERR["rights"]
    return cases + 2


def run_lapse(inp: IdeologyInputs) -> int:
    """The name ends with the government it was given to; nothing else ends it.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for event in ("on_ruling_party_change", "on_government_change"):
        vm = inp.vm()
        open_editor(vm)
        assert apply(vm) == 0
        cooldown = vm.nations["FRA"].vars["rn_ip_cd_subideo_until"]
        on_action(inp, vm, event)
        assert name_of(vm) is None, event
        assert vm.nations["FRA"].vars["capie_sn_rev"] == 2, event  # noqa: PLR2004 - set, clear
        assert vm.nations["FRA"].vars["rn_ip_cd_subideo_until"] == cooldown, "no new cooldown"
        on_action(inp, vm, event)
        assert vm.nations["FRA"].vars["capie_sn_rev"] == 2, "nothing to clear, no commit"  # noqa: PLR2004
        cases += 1
    # Daily: the same leader keeps it, a new leader ends it.
    vm = inp.vm()
    open_editor(vm)
    assert apply(vm) == 0
    on_action(inp, vm, "on_daily")
    assert name_of(vm) == NAME
    vm.nations[LEADER].leader = False
    vm.nations[NEXT_LEADER].leader = True
    on_action(inp, vm, "on_daily")
    assert name_of(vm) is None
    cases += 2
    # A layer another mod wrote (no pinned leader) is left to CAPIE's binding.
    vm = inp.vm()
    root = vm.nations["FRA"]
    root.vars.update(capie_sn_ver=Decimal(1), capie_sn_rev=Decimal(5))
    root.arrays["capie_sn_n"] = [Decimal(CODE["A"])]
    vm.nations[LEADER].leader = False
    on_action(inp, vm, "on_daily")
    assert name_of(vm) == "A"
    return cases + 1


# ----------------------------------------------------------------------------- mutations


def run_ideology_mutations(inp: IdeologyInputs) -> int:
    """Remove one guard at a time; the cases must then fail.

    Args:
        inp: Inputs.

    Returns:
        Number of rejected mutations.
    """
    mutations = [
        mutated(inp, "rn_si_apply", lambda n: "capie_cap" in str(n) and n[0] == "if"),
        mutated(inp, "rn_si_apply", lambda n: n[0] == "else_if"),
        mutated(inp, "rn_si_apply", lambda n: n == ("rn_si_rights", "=", "yes")),
        mutated(inp, "rn_si_apply", lambda n: "rn_si_cooldown_active" in str(n) and n[0] == "if"),
        mutated(inp, "rn_si_apply", lambda n: "rn_cv1_take_one" in str(n) and n[0] == "if"),
        mutated(inp, "rn_si_reset", lambda n: "rn_si_cooldown_active" in str(n) and n[0] == "if"),
        mutated(inp, "rn_subideology_name_commit", lambda n: n[0] == "add_to_temp_variable"),
        mutated(inp, "rn_subideology_name_carrier_set", lambda n: n[0] == "every_character"),
        mutated(inp, "rn_si_daily_check", lambda n: n[0] == "if"),
    ]
    rejected = 0
    for mutant in mutations:
        try:
            run_apply(mutant)
            run_lapse(mutant)
        except AssertionError:
            rejected += 1
    assert rejected == len(mutations), ("ideology mutations not caught", rejected, len(mutations))
    return rejected


def run_ideology_cases() -> dict[str, int]:
    """Run every party ideology name VM case.

    Returns:
        Case counts by group.
    """
    inp = IdeologyInputs()
    return {
        "ideology_open_cases": run_open(inp),
        "ideology_apply_cases": run_apply(inp),
        "ideology_lapse_cases": run_lapse(inp),
        "ideology_mutations_rejected": run_ideology_mutations(inp),
    }
