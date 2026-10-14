"""Portrait picker: structure, geometry and VM cases (ADR-0036 with its amendment).

Structure. The two generated editors follow the CAPIE grammar under their own mod
id ``rnpt`` (no mod id has more than eight editors), have no text field, a
hidden epoch and Enter only on Apply; every element, effect, trigger and
localisation key they name exists.

Geometry. Every control inside the window, no overlaps, the own picker right of
the politics view's leader frame (the current portrait stays visible) and above
its action row, the portrait inside the scaled vanilla frame, and the leader
editor's new tab row above its field.

VM. The generated lookups against the catalog the generator builds from the game
(every entry's group and kinds, every pool of both kinds, the letters), and the
picker: opening pins the country leader, the pool rule and the subject rule at
Apply, the switches, rights, a changed leader (18), the CAPIE records (no CAPIE
sends API level 7 yet, so Apply stops at 15), the cooldown, and Restore. The
carrier is pending the native contract; the cases check that Apply reaches it
only with the full records.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from inline_checks.constants import ACTIONS_Y, MOD, SOURCE, VM_TODAY
from inline_checks.fixtures import parse
from inline_checks.flag_cases import FlagVM, Nation, Ref, _loc_keys, _rects, decode, root_err
from inline_checks.geometry import disjoint, inside
from inline_checks.tree import declarations, get, models_of, walk, xy
from modgen.features import portrait_picker as pp
from modgen.features.portraits import GENERAL, LEADER, PortraitCatalog, read_catalog
from rncommon.game_data import DEFAULT_GAME, GameInstallation

MAX_EDITORS_PER_MOD = 8
"""CAPIE registry limit per mod id."""

POLITICS_LEADER_FRAME_RIGHT = 182
"""Right edge of the politics view's leader frame (10 + 172)."""

ERR = {"old": 15, "layer": 16, "pool": 17, "leader": 18, "rights": 20, "off": 21, "cooldown": 11}
"""Portrait picker error codes."""


def _windows() -> dict[str, list[Any]]:
    """Return the generated portrait windows and entries.

    Returns:
        Name to body.
    """
    tree = parse((MOD / "interface" / "rn_portrait_picker.gui").read_text(encoding="utf-8-sig"))
    return {
        get(v, "name"): v
        for k, _, v in walk(tree)
        if k == "containerWindowType" and any(n[0] == "name" for n in v)
    }


def check_portrait_structure(models: dict[str, Any]) -> None:  # noqa: C901, PLR0912 - one loop per checked part
    """Check grammar, registry limits, references and localisation of the portrait editors.

    Args:
        models: Source scripted GUI models.
    """
    generated = models_of(MOD / "common" / "scripted_guis", "rn_portrait_picker.txt")
    flags = models_of(MOD / "common" / "scripted_guis", "rn_flag_picker.txt")
    per_mod: dict[str, int] = {}
    for model in (*models, *flags, *generated):
        match = re.fullmatch(r"capie_v1_ed__([a-z0-9]{1,12})__[a-z0-9]{1,12}", model)
        if match:
            per_mod[match[1]] = per_mod.get(match[1], 0) + 1
    assert all(n <= MAX_EDITORS_PER_MOD for n in per_mod.values()), per_mod
    daily = (MOD / "common" / "on_actions" / "rn_portrait_on_actions.txt").read_text("utf-8")
    assert "any_character = { is_country_leader = yes has_variable = capie_pt_ver }" in daily
    assert "set_variable = { capie_pt_rev = 1 }" in daily, "daily commit (CONTRACT 18)"
    windows = _windows()
    effects = {
        **declarations(SOURCE / "common" / "scripted_effects"),
        **declarations(MOD / "common" / "scripted_effects", "rn_portrait_catalog.txt"),
        **declarations(MOD / "common" / "scripted_effects", "rn_flag_catalog.txt"),
    }
    triggers = {
        **declarations(SOURCE / "common" / "scripted_triggers"),
        **declarations(MOD / "common" / "scripted_triggers", "rn_feature_switches.txt"),
    }
    keys = _loc_keys()
    for picker in pp.PICKERS:
        model, win = generated[picker.key], windows[picker.key]
        assert not any(k == "editBoxType" for k, _, _ in walk(win))
        epoch = get(get(model, "triggers"), f"capie_v1_ep__rnpt__{picker.editor}_visible")
        assert epoch == [("always", "=", "no")]
        buttons = {get(b, "name"): b for k, _, b in walk(win) if k == "buttonType"}
        enter = {n for n, b in buttons.items() if any(k == "shortcut" for k, _, _ in b)}
        assert enter == {f"{picker.key}_apply"}
        elements = {
            get(b, "name")
            for _, _, b in walk([*win, *windows["rn_pp_cell"], *windows["rn_pp_row"]])
            if isinstance(b, list) and any(n[0] == "name" for n in b)
        }
        for name, _, body in get(model, "effects"):
            assert name.removesuffix("_click") in elements, (picker.key, name)
            for k, _, v in walk(body):
                if v == "yes" and k.startswith("rn_"):
                    assert k in effects or k in triggers, (picker.key, k)
        for name, _, body in get(model, "triggers"):
            assert re.sub(r"_(visible|click_enabled)$", "", name) in elements, (picker.key, name)
            for k, _, v in walk(body):
                if v in ("yes", "no") and k.startswith("rn_"):
                    assert k in triggers, (picker.key, name, k)
        for _, _, body in walk(win):
            if isinstance(body, list):
                for k, _, v in body:
                    if k in {"buttonText", "pdx_tooltip", "text"} and not str(v).startswith("["):
                        assert v in keys, (picker.key, k, v)


def check_portrait_geometry() -> None:
    """Check the portrait windows, the cell and the leader editor's tab row."""
    windows = _windows()
    for picker in pp.PICKERS:
        win = windows[picker.key]
        w, h = xy(win, "size")
        x, y = xy(win)
        rects = {n: r for n, (_, r) in _rects(win).items()}
        for name, rect in rects.items():
            assert inside(rect, (0, 0, w, h)), (picker.key, name, rect)
        controls = {n: r for n, (k, r) in _rects(win).items() if k in {"buttonType", "gridBoxType"}}
        names = sorted(controls)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                grids = {a, b} == {"rn_pp_grid", "rn_pp_rows_grid"}
                # The pack steps share two places; exactly one per place is visible.
                steps = a.startswith("rn_pp_pack_") and b.startswith("rn_pp_pack_")
                assert grids or steps or disjoint(controls[a], controls[b]), (picker.key, a, b)
        assert inside(rects["rn_pp_preview"], rects["rn_pp_frame"])
        if picker is pp.OWN:
            assert x >= POLITICS_LEADER_FRAME_RIGHT, "the current portrait stays visible"
            assert y + h <= ACTIONS_Y
    cell = {n: r for n, (_, r) in _rects(windows["rn_pp_cell"]).items()}
    assert inside(cell["rn_pp_cell_portrait"], (0, 0, *pp.CELL))
    assert inside(cell["rn_pp_cell_sel"], (0, 0, *pp.CELL))
    gui = parse((SOURCE / "interface" / "rn_in_place_ui.gui").read_text(encoding="utf-8-sig"))
    win = next(
        v
        for k, _, v in walk(gui)
        if k == "containerWindowType" and get(v, "name") == "rn_ip_leader_window"
    )
    items = {
        get(b, "name"): b
        for _, _, b in win
        if isinstance(b, list) and any(n[0] == "name" for n in b)
    }
    for tab in ("rn_ip_leader_tab_name", "rn_ip_leader_tab_portrait"):
        assert xy(items[tab])[1] + 31 <= xy(items["rn_ipl_frame"])[1], tab
    assert xy(win)[1] + xy(win, "size")[1] <= ACTIONS_Y


# ----------------------------------------------------------------------------- VM


class PortraitInputs:
    """Effects, triggers and the reference catalog of the portrait VM cases."""

    def __init__(self) -> None:
        """Load the source and generated script and the game's catalog."""
        self.cat: PortraitCatalog = read_catalog(DEFAULT_GAME)
        self.effects = {
            **declarations(SOURCE / "common" / "scripted_effects"),
            **declarations(MOD / "common" / "scripted_effects", "rn_portrait_catalog.txt"),
            **declarations(MOD / "common" / "scripted_effects", "rn_flag_catalog.txt"),
        }
        self.triggers = {
            **declarations(SOURCE / "common" / "scripted_triggers"),
            **declarations(MOD / "common" / "scripted_triggers", "rn_feature_switches.txt"),
        }

    def vm(self, own: str, subject: str) -> FlagVM:
        """Return a VM: a human ``FRA``, a subject and a stranger, each with a leader.

        Args:
            own: Tag of the player (a catalog country).
            subject: Tag of the player's subject (a catalog country).

        Returns:
            The VM.
        """
        vm = FlagVM(self.effects, self.triggers, own)
        vm.rules.update(
            rn_portrait_pool="RN_PORTRAIT_POOL_ANY_LEADER",
            rn_portrait_subjects="RN_PORTRAIT_SUBJECTS_BOTH",
        )
        vm.nation(own, ai=False, government="democratic")
        vm.nation(subject, overlord=own)
        vm.nation("ITA")
        for tag in (own, subject, "ITA"):
            leader = vm.nation(f"c_{tag}", leader=True)
            general = vm.nation(f"g_{tag}")
            vm.nations[tag].characters = [leader.tag, general.tag]
        for tag in self.cat.tags:
            vm.nation(tag)
        return vm


def _capie(vm: FlagVM, *, cap: int = 7, portrait: int = 1) -> None:
    """Put the CAPIE records of a portrait editor's Apply into the temps.

    Args:
        vm: VM.
        cap: ``capie_cap``.
        portrait: ``capie_portrait``.
    """
    vm.temp = {
        "capie_cap": Decimal(cap),
        "capie_portrait": Decimal(portrait),
        "capie_epoch": vm.nations[vm.root].vars.get("rn_pp_epoch", Decimal(0)),
    }


def _apply(vm: FlagVM, index: int, **records: int) -> int:
    """Select ``index`` and Apply; return the status error.

    Args:
        vm: VM.
        index: Catalog index.
        **records: CAPIE record overrides.

    Returns:
        ``rn_cv1_st_err``.
    """
    vm.nations[vm.root].vars["rn_pp_sel"] = Decimal(index)
    _capie(vm, **records)
    vm.run("rn_pp_apply")
    return root_err(vm)


def run_portrait_catalog(inp: PortraitInputs) -> int:
    """Check the generated lookups for every entry, pool and letter.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    vm = inp.vm(cat.tags[0], cat.tags[1])
    group = {t: g for g, t in enumerate(cat.tags, start=1)}
    for n, e in enumerate(cat.entries, start=1):
        vm.temp = {"rn_pp_w": Decimal(n)}
        vm.run("rn_pp_entry_info")
        got = (vm.temp["rn_pp_e_g"], vm.temp["rn_pp_e_leader"], vm.temp["rn_pp_e_general"])
        assert got == (group[e.tag], int(e.leader), int(e.general)), (n, e)
    char = vm.nations[f"c_{vm.root}"]
    for n, e in enumerate(cat.entries, start=1):
        char.vars.clear()
        char.arrays.clear()
        vm.temp = {"rn_pp_w": Decimal(n)}
        vm.scoped(char.tag, lambda: vm.run("rn_pp_write_portrait"))
        assert decode(char.arrays["capie_pt_s"], char.vars["capie_pt_len"]) == e.large, n
        assert decode(char.arrays["capie_pt_ss"], char.vars["capie_pt_slen"]) == e.small, n
    root = vm.nations[vm.root]
    packs = range(len(cat.packs))
    for g, tag in enumerate(cat.tags, start=1):
        for kind in (LEADER, GENERAL):
            for pack in packs:
                root.vars.update(rn_pp_kind=Decimal(kind), rn_pp_pack=Decimal(pack))
                root.arrays["rn_pp_list"] = []
                vm.temp = {"rn_pp_g": Decimal(g)}
                vm.run("rn_pp_fill_group")
                want = [Decimal(i) for i in cat.pool(tag, kind, pack)]
                assert root.arrays["rn_pp_list"] == want, (tag, kind, pack)
    for kind in (LEADER, GENERAL):
        for pack in packs:
            seen: list[str] = []
            for letter in range(1, 27):
                root.vars.update(
                    rn_pp_kind=Decimal(kind), rn_pp_pack=Decimal(pack), rn_pp_letter=Decimal(letter)
                )
                root.arrays["rn_pp_list"] = []
                vm.run("rn_pp_fill_letter")
                seen += [r.tag for r in root.arrays["rn_pp_list"]]
            assert sorted(seen) == sorted(t for t in cat.tags if cat.pool(t, kind, pack))
    return 2 * len(cat.entries) + 2 * len(cat.tags) * len(cat.packs) + 2 * len(cat.packs)


def _own_tags(cat: PortraitCatalog) -> tuple[str, str]:
    """Return two catalog countries that have leaders' and generals' portraits.

    Args:
        cat: Catalog.

    Returns:
        ``(own, subject)``.
    """
    both = [t for t in cat.tags if cat.pool(t, LEADER, 0) and cat.pool(t, GENERAL, 0)]
    leaders = [t for t in cat.tags if cat.pool(t, LEADER, 0) and t not in both[:1]]
    return both[0], leaders[0]


def run_portrait_picker(inp: PortraitInputs) -> int:  # noqa: PLR0915 - one scenario per behaviour
    """Run the own and the subject portrait picker.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    own, sub = _own_tags(cat)
    stranger_leader = next(i for t in cat.tags if t not in {own, sub} for i in cat.pool(t, LEADER))
    own_leader, own_general = cat.pool(own, LEADER, 0)[0], cat.pool(own, GENERAL, 0)[0]
    cases = 0

    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    root = vm.nations[own]
    assert "rn_pp_open_own" in root.flags
    assert root.arrays["rn_pp_char_arr"] == [Ref(f"c_{own}")], "the country leader is pinned"
    assert root.vars["rn_pp_init"] == 0, "the game's portrait has no getter"
    assert root.arrays["rn_pp_cells"] == [Decimal(i) for i in cat.pool(own, LEADER, 0)[: pp.PAGE]]
    cases += 1

    # CAPIE 1.4 sends API level 6 and no capie_portrait: refused before anything else.
    for records, err in (({"cap": 6}, ERR["old"]), ({"portrait": 0}, ERR["layer"])):
        assert _apply(vm, own_leader, **records) == err, records
        assert "rn_ip_cd_portrait_until" not in root.vars
        cases += 1

    # Pool rule at Apply.
    for rule, index, err in (
        ("RN_PORTRAIT_POOL_ANY_LEADER", stranger_leader, 0),
        ("RN_PORTRAIT_POOL_ANY_LEADER", own_general, ERR["pool"]),
        ("RN_PORTRAIT_POOL_OWN", stranger_leader, ERR["pool"]),
        ("RN_PORTRAIT_POOL_OWN", own_leader, 0),
        ("RN_PORTRAIT_POOL_OWN_GENERALS", own_general, 0),
        ("RN_PORTRAIT_POOL_OWN_GENERALS", stranger_leader, ERR["pool"]),
        ("RN_PORTRAIT_POOL_ALL", own_general, 0),
        ("RN_PORTRAIT_POOL_ALL", len(cat.entries) + 1, ERR["pool"]),
    ):
        vm = inp.vm(own, sub)
        vm.rules["rn_portrait_pool"] = rule
        vm.temp = {}
        vm.run("rn_pp_open_own")
        assert _apply(vm, index) == err, (rule, index)
        until = vm.nations[own].vars.get("rn_ip_cd_portrait_until")
        assert (until is not None) == (err == 0), (rule, index)
        cases += 1

    # The carrier (CONTRACT 18.4): both sizes on the ruling leader, the commit last on the country.
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    vm.writes = []
    assert _apply(vm, own_leader) == 0
    entry = cat.entries[own_leader - 1]
    char = vm.nations[f"c_{own}"]
    assert decode(char.arrays["capie_pt_s"], char.vars["capie_pt_len"]) == entry.large
    assert decode(char.arrays["capie_pt_ss"], char.vars["capie_pt_slen"]) == entry.small
    assert char.vars["capie_pt_ver"] == 1
    assert char.vars["rn_pt_idx"] == own_leader
    assert "capie_pt_ver" not in vm.nations[f"g_{own}"].vars, "only the ruling leader"
    layer_writes = [(t, w) for t, w in vm.writes if "capie_pt" in w]
    assert layer_writes[-1] == (own, "capie_pt_rev"), layer_writes[-3:]
    vm.temp = {}
    vm.run("rn_pp_open_own")
    assert vm.nations[own].vars["rn_pp_init"] == own_leader, "the chosen portrait is preselected"
    vm.nations[own].vars["rn_ip_cd_portrait_until"] = Decimal(VM_TODAY)
    vm.writes = []
    vm.temp = {}
    vm.run("rn_pp_reset")
    assert "capie_pt_ver" not in char.vars
    assert "capie_pt_s" not in char.arrays
    assert [(t, w) for t, w in vm.writes if "capie_pt" in w][-1] == (own, "capie_pt_rev")
    cases += 2

    # A new leader since the opening (18); the cooldown (11); switches (21).
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    vm.nations[f"c_{own}"].leader = False
    vm.nations[f"g_{own}"].leader = True
    assert _apply(vm, own_leader) == ERR["leader"]
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    vm.nations[own].vars["rn_ip_cd_portrait_until"] = Decimal(VM_TODAY + 2)
    assert _apply(vm, own_leader) == ERR["cooldown"]
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    vm.rules["rn_feature_portrait"] = "RN_FEATURE_PORTRAIT_OFF"
    assert _apply(vm, own_leader) == ERR["off"]
    vm = inp.vm(own, sub)
    vm.rules["rn_feature_portrait"] = "RN_FEATURE_PORTRAIT_OFF"
    vm.temp = {}
    vm.run("rn_pp_open_own")
    assert "rn_pp_open_own" not in vm.nations[own].flags, "no opening while switched off"
    cases += 4

    # Subjects: who may change a subject leader's portrait.
    for rule, overlord_ok, subject_ok in (
        ("RN_PORTRAIT_SUBJECTS_BOTH", True, True),
        ("RN_PORTRAIT_SUBJECTS_OVERLORD_ONLY", True, False),
        ("RN_PORTRAIT_SUBJECTS_NO_OVERLORD", False, True),
    ):
        vm = inp.vm(own, sub)
        vm.rules["rn_portrait_subjects"] = rule
        vm.temp = {}
        vm.scoped(sub, lambda vm=vm: vm.run("rn_pp_open_sub"))
        assert ("rn_pp_open_sub" in vm.nations[own].flags) == overlord_ok, rule
        if overlord_ok:
            assert _apply(vm, cat.pool(sub, LEADER)[0]) == 0, rule
            assert "rn_ip_cd_portrait_until" in vm.nations[sub].vars, "cooldown on the subject"
        player = inp.vm(sub, own)
        player.nations[sub].overlord = own
        player.rules["rn_portrait_subjects"] = rule
        player.temp = {}
        player.run("rn_pp_open_own")
        assert ("rn_pp_open_own" in player.nations[sub].flags) == subject_ok, rule
        cases += 2
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.scoped("ITA", lambda: vm.run("rn_pp_open_sub"))
    assert "rn_pp_open_sub" not in vm.nations[own].flags, "a stranger cannot be opened"
    cases += 1

    # Restore: only with a layer, under the cooldown.
    vm = inp.vm(own, sub)
    vm.nations[f"c_{own}"].vars["capie_pt_ver"] = Decimal(1)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    assert "rn_pp_has_layer" in vm.nations[own].flags
    vm.temp = {}
    vm.run("rn_pp_reset")
    assert root_err(vm) == 0
    assert "rn_ip_cd_portrait_until" in vm.nations[own].vars
    assert "rn_pp_open_own" not in vm.nations[own].flags
    cases += 1
    return cases


def run_portrait_dlc(inp: PortraitInputs) -> int:  # noqa: PLR0915 - one scenario per check
    """DLC packs: MP-safe state, the stepper for several sets of owned DLC, and Apply without DLC.

    ``has_dlc`` may appear only in visible triggers of the local window: no effect,
    trigger file or game-state write may read it. The stepper's visible triggers are
    evaluated for sets of owned DLC; from the base game, "next" must walk exactly the
    owned packs in order (no gaps), and "previous" back.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    for folder in ("scripted_effects", "scripted_triggers", "on_actions", "scripted_localisation"):
        for path in (SOURCE / "common" / folder).glob("*.txt"):
            assert "has_dlc" not in path.read_text(encoding="utf-8-sig"), path
        for path in (MOD / "common" / folder).glob("rn_*.txt"):
            assert "has_dlc" not in path.read_text(encoding="utf-8-sig"), path
    model = models_of(MOD / "common" / "scripted_guis", "rn_portrait_picker.txt")[pp.OWN.key]
    for name, _, body in get(model, "effects"):
        assert "has_dlc" not in str(body), name
    for name, _, body in get(model, "triggers"):
        if "has_dlc" in str(body):
            assert name.endswith("_visible"), ("has_dlc only decides what the local UI shows", name)
    cat = inp.cat
    packs = cat.packs
    visible = {
        name.removesuffix("_visible"): body
        for name, _, body in get(model, "triggers")
        if name.startswith("rn_pp_pack_")
        and name.endswith("_visible")
        and name != "rn_pp_pack_name_visible"
    }
    cases = 0
    for owned in (set(), set(range(1, len(packs))), {1, len(packs) - 1}, {2, 3}):
        current, walked = 0, [0]
        while True:
            nexts = [
                b
                for (a, b) in _steps(visible)
                if a == current
                and b > current
                and _holds(visible[f"rn_pp_pack_{a}_{b}"], current, owned, packs)
            ]
            assert len(nexts) <= 1, (owned, current, nexts)
            if not nexts:
                break
            current = nexts[0]
            walked.append(current)
        assert walked == [0, *sorted(owned)], (owned, walked)
        backs = [
            b
            for (a, b) in _steps(visible)
            if a == current
            and b < current
            and _holds(visible[f"rn_pp_pack_{a}_{b}"], current, owned, packs)
        ]
        expected_back = ([0, *sorted(owned)][-2:-1]) if owned else []
        assert backs == expected_back, (owned, backs)
        cases += 1
    # Apply takes a DLC portrait by its index; the state does not depend on the local DLC set.
    own, sub = _own_tags(cat)
    dlc_leader = next(n for n, e in enumerate(cat.entries, start=1) if e.pack > 0 and e.leader)
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    assert _apply(vm, dlc_leader) == 0, "a DLC portrait is applied like any other"
    entry = cat.entries[dlc_leader - 1]
    char = vm.nations[f"c_{own}"]
    assert decode(char.arrays["capie_pt_s"], char.vars["capie_pt_len"]) == entry.large
    # The pack stepper's effect: pages of a pack are counted from game state only.
    dlc_tag = entry.tag
    vm = inp.vm(own, sub)
    vm.temp = {}
    vm.run("rn_pp_open_own")
    vm.temp = {}
    root = vm.nations[own]
    root.vars["rn_pp_view"] = Decimal(1)
    root.vars["rn_pp_src"] = Ref(dlc_tag)
    root.flags.discard("rn_pp_view_target")
    vm.temp = {"rn_pp_pk": Decimal(entry.pack)}
    vm.run("rn_pp_pick_pack")
    pool = cat.pool(dlc_tag, LEADER, entry.pack)
    assert root.vars["rn_pp_pack"] == entry.pack
    assert root.arrays["rn_pp_cells"] == [Decimal(i) for i in pool[: pp.PAGE]]
    assert root.vars["rn_pp_pages"] == (len(pool) + pp.PAGE - 1) // pp.PAGE
    vm.temp = {"rn_pp_pk": Decimal(len(packs))}
    vm.run("rn_pp_pick_pack")
    assert root.vars["rn_pp_pack"] == entry.pack, "no pack outside the catalog"
    return cases + 3


def _steps(visible: dict[str, Any]) -> list[tuple[int, int]]:
    """Return the ``(from, to)`` pairs of the pack step buttons.

    Args:
        visible: Step name to its visible trigger.

    Returns:
        Pairs.
    """
    out = []
    for name in visible:
        a, b = name.removeprefix("rn_pp_pack_").split("_")
        out.append((int(a), int(b)))
    return out


def _holds(trigger: list[Any], current: int, owned: set[int], packs: tuple[str, ...]) -> bool:
    """Evaluate a step's visible trigger for the shown pack and a set of owned DLC.

    Args:
        trigger: Trigger body.
        current: ``rn_pp_pack``.
        owned: Indices of the owned packs.
        packs: Pack names.

    Returns:
        Whether the button shows.
    """

    def one(key: str, value: Any) -> bool:  # noqa: ANN401 - parse-tree value
        """Evaluate one node.

        Args:
            key: Node key.
            value: Node value.

        Returns:
            The result.

        Raises:
            AssertionError: An unexpected trigger.
        """
        if key == "ROOT":
            return all(one(k, v) for k, _, v in value)
        if key == "check_variable":
            ((_, _, rhs),) = value
            return bool(int(rhs) == current)
        if key == "has_dlc":
            return bool(packs.index(value.strip('"')) in owned)
        if key == "NOT":
            return not any(one(k, v) for k, _, v in value)
        if key == "always":
            return bool(value == "yes")
        raise AssertionError(key)

    return all(one(k, v) for k, _, v in trigger)


def run_portrait_cases() -> dict[str, int]:
    """Run every portrait VM case (skipped without the game, which the catalog comes from).

    Returns:
        Case counts.
    """
    if not GameInstallation(DEFAULT_GAME).has_state_history():
        return {"portrait_cases": 0}
    inp = PortraitInputs()
    return {
        "portrait_catalog_cases": run_portrait_catalog(inp),
        "portrait_picker_cases": run_portrait_picker(inp),
        "portrait_dlc_cases": run_portrait_dlc(inp),
    }


__all__ = ["Nation", "check_portrait_geometry", "check_portrait_structure", "run_portrait_cases"]
