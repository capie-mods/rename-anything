"""CAPIE v1.1 grammar editors: subject rename and the legacy window's text field.

Two parts. The structural checks read the source GUI and scripted GUI trees:
every grammar name follows ``plugin/capie/CONTRACT.md`` section 3, the
carriers are hidden, every Apply has Enter, and the subject editors sit on the
same grid as the politics editors. The VM cases run the real effects in the
borrowed ApplyVM, extended here with a second country (the subject): the CAPIE
header and the field adapters, every permission and cooldown rejection with no
write, the three subject setters and the legacy field's Apply.

The VM models a ``var:rn_sub_target = { ... }`` block by swapping the subject's
variables, flags, tag and government in for the player's. It is not the HOI4
parser and proves nothing about the game.
"""

from __future__ import annotations

import itertools
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any, override

from inline_checks.constants import MAX_NAME, MOD, SOURCE
from inline_checks.fixtures import NATIVE_ALPHABET, Country
from inline_checks.tree import declarations, get, named, walk, xy
from inline_checks.vm_cases import Context, ProductVM
from modgen.charset import CODE

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

CAPIE_API = 4
"""API level CAPIE 1.2 sends as ``capie_cap``."""

SUB_EPOCH = 4
"""Opening epoch of the subject editor in every VM case."""

LEGACY_EPOCH = 9
"""Opening epoch of the legacy text field in every VM case."""

SUBJECT_TAG = "SUB"
"""Tag of the subject country in the VM."""

ERR_FIELD = 1
"""rn_cv1_err: a field rejected by the encoder (validator code 1)."""

ERR_ALPHABET = 5
"""rn_cv1_err: a code outside Rename Anything's 84-code alphabet (validator code 5)."""

ERR_NO_CAPIE = 10
"""rn_cv1_err: no ``capie_cap`` of API level 2 in the command."""

ERR_COOLDOWN = 11
"""rn_cv1_err: the subject's cooldown of this type is active."""

ERR_STALE = 12
"""rn_cv1_err: sentinel -1, an epoch of another opening, or no opening."""

ERR_SETUP = 13
"""rn_cv1_err: sentinel -2 (registry full) or -3 (layout invalid)."""

ERR_RIGHTS = 20
"""rn_cv1_err: the target is not a subject of the player, or the editor is not open."""

GRAMMAR = re.compile(r"^capie_v1_(ed|f|pf|ep)__rn__([a-z0-9]{1,12})(__[1-4])?(_apply(_click)?)?$")
"""Grammar of a Rename Anything editor name (CONTRACT.md section 3, mod id ``rn``)."""

SUBJECT_EDITORS = {"subcountry": 2, "subleader": 1, "subparty": 2}
"""Subject editor id to its number of fields."""

DIPLOMACY_WIDTH = 550
"""Width of the vanilla diplomacy view (``countrydiplomacyview``)."""

DIPLOMACY_HEADER_TOP = 37
"""Top of the Diplomacy view's header (flag and names) under its title line."""

KIND_FLAGS = {1: "rn_sub_open_country", 2: "rn_sub_open_leader", 3: "rn_sub_open_party"}
"""rn_sub_kind to the opening flag on the player."""


# ----------------------------------------------------------------------------- structure


def check_capie_structure(models: dict[str, Any], gui: list[Any], triggers: dict[str, Any]) -> None:
    """Check the grammar names, carriers, fields and the subject permission trigger.

    Args:
        models: Source scripted GUI models.
        gui: Parsed source GUI files.
        triggers: Source scripted triggers.
    """
    names = {n for k, _, b in walk(gui) if isinstance(b, list) for n in [_name(b)] if n}
    grammar = sorted(n for n in names if n.startswith("capie_"))
    assert grammar, "no CAPIE grammar element"
    assert all(GRAMMAR.match(n) for n in grammar), [n for n in grammar if not GRAMMAR.match(n)]
    widgets = named(gui)
    for editor, count in SUBJECT_EDITORS.items():
        model = f"capie_v1_ed__rn__{editor}"
        body = models[model]
        assert get(body, "context_type") == "selected_country_context", editor
        assert get(body, "parent_window_token") == "selected_country_view_diplomacy", editor
        assert get(body, "window_name") == model, editor
        fields = [f"capie_v1_f__rn__{editor}__{n}" for n in range(1, 5)]
        present = [f for f in fields if f in widgets]
        assert present == fields[:count], (editor, present)
        for field in present:
            assert ("ignore_enter", "=", "yes") in widgets[field], field
            assert get(widgets[field], "font") == "hoi_18", field
            assert xy(widgets[field], "size")[0] >= MAX_NAME * 11, field
        assert ("shortcut", "=", "RETURN") in widgets[f"{model}_apply"], editor
        carriers = [f"capie_v1_ep__rn__{editor}"] + [
            f"capie_v1_pf__rn__{editor}__{n}" for n in range(1, count + 1)
        ]
        hidden = get(body, "triggers")
        for carrier in carriers:
            assert carrier in widgets, carrier
            assert get(hidden, f"{carrier}_visible") == [("always", "=", "no")], carrier
        apply_ = get(get(body, "effects"), f"{model}_apply_click")
        assert len(apply_) == 1, "one statement: the player's Apply effect"
        assert apply_[0][0] == "ROOT", "Apply runs on the player only"
        visible = get(body, "visible")
        assert ("rn_sub_may_edit", "=", "yes") in visible, editor
        own = {"subcountry": "country", "subleader": "leader", "subparty": "party"}[editor]
        for key in ("country", "leader", "party"):
            enabled = get(hidden, f"rn_sub_{editor}_tab_{key}_click_enabled")
            assert (enabled == [("always", "=", "no")]) == (key == own), (editor, key)
            tab = get(get(body, "effects"), f"rn_sub_{editor}_tab_{key}_click")
            assert ("rn_sub_may_edit", "=", "yes") in get(get(tab, "if"), "limit"), (editor, key)
        assert any(k == "is_in_array" for k, _, _ in visible), "pinned target only"
    assert "rn_sub_launcher_gui" not in models, "no title-line button any more"
    _check_action()
    _check_carrier()
    assert triggers["rn_sub_may_edit"] == [
        ("exists", "=", "yes"),
        ("is_subject_of", "=", "ROOT"),
        ("NOT", "=", [("tag", "=", "ROOT")]),
    ]
    _subject_geometry(widgets)


def _check_action() -> None:
    """The entry is a free diplomatic action, only for the player's own subjects.

    It costs nothing, needs no answer, is never sent by the AI and opens the
    country editor through the same guard as everything else. Its list title
    starts with the vanilla edit icon. No title-line button or test text is left.
    """
    actions = declarations(SOURCE / "common" / "scripted_diplomatic_actions")
    assert set(actions) == {"scripted_diplomatic_actions"}
    action = get(actions["scripted_diplomatic_actions"], "rn_rename_subject")
    visible = get(action, "visible")
    assert ("rn_sub_may_edit", "=", "yes") in visible
    assert ("ROOT", "=", [("is_ai", "=", "no")]) in visible
    for key, value in (
        ("requires_acceptance", "no"),
        ("cost", "0"),
        ("command_power", "0"),
        ("show_acceptance_on_action_button", "no"),
    ):
        assert get(action, key) == value, key
    assert get(action, "ai_desire") == [("base", "=", "0")]
    guard = get(get(action, "complete_effect"), "if")
    assert ("rn_sub_may_edit", "=", "yes") in get(guard, "limit")
    assert ("ROOT", "=", [("set_country_flag", "=", "rn_sub_open_country")]) in guard
    for lang in ("english", "polish"):
        text = (SOURCE / "localisation" / lang / f"rn_inline_subjects_l_{lang}.yml").read_text(
            encoding="utf-8-sig"
        )
        assert re.search(r'^ RN_RENAME_SUBJECT_TITLE:0 "£edit_list_icon ', text, re.MULTILINE)
        assert "RN_SUB_DEBUG" not in text, lang
        assert "RN_SUB_BUTTON" not in text, lang


def _check_carrier() -> None:
    """The country-name carrier is written in one source file only.

    ``rn_country_name_carrier.txt`` holds the only ``set_cosmetic_tag`` and
    ``drop_cosmetic_tag`` of the in-place source and of the hand-written legacy
    effects, so the planned non-cosmetic carrier replaces one file. The legacy
    generator (``modgen/features/country.py``, ``rn_apply_country_name``) still has
    its own copy; that file belongs to the stage-2 agent.
    """
    carrier = SOURCE / "common" / "scripted_effects" / "rn_country_name_carrier.txt"
    files = [
        *sorted((SOURCE / "common").rglob("*.txt")),
        MOD / "common" / "scripted_effects" / "rename_anything_effects.txt",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        uses = len(re.findall(r"(?<![a-z_])(?:set|drop)_cosmetic_tag(?![a-z_])", text))
        assert (uses > 0) == (path == carrier), path.name
    hand = files[-1].read_text(encoding="utf-8-sig")
    assert "rn_country_name_carrier_clear = yes" in hand


def _name(body: list[Any]) -> str:
    """Return the ``name`` of an element body, or an empty string.

    Args:
        body: Element body.

    Returns:
        The name.
    """
    return next((v for k, _, v in body if k == "name" and isinstance(v, str)), "")


def _subject_geometry(widgets: dict[str, Any]) -> None:
    """Editors stay in the Diplomacy view, under its header line, on the design-system grid.

    Args:
        widgets: Element name to body.
    """
    assert "rn_sub_launcher_window" not in widgets, "no title-line button any more"
    for editor, count in SUBJECT_EDITORS.items():
        win = widgets[f"capie_v1_ed__rn__{editor}"]
        x, y = xy(win)
        w, h = xy(win, "size")
        assert w == 420, editor  # noqa: PLR2004 - design-system editor width
        assert x + w <= DIPLOMACY_WIDTH, editor
        assert y >= DIPLOMACY_HEADER_TOP, editor
        tops = [xy(widgets[f"rn_subf_{editor}_{n}"])[1] for n in range(1, count + 1)]
        for n, top in enumerate(tops, start=1):
            assert xy(widgets[f"rn_subl_{editor}_{n}"])[1] + 12 == top, (editor, n)
        assert all(b - a == 42 for a, b in itertools.pairwise(tops)), editor  # noqa: PLR2004
        tabs = [widgets[f"rn_sub_{editor}_tab_{k}"] for k in ("country", "leader", "party")]
        assert all(xy(tab)[1] + 31 <= tops[0] - 12 for tab in tabs), editor
        status = widgets[f"rn_sub_{editor}_status"]
        assert xy(status)[1] >= tops[-1] + 26, editor
        assert xy(status)[1] + 14 <= h, editor


# ----------------------------------------------------------------------------- VM


class CapieVM(ProductVM):
    """ProductVM with a subject country reachable through ``var:rn_sub_target``."""

    def __init__(self, ctx: Context, *, effects: dict[str, Any] | None = None) -> None:
        """Create a player with an open subject editor and a valid CAPIE header.

        Args:
            ctx: Shared VM inputs.
            effects: Replacement effects (stubs) for one case.
        """
        super().__init__(
            effects if effects is not None else ctx.effects,
            ctx.locmap,
            ctx.chars,
            "party",
            tag="FRA",
            triggers=ctx.triggers,
        )
        self.enforce = False
        self.flags = set()
        self.persistent.update(
            rn_sub_epoch=Decimal(SUB_EPOCH),
            rn_lg_epoch=Decimal(LEGACY_EPOCH),
            rn_sub_target=Country(SUBJECT_TAG),
        )
        self.arrays["rn_sub_target_arr"] = [Country(SUBJECT_TAG)]
        self.subject: dict[str, Any] = {
            "exists": True,
            "is_subject": True,
            "persistent": {"global.num_days": self.persistent["global.num_days"]},
            "flags": set(),
            "arrays": {},
            "government": "fascism",
        }
        self.in_subject: bool = False
        self.temp.update(capie_cap=Decimal(CAPIE_API), capie_ver=Decimal(10200))
        self.temp["capie_epoch"] = Decimal(SUB_EPOCH)

    def fields(self, *names: str) -> None:
        """Put typed names into the CAPIE records (``capie_nf`` and ``capie_f<n>_*``).

        Args:
            names: One text per field, in field order.
        """
        self.temp["capie_nf"] = Decimal(len(names))
        for n, text in enumerate(names, start=1):
            codes = [CODE[c] for c in text]
            self.temp[f"capie_f{n}_err"] = Decimal(0)
            self.temp[f"capie_f{n}_at"] = Decimal(0)
            self.temp[f"capie_f{n}_len"] = Decimal(len(codes))
            for i in range(MAX_NAME):
                self.temp[f"capie_f{n}_{i}"] = Decimal(codes[i] if i < len(codes) else 0)

    def subject_state(self) -> Any:  # noqa: ANN401 - deep copy of the subject record
        """Return a comparable copy of the subject's variables and flags.

        Returns:
            ``(persistent, flags, arrays)``.
        """
        return (
            dict(self.subject["persistent"]),
            set(self.subject["flags"]),
            {k: list(v) for k, v in self.subject["arrays"].items()},
        )

    def _swap(self) -> None:
        """Exchange the player's and the subject's variables, arrays, flags, tag and government."""
        s = self.subject
        self.persistent, s["persistent"] = s["persistent"], self.persistent
        self.arrays, s["arrays"] = s["arrays"], self.arrays
        self.flags, s["flags"] = s["flags"], self.flags
        self.government, s["government"] = s["government"], self.government
        self.tag = SUBJECT_TAG if not self.in_subject else self.root_tag
        self.in_subject = not self.in_subject

    def _in_scope(self, key: str) -> bool:
        """Return whether a block key switches to another scope this VM models.

        Args:
            key: Node key.

        Returns:
            True for ``var:rn_sub_target`` and ``ROOT``.
        """
        return key == "var:rn_sub_target" or (key == "ROOT" and bool(self.in_subject))

    @override
    def condition(self, nodes: list[Any]) -> bool:
        """Evaluate triggers, with the subject scope and its country triggers.

        Args:
            nodes: Trigger nodes.

        Returns:
            Whether every trigger holds.
        """
        for node in nodes:
            key, _, value = node
            if self._in_scope(key):
                answer = self._scoped(lambda v=value: self.condition(v))
            elif key == "ROOT":
                answer = self.condition(value)
            elif key == "rn_sub_may_edit":
                answer = self.condition(self.triggers[key]) == (value == "yes")
            elif key == "exists":
                answer = self.subject["exists"] == (value == "yes") if self.in_subject else True
            elif key == "is_subject_of":
                answer = self.in_subject and self.subject["is_subject"]
            else:
                answer = super().condition([node])
            if not answer:
                return False
        return True

    @override
    def localized(self, name: str) -> str:
        """Resolve scripted localisation in ROOT's scope, as ``[ROOT.<name>]`` does.

        Args:
            name: Scripted loc name.

        Returns:
            The text.
        """
        if self.in_subject:
            return str(self._scoped(lambda: super(CapieVM, self).localized(name)))
        return str(super().localized(name))

    def _scoped(self, call: Any) -> Any:  # noqa: ANN401 - result of the wrapped call
        """Run ``call`` in the other scope and swap back.

        Args:
            call: Callable without arguments.

        Returns:
            Its result.
        """
        if not self.subject["exists"] and not self.in_subject:
            return False
        self._swap()
        try:
            return call()
        finally:
            self._swap()

    @override
    def execute(self, nodes: list[Any]) -> None:
        """Execute effects, with the subject scope and its character loop.

        Args:
            nodes: Effect nodes.
        """
        run: list[Any] = []
        for node in nodes:
            key, _, value = node
            if key == "drop_cosmetic_tag":
                if run:
                    super().execute(run)
                    run = []
                assert value == "yes", value
                self.requests.append([("drop_cosmetic_tag", "=", self.tag)])
                continue
            if not (self._in_scope(key) or (key == "every_character" and self.in_subject)):
                run.append(node)
                continue
            if run:
                super().execute(run)
                run = []
            if key == "every_character":
                limit = get(value, "limit")
                assert limit == [("is_country_leader", "=", "yes")], limit
                self.execute([n for n in value if n[0] != "limit"])
            else:
                self._scoped(lambda v=value: self.execute(v))
        if run:
            super().execute(run)


def _case(ctx: Context, *, kind: int, names: tuple[str, ...]) -> CapieVM:
    """Return a VM with the subject editor of ``kind`` open and its fields typed.

    Args:
        ctx: Shared VM inputs.
        kind: 1 country, 2 leader, 3 party.
        names: Field texts.

    Returns:
        The VM.
    """
    vm = CapieVM(ctx)
    vm.flags.add(KIND_FLAGS[kind])
    vm.fields(*names)
    return vm


APPLY = {1: "rn_sub_apply_country", 2: "rn_sub_apply_leader", 3: "rn_sub_apply_party"}
"""rn_sub_kind to its Apply effect."""


def run_capie_header(ctx: Context) -> int:
    """The CAPIE header: presence, API level, sentinels and the opening epoch.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases: list[tuple[dict[str, Decimal], Decimal, int]] = [
        ({}, Decimal(SUB_EPOCH), 0),
        ({"capie_cap": Decimal(0)}, Decimal(SUB_EPOCH), ERR_NO_CAPIE),
        ({"capie_cap": Decimal(1)}, Decimal(SUB_EPOCH), ERR_NO_CAPIE),
        ({"capie_epoch": Decimal(-1)}, Decimal(SUB_EPOCH), ERR_STALE),
        ({"capie_epoch": Decimal(-2)}, Decimal(SUB_EPOCH), ERR_SETUP),
        ({"capie_epoch": Decimal(-3)}, Decimal(SUB_EPOCH), ERR_SETUP),
        ({"capie_epoch": Decimal(SUB_EPOCH - 1)}, Decimal(SUB_EPOCH), ERR_STALE),
        ({"capie_epoch": Decimal(0)}, Decimal(0), ERR_STALE),
    ]
    for temps, opened, want in cases:
        vm = CapieVM(ctx)
        vm.temp.update(temps)
        if "capie_cap" in temps and temps["capie_cap"] == 0:
            vm.temp.pop("capie_cap")
        vm.temp["rn_cv1_open"] = opened
        vm.run("rn_cv1_header")
        assert vm.temp["rn_cv1_err"] == want, (temps, opened)
    return len(cases)


def run_capie_fields(ctx: Context) -> int:
    """Field adapters: valid copy, encoder reasons, the 84-code alphabet, a missing field.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    vm = CapieVM(ctx)
    vm.fields("Łódź", "Żółta")
    vm.run("rn_cv1_take_two")
    assert vm.temp.get("rn_cv1_err", Decimal(0)) == 0
    assert [vm.temp[f"rn_native_{i}"] for i in range(4)] == [Decimal(CODE[c]) for c in "Łódź"]
    assert vm.temp["rn_nativeb_len"] == Decimal(len("Żółta"))
    cases = 1
    for field, capie_err, want_err, want_why in (
        (1, 1, ERR_FIELD, 1),
        (2, 2, ERR_FIELD, 2),
        (1, 6, ERR_FIELD, 3),
        (2, 5, ERR_FIELD, 3),
    ):
        vm = CapieVM(ctx)
        vm.fields("Abc", "Def")
        vm.temp[f"capie_f{field}_err"] = Decimal(capie_err)
        vm.temp[f"capie_f{field}_len"] = Decimal(0)
        vm.temp["rn_cv1_err"] = Decimal(0)
        vm.run("rn_cv1_take_two")
        assert (vm.temp["rn_cv1_err"], vm.temp["rn_cv1_field"]) == (want_err, field)
        vm.run("rn_cv1_reason")
        assert vm.temp["rn_cv1_why"] == want_why, (field, capie_err)
        cases += 1
    vm = CapieVM(ctx)
    vm.fields("Abc")
    vm.temp["capie_f1_1"] = Decimal(93)  # "À": valid for CAPIE, outside Rename Anything's alphabet
    vm.temp["rn_cv1_err"] = Decimal(0)
    vm.run("rn_cv1_take_one")
    assert vm.temp["rn_cv1_err"] == ERR_ALPHABET
    vm.run("rn_cv1_reason")
    assert vm.temp["rn_cv1_why"] == 4  # noqa: PLR2004 - alphabet reason
    vm = CapieVM(ctx)
    vm.fields("Abc")
    vm.temp["rn_cv1_err"] = Decimal(0)
    vm.run("rn_cv1_take_two")
    assert (vm.temp["rn_cv1_err"], vm.temp["rn_cv1_field"]) == (ERR_FIELD, 2), "missing field 2"
    return cases + 2


def _decoded(request: list[Any]) -> Iterator[str]:
    """Yield every string value of a rendered ``meta_effect`` request.

    Args:
        request: Rendered ``text`` nodes.

    Yields:
        String values.
    """
    for _, _, v in walk(request):
        if isinstance(v, str):
            yield v


def run_subject_apply(ctx: Context) -> int:
    """The three subject setters write only to the subject and close the editor.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    vm = _case(ctx, kind=1, names=("Nowa Gdynia", "nowogdyński"))
    root_before = dict(vm.persistent)
    root_arrays = {k: list(v) for k, v in vm.arrays.items() if k.startswith("capie_cn_")}
    vm.run(APPLY[1])
    assert vm.temp["rn_cv1_err"] == 0
    assert not vm.requests, "the name layer writes no cosmetic tag (flag and colour stay)"
    assert _layer_text(vm.subject["arrays"]["capie_cn_n"]) == "Nowa Gdynia"
    assert _layer_text(vm.subject["arrays"]["capie_cn_a"]) == "nowogdyński"
    assert vm.subject["persistent"]["capie_cn_ver"] == 1
    assert "capie_cn_rev" in vm.subject["persistent"], "the commit variable comes last"
    assert {k: list(v) for k, v in vm.arrays.items() if k.startswith("capie_cn_")} == root_arrays
    assert "capie_cn_ver" not in vm.persistent, "the layer is written on the subject only"
    assert "rn_custom_name" in vm.subject["flags"]
    assert "rn_cn_migrated" in vm.subject["flags"]
    assert "rn_ip_cd_country_until" in vm.subject["persistent"]
    assert "rn_ip_cd_country_until" not in vm.persistent, "cooldown on the subject only"
    assert "rn_sub_open_country" not in vm.flags
    assert vm.persistent["rn_sub_epoch"] == root_before["rn_sub_epoch"] + 1
    assert not vm.arrays["rn_sub_target_arr"]
    cases += 1
    vm = _case(ctx, kind=2, names=("Jan Żółć",))
    vm.run(APPLY[2])
    assert vm.temp["rn_cv1_err"] == 0
    assert get(vm.requests[0], "set_character_name") == "Jan Żółć"
    assert "rn_ip_cd_leader_until" in vm.subject["persistent"]
    cases += 1
    for government in ("democratic", "communism", "fascism", "neutrality"):
        vm = _case(ctx, kind=3, names=("PZP", "Partia Zmiany Pól"))
        vm.subject["government"] = government
        vm.run(APPLY[3])
        assert vm.temp["rn_cv1_err"] == 0, government
        setter = get(vm.requests[0], "set_party_name")
        assert get(setter, "ideology") == government
        assert get(setter, "name") == "PZP"
        assert get(setter, "long_name") == "Partia Zmiany Pól"
        assert "rn_ip_cd_party_until" in vm.subject["persistent"]
        cases += 1
    vm = _case(ctx, kind=1, names=("Polska", "polski"))
    vm.run(APPLY[1])
    assert vm.localized("RN_SUB_STATUS") == ctx.chars["RN_IP_HINT"]
    cases += 1
    return cases + run_layer_migration(ctx)


def _layer_text(codes: list[Any]) -> str:
    """Return the text of a code array of the name layer.

    Args:
        codes: Codes as stored by ``add_to_array``.

    Returns:
        The text (Rename Anything's 84-code table).
    """
    alphabet = str(NATIVE_ALPHABET)
    return "".join(alphabet[int(c) - 1] for c in codes)


def run_layer_migration(ctx: Context) -> int:
    """Legacy RN1 names: the first Apply or Reset drops the RN1 cosmetic tag once, never again.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    # A subject renamed with CAPIE 1.1 (RN1 cosmetic tag + flag, no layer): Apply migrates it.
    vm = _case(ctx, kind=1, names=("Kanadia", "kanadyjski"))
    vm.subject["flags"].add("rn_custom_name")
    vm.run(APPLY[1])
    assert vm.temp["rn_cv1_err"] == 0
    assert vm.requests == [[("drop_cosmetic_tag", "=", SUBJECT_TAG)]], vm.requests
    assert _layer_text(vm.subject["arrays"]["capie_cn_n"]) == "Kanadia"
    assert "rn_cn_migrated" in vm.subject["flags"]
    cases += 1
    # Reset after a migration (or after a console reset of a layer) never drops a cosmetic tag.
    vm.enforce = False
    vm.requests.clear()
    vm._scoped(lambda: vm.run("rn_country_name_carrier_clear"))  # noqa: SLF001 - VM scope helper
    assert not vm.requests, "a migrated country keeps any cosmetic tag the game sets later"
    assert "capie_cn_ver" not in vm.subject["persistent"]
    assert not vm.subject["arrays"]["capie_cn_n"]
    assert not vm.subject["arrays"]["capie_cn_a"]
    assert "rn_custom_name" not in vm.subject["flags"]
    assert "capie_cn_rev" in vm.subject["persistent"]
    cases += 1
    # Reset of a legacy country drops the RN1 tag once.
    vm = _case(ctx, kind=1, names=("Kanadia", "kanadyjski"))
    vm.enforce = False
    vm.subject["flags"].add("rn_custom_name")
    vm._scoped(lambda: vm.run("rn_country_name_carrier_clear"))  # noqa: SLF001 - VM scope helper
    assert vm.requests == [[("drop_cosmetic_tag", "=", SUBJECT_TAG)]], vm.requests
    vm.requests.clear()
    vm._scoped(lambda: vm.run("rn_country_name_carrier_clear"))  # noqa: SLF001 - VM scope helper
    assert not vm.requests, "the legacy tag is dropped once"
    cases += 1
    # A country renamed for the first time never loses a cosmetic tag.
    vm = _case(ctx, kind=1, names=("Kanadia", "kanadyjski"))
    vm.run(APPLY[1])
    assert not vm.requests
    cases += 1
    return cases


REJECTIONS: list[tuple[str, Callable[[CapieVM], object], int]] = [
    ("not a subject", lambda v: v.subject.update(is_subject=False), ERR_RIGHTS),
    ("subject gone", lambda v: v.subject.update(exists=False), ERR_RIGHTS),
    ("AI actor", lambda v: setattr(v, "ai", True), ERR_RIGHTS),
    ("other editor open", lambda v: (v.flags.clear(), v.flags.add(KIND_FLAGS[2])), ERR_RIGHTS),
    ("legacy window open", lambda v: v.flags.add("rn_open"), ERR_RIGHTS),
    ("legacy input open", lambda v: v.flags.add("rn_input"), ERR_RIGHTS),
    ("no pinned target", lambda v: v.persistent.pop("rn_sub_target"), ERR_RIGHTS),
    ("two pins", lambda v: v.arrays["rn_sub_target_arr"].append(Country("GER")), ERR_RIGHTS),
    (
        "subject cooldown",
        lambda v: v.subject["persistent"].update(
            rn_ip_cd_country_until=v.persistent["global.num_days"] + 3
        ),
        ERR_COOLDOWN,
    ),
    ("no CAPIE", lambda v: v.temp.pop("capie_cap"), ERR_NO_CAPIE),
    ("sentinel -1", lambda v: v.temp.update(capie_epoch=Decimal(-1)), ERR_STALE),
    ("other opening", lambda v: v.temp.update(capie_epoch=Decimal(SUB_EPOCH + 1)), ERR_STALE),
    ("registry full", lambda v: v.temp.update(capie_epoch=Decimal(-2)), ERR_SETUP),
    ("empty adjective", lambda v: v.temp.update(capie_f2_err=Decimal(1)), ERR_FIELD),
]
"""Subject country Apply rejections: label, change to a ready VM, expected rn_cv1_err."""

REJECTION_STATUS = {
    ERR_RIGHTS: "RN_SUB_ERR_RIGHTS",
    ERR_NO_CAPIE: "RN_IP_ERR_NO_BRIDGE",
    ERR_STALE: "RN_IP_ERR_STALE",
    ERR_SETUP: "RN_CV1_ERR_SETUP",
    ERR_FIELD: "RN_IP_ERR_COUNTRY_ADJ_EMPTY",
}
"""Status line key the subject editor shows for a rejection code."""


def _without_status(persistent: dict[str, Any]) -> dict[str, Any]:
    """Return the variables without the display-only status line.

    Args:
        persistent: Country variables.

    Returns:
        A copy without ``rn_cv1_st_*``.
    """
    return {k: v for k, v in persistent.items() if not k.startswith("rn_cv1_st_")}


def run_subject_rejections(ctx: Context) -> int:
    """Every rejection changes nothing on either country and names its reason.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    for label, mutate, want in REJECTIONS:
        vm = _case(ctx, kind=1, names=("Polska", "polski"))
        mutate(vm)
        (persistent, arrays, flags), subject = vm.state(), vm.subject_state()
        vm.run(APPLY[1])
        assert vm.temp["rn_cv1_err"] == want, label
        assert not vm.requests, label
        assert vm.subject_state() == subject, label
        assert _without_status(vm.persistent) == _without_status(persistent), label
        assert (vm.arrays, vm.flags) == (arrays, flags), label
        assert vm.persistent["rn_cv1_st_err"] == want, label
        if want in REJECTION_STATUS:
            assert vm.localized("RN_SUB_STATUS") == ctx.chars[REJECTION_STATUS[want]], label
    return len(REJECTIONS)


def run_legacy_field(ctx: Context) -> int:
    """The legacy text field: success hands a filled buffer to rn_apply_input; failures don't.

    ``rn_apply_input`` (the legacy setters) is replaced by a stub that records the
    buffer it receives; the real one is covered by the legacy tests.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    effects = dict(ctx.effects)
    effects["rn_apply_input"] = [("set_variable", "=", [("rn_stub_applied", "=", "1")])]
    vm = CapieVM(ctx, effects=effects)
    vm.flags.add("rn_input")
    vm.temp["capie_epoch"] = Decimal(LEGACY_EPOCH)
    vm.fields("Wrocław")
    vm.run("rn_lg_field_apply")
    assert vm.persistent["rn_stub_applied"] == 1
    assert vm.arrays["rn_buf"] == [Decimal(CODE[c]) for c in "Wrocław"]
    assert vm.persistent["rn_len"] == Decimal(len("Wrocław"))
    cases = 1
    for label, mutate, want, keyboard in (
        ("no CAPIE", lambda v: v.temp.pop("capie_cap"), ERR_NO_CAPIE, True),
        ("stale", lambda v: v.temp.update(capie_epoch=Decimal(-1)), ERR_STALE, False),
        ("closed", lambda v: v.flags.discard("rn_input"), ERR_STALE, False),
        ("too long", lambda v: v.temp.update(capie_f1_err=Decimal(2)), ERR_FIELD, False),
    ):
        vm = CapieVM(ctx, effects=effects)
        vm.flags.add("rn_input")
        vm.temp["capie_epoch"] = Decimal(LEGACY_EPOCH)
        vm.fields("Wrocław")
        mutate(vm)
        buffer = list(vm.arrays.get("rn_buf", []))
        vm.run("rn_lg_field_apply")
        assert "rn_stub_applied" not in vm.persistent, label
        assert vm.arrays.get("rn_buf", []) == buffer, label
        assert vm.persistent["rn_cv1_st_err"] == want, label
        assert ("rn_lg_keyboard" in vm.flags) == keyboard, label
        cases += 1
    vm.flags.add("rn_lg_keyboard")
    vm.persistent["rn_cv1_st_err"] = Decimal(ERR_NO_CAPIE)
    assert vm.localized("RN_LG_STATUS") == ctx.chars["RN_LG_ERR_NO_CAPIE"]
    assert vm.localized("RN_LG_KB_STATUS") == ctx.chars["RN_LG_KB_NO_CAPIE"]
    return cases
