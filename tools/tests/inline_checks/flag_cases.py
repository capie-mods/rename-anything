"""Flag picker and flag catalog: structure, geometry and a small multi-country VM.

Three parts.

* Structure. The two generated pickers (``capie_v1_ed__rn__flag`` and
  ``__subflag``) follow the CAPIE grammar (CONTRACT section 3) without text
  fields, carry a hidden epoch, have Enter only on Apply, stay within the
  registry limit of eight editors per mod id, and every element, effect,
  trigger and localisation key they name exists.
* Geometry. Rectangles from the generated GUI: every control inside the 420 px
  window, no two controls overlapping, the grid left of the Apply column, the
  flags inside their vanilla frames, and the name editor's new tab row clear of
  its fields.
* VM. :class:`FlagVM` runs the real hand-written effects
  (``tools/inline_editor``) and the generated catalog effects (``mod/``) over
  several countries: the stem writer for every catalog index, the cosmetic
  snapshot for every known cosmetic tag, every country pool, the game's flag
  choice, and the picker itself (open, navigation, Apply with the CAPIE
  records, every rejection, the pool rule, Restore, the daily cosmetic check).
  A few mutated effects must make the cases fail.

The VM is not the HOI4 parser and proves nothing about the game, CAPIE or
multiplayer; it checks that the script does what the design says.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from inline_checks.constants import ACTIONS_Y, MOD, PANEL_WIDTH, SOURCE, VM_TODAY
from inline_checks.fixtures import parse
from inline_checks.geometry import disjoint, inside
from inline_checks.tree import declarations, get, models_of, walk, xy
from modgen.common import LANGS
from modgen.features import flag_picker
from modgen.features.catalog_common import LETTERS, OTHER_LETTER, TAG_LEN, pack
from modgen.features.flags import IDEOLOGIES, split_stem

Rect = tuple[int, int, int, int]
"""``(left, top, right, bottom)``."""

TAG_LITERAL = re.compile(r"[A-Z][A-Z0-9]{2}")
"""A country tag used as a scope."""

NUMBER = re.compile(r"-?\d+(\.\d+)?")
"""A numeric literal."""

ERR = {"capie": 10, "cooldown": 11, "stale": 12, "old": 15, "layer": 16, "pool": 17, "rights": 20}
"""Flag picker error codes (temp ``rn_cv1_err``)."""

PICKER_EPOCH = 1
"""``rn_fp_epoch`` after the first opening in a fresh VM."""

PAGE = 10
"""Flags or countries per page."""

LIST_VIEW = 2
"""``rn_fp_view`` of the country list."""

MAX_EDITORS_PER_MOD = 8
"""CAPIE registry limit per mod id (CONTRACT section 3)."""

FLAG_SIZE = {"large": (82, 52), "medium": (41, 26)}
"""Pixel sizes of the game's large and medium flags."""

FRAME_SIZE = {"GFX_large_flag_frame": (92, 58), "GFX_small_flag_frame_selectable": (51, 36)}
"""Pixel sizes of the vanilla frames (one frame of the two-frame sprite)."""

SPRITE_SIZE = {
    "GFX_button_94x31": (94, 31),
    "GFX_button_123x34": (123, 34),
    "GFX_opinion_arrow_left": (17, 17),
    "GFX_opinion_arrow_right": (17, 17),
    "GFX_closebutton_16": (16, 16),
    "GFX_rn_hit_row": flag_picker.ROW,
    "GFX_rn_hit_letter": (flag_picker.LETTER_W, flag_picker.LETTER_H),
    "GFX_rn_hit_other": (flag_picker.OTHER_W, flag_picker.LETTER_H),
    "GFX_rn_hit_row108": (108, 16),
    "GFX_pol_leader_frame": (172, 258),
    "GFX_diplo_leader_frame": (134, 175),
    "GFX_rnp_1": (156, 210),
}
"""Drawn sizes of the button sprites the pickers use."""


# ----------------------------------------------------------------------------- inputs


@dataclass
class Catalog:
    """The generated catalog as the tests read it back from ``mod/``."""

    stems: list[str]
    """Stem of each index (index ``n`` is ``stems[n - 1]``)."""

    tags: list[str]
    """Group tags in group order (group ``g`` is ``tags[g - 1]``)."""

    cosmetics: list[str]
    """Known cosmetic tags of the snapshot chain."""

    effects: dict[str, Any]
    """Generated effect bodies."""


def read_catalog() -> Catalog:
    """Read the generated catalog files.

    Returns:
        The catalog.
    """
    gfx = (MOD / "interface" / "rn_flag_catalog.gfx").read_text(encoding="utf-8")
    pairs = re.findall(
        r'name = "GFX_rnf_(\d+)" texturefile = "gfx/flags/([A-Za-z0-9_]+)\.tga"', gfx
    )
    stems = [s for _, s in sorted(pairs, key=lambda p: int(p[0]))]
    assert [int(n) for n, _ in sorted(pairs, key=lambda p: int(p[0]))] == list(
        range(1, len(stems) + 1)
    )
    effects = declarations(MOD / "common" / "scripted_effects", "rn_flag_catalog.txt")
    tags = [
        get(get(v, "limit"), "original_tag")
        for k, _, v in effects["rn_fp_group_of"]
        if k in {"if", "else_if"}
    ]
    cosmetics = [
        get(get(v, "limit"), "has_cosmetic_tag")
        for k, _, v in effects["rn_fp_cos_write"]
        if k in {"if", "else_if"}
    ]
    return Catalog(stems, tags, cosmetics, effects)


def pool_of(cat: Catalog, tag: str) -> list[int]:
    """Return the reference pool of a tag (design 2.2).

    The tag's own key first, then the other keys sorted; each key bare, then by ideology.

    Args:
        cat: Catalog.
        tag: Group tag, or an empty string for "Other".

    Returns:
        Catalog indices.
    """
    index = {s: n for n, s in enumerate(cat.stems, start=1)}
    keys: dict[str, dict[str | None, int]] = {}
    for stem in cat.stems:
        key, ideology = split_stem(stem)
        keys.setdefault(key, {})[ideology] = index[stem]
    tagset = set(cat.tags)

    def owner(key: str) -> str:
        """Return the group tag of a key.

        Args:
            key: Flag key.

        Returns:
            Its tag, or an empty string.
        """
        tag = key[:TAG_LEN]
        return tag if tag in tagset and (len(key) == TAG_LEN or key[TAG_LEN] == "_") else ""

    chosen = sorted((k for k in keys if owner(k) == tag), key=lambda k: (k != tag, k))
    return [keys[k][i] for k in chosen for i in (None, *IDEOLOGIES) if i in keys[k]]


def game_flag(cat: Catalog, original: str, government: str, cosmetic: str | None) -> int:
    """Return the reference game flag: cosmetic + ideology, cosmetic, tag + ideology, tag.

    Args:
        cat: Catalog.
        original: Original tag.
        government: Ideology group.
        cosmetic: Cosmetic tag or None.

    Returns:
        Catalog index, 0 when none matches.
    """
    index = {s: n for n, s in enumerate(cat.stems, start=1)}
    candidates = [f"{cosmetic}_{government}", cosmetic] if cosmetic in set(cat.cosmetics) else []
    candidates += [f"{original}_{government}", original]
    return next((index[c] for c in candidates if c in index), 0)


def decode(codes: list[Decimal], length: Decimal) -> str:
    """Decode a packed stem (CONTRACT 17.3).

    Args:
        codes: Array elements.
        length: Character count.

    Returns:
        The text.
    """
    alphabet = "abcdefghijklmnopqrstuvwxyz" + LETTERS + "0123456789_"
    chars = []
    for value in codes:
        v = int(value)
        chars += [v // 4096, v // 64 % 64, v % 64]
    text = "".join(alphabet[c - 1] for c in chars[: int(length)])
    assert all(c == 0 for c in chars[int(length) :]), "padding"
    assert all(c > 0 for c in chars[: int(length)]), "code 0 inside"
    return text


# ----------------------------------------------------------------------------- VM


@dataclass
class Nation:
    """One country of the VM."""

    tag: str
    """Tag."""

    original: str = ""
    """Original tag (the tag itself when empty)."""

    government: str = "neutrality"
    """Ideology group."""

    cosmetic: str | None = None
    """Cosmetic tag."""

    overlord: str | None = None
    """Overlord's tag when a subject."""

    ai: bool = True
    """AI-controlled."""

    exists: bool = True
    """On the map."""

    vars: dict[str, Any] = field(default_factory=dict)
    """Country variables."""

    arrays: dict[str, list[Any]] = field(default_factory=dict)
    """Country arrays."""

    flags: set[str] = field(default_factory=set)
    """Country flags."""

    characters: list[str] = field(default_factory=list)
    """Characters of a country (their VM tags); empty for a character."""

    leader: bool = False
    """A character that leads its country."""


@dataclass(frozen=True)
class Ref:
    """A country value (a scope stored in a variable or an array)."""

    tag: str
    """Tag."""


class FlagVM:
    """Executes parsed effects and triggers over several countries.

    Scope keys: ROOT, THIS, PREV, ``var:<name>``, ``overlord`` and tag literals.
    Bare variable names read the temp variable first, then the scope's variable,
    as the legacy paging effect relies on.
    """

    def __init__(self, effects: dict[str, Any], triggers: dict[str, Any], root: str) -> None:
        """Create a VM with ROOT as the only scope.

        Args:
            effects: Effect bodies (source and generated).
            triggers: Scripted trigger bodies.
            root: Tag of the player.
        """
        self.effects = effects
        self.triggers = triggers
        self.nations: dict[str, Nation] = {}
        self.root = root
        self.stack: list[str] = [root]
        self.temp: dict[str, Any] = {}
        self.rules = {
            "rn_edit_rights": "RN_RIGHTS_SUBJECTS",
            "rn_flag_pool": "RN_FLAG_POOL_ALL",
            "rn_rename_cooldown": "RN_COOLDOWN_DEFAULT",
        }
        self.writes: list[tuple[str, str]] = []

    def nation(self, tag: str, **kwargs: Any) -> Nation:  # noqa: ANN401 - Nation fields
        """Add or return a country.

        Args:
            tag: Tag.
            **kwargs: Nation fields for a new country.

        Returns:
            The country.
        """
        if tag not in self.nations:
            self.nations[tag] = Nation(tag, **kwargs)
        return self.nations[tag]

    @property
    def here(self) -> Nation:
        """Return the current scope.

        Returns:
            The country.
        """
        return self.nations[self.stack[-1]]

    # -- values

    def scope_of(self, key: str) -> str | None:  # noqa: PLR0911 - one return per scope keyword
        """Return the tag a scope key switches to, or None when it is not a scope key.

        Args:
            key: Node key.

        Returns:
            Tag or None.
        """
        if key == "ROOT":
            return self.root
        if key == "THIS":
            return self.stack[-1]
        if key == "PREV":
            return self.stack[-2] if len(self.stack) > 1 else self.stack[-1]
        if key == "overlord":
            lord = self.here.overlord
            assert lord is not None, "overlord scope of an independent country"
            return lord
        if key.startswith("var:"):
            value = self.here.vars.get(key[4:])
            assert isinstance(value, Ref), ("var scope", key, value)
            return value.tag
        if TAG_LITERAL.fullmatch(key) and key in self.nations:
            return key
        return None

    def value(self, token: str) -> Any:  # noqa: ANN401, PLR0911 - every value kind of the script
        """Resolve a script value.

        Args:
            token: Literal, variable reference or scope.

        Returns:
            Decimal or :class:`Ref`.
        """
        if NUMBER.fullmatch(token):
            return Decimal(token)
        if token in {"global.num_days", "global.date"}:
            return Decimal(VM_TODAY)
        scope = self.scope_of(token)
        if scope is not None:
            return Ref(scope)
        if token.startswith("temp_var:"):
            return self.temp.get(token[9:], Decimal(0))
        if "." in token:
            head, _, rest = token.partition(".")
            tag = self.scope_of(head)
            assert tag is not None, token
            self.stack.append(tag)
            try:
                return self.value(rest)
            finally:
                self.stack.pop()
        if "^" in token:
            name, _, idx = token.partition("^")
            items = self.array(name)
            if idx == "num":
                return Decimal(len(items))
            i = int(self.value(idx))
            return items[i] if 0 <= i < len(items) else Decimal(0)
        if token in self.temp:
            return self.temp[token]
        return self.here.vars.get(token, Decimal(0))

    def array(self, name: str) -> list[Any]:
        """Return an array of the current scope or of a scoped name (``ROOT.x``).

        Args:
            name: Array name.

        Returns:
            The live list.
        """
        if "." in name:
            head, _, rest = name.partition(".")
            tag = self.scope_of(head)
            assert tag is not None, name
            return self.nations[tag].arrays.setdefault(rest, [])
        return self.here.arrays.setdefault(name, [])

    # -- triggers

    def condition(self, nodes: list[Any]) -> bool:
        """Return whether every trigger holds.

        Args:
            nodes: Trigger nodes.

        Returns:
            The result.
        """
        return all(self.trigger(key, op, value) for key, op, value in nodes)

    def scoped(self, tag: str, call: Any) -> Any:  # noqa: ANN401 - any callable result
        """Run ``call`` with ``tag`` pushed as the scope.

        Args:
            tag: Scope.
            call: Callable without arguments.

        Returns:
            Its result.
        """
        self.stack.append(tag)
        try:
            return call()
        finally:
            self.stack.pop()

    def compare(self, nodes: list[Any]) -> bool:
        """Evaluate a ``check_variable`` body.

        Args:
            nodes: ``[(lhs, op, rhs)]``.

        Returns:
            The comparison.
        """
        ((lhs, op, rhs),) = nodes
        a, b = self.value(lhs), self.value(rhs)
        if op == "=":
            return bool(a == b)
        assert isinstance(a, Decimal), lhs
        assert isinstance(b, Decimal), rhs
        return a < b if op == "<" else a > b

    def trigger(self, key: str, op: str, value: Any) -> bool:  # noqa: ANN401, PLR0911 - one branch per trigger
        """Evaluate one trigger.

        Args:
            key: Trigger key.
            op: Operator.
            value: Value.

        Returns:
            The result.
        """
        here = self.here
        tag = self.scope_of(key)
        if tag is not None:
            return bool(self.scoped(tag, lambda: self.condition(value)))
        if key == "any_character":
            return any(self.scoped(c, lambda: self.condition(value)) for c in here.characters)
        if key == "AND":
            return self.condition(value)
        if key == "OR":
            return any(self.trigger(*n) for n in value)
        if key == "NOT":
            return not any(self.trigger(*n) for n in value)
        if key == "check_variable":
            return self.compare(value)
        if key in {"set_temp_variable", "subtract_from_temp_variable"}:
            self.effect(key, op, value)
            return True
        if key in self.triggers and value in {"yes", "no"}:
            return self.condition(self.triggers[key]) == (value == "yes")
        facts = {
            "has_variable": lambda: value in here.vars,
            "has_country_flag": lambda: value in here.flags,
            "tag": lambda: here.tag == (self.scope_of(value) or value),
            "original_tag": lambda: (here.original or here.tag) == value,
            "has_cosmetic_tag": lambda: here.cosmetic == value,
            "has_government": lambda: here.government == value,
            "is_subject": lambda: (here.overlord is not None) == (value == "yes"),
            "is_subject_of": lambda: here.overlord == self.scope_of(value),
            "is_ai": lambda: here.ai == (value == "yes"),
            "exists": lambda: here.exists == (value == "yes"),
            "is_country_leader": lambda: here.leader == (value == "yes"),
            "always": lambda: value == "yes",
            "has_game_rule": lambda: (
                self.rules.get(get(value, "rule"), get(value, "rule").upper() + "_ON")
                == get(value, "option")
            ),
            "is_in_array": lambda: (
                self.value(get(value, "value")) in self.array(get(value, "array"))
            ),
            "any_other_country": lambda: any(
                not n.ai for t, n in self.nations.items() if t != here.tag
            ),
        }
        assert key in facts, ("trigger not modelled", key)
        return bool(facts[key]())

    # -- effects

    def run(self, name: str) -> None:
        """Run a scripted effect in the current scope.

        Args:
            name: Effect name.
        """
        self.execute(self.effects[name])

    def execute(self, nodes: list[Any]) -> None:
        """Execute effect nodes with if/else_if/else chaining.

        Args:
            nodes: Effect nodes.
        """
        taken: bool | None = None
        for key, op, value in nodes:
            if key in {"if", "else_if", "else"}:
                if key == "if":
                    taken = False
                limit = next((v for k, _, v in value if k == "limit"), [])
                if taken is not True and (key == "else" or self.condition(limit)):
                    self.execute([n for n in value if n[0] != "limit"])
                    taken = True
                continue
            taken = None
            self.effect(key, op, value)

    def write(self, name: str, value: Any) -> None:  # noqa: ANN401 - Decimal or Ref
        """Set a country variable and record the write.

        Args:
            name: Variable.
            value: Value.
        """
        self.here.vars[name] = value
        self.writes.append((self.here.tag, name))

    def effect(self, key: str, op: str, value: Any) -> None:  # noqa: ANN401, ARG002, C901, PLR0911 - one branch per effect
        """Execute one effect.

        Args:
            key: Effect key.
            op: Operator (unused).
            value: Value.
        """
        here = self.here
        tag = self.scope_of(key)
        if tag is not None:
            self.scoped(tag, lambda: self.execute(value))
            return
        if key in self.effects and value == "yes":
            self.run(key)
            return
        if key == "log":
            return
        if key == "every_character":
            limit = next((v for k, _, v in value if k == "limit"), [])
            body = [n for n in value if n[0] != "limit"]
            for c in list(here.characters):
                self.scoped(c, lambda: self.condition(limit) and self.execute(body))
            return
        if key == "for_each_loop":
            params = {k: v for k, _, v in value if k in {"array", "value", "index"}}
            body = [n for n in value if n[0] not in {"array", "value", "index"}]
            for i, item in enumerate(list(self.array(params["array"]))):
                self.temp[params.get("value", "v")] = item
                self.temp[params.get("index", "i")] = Decimal(i)
                self.execute(body)
            return
        if key == "modulo_temp_variable":
            name, by = get(value, "var"), self.value(get(value, "value"))
            self.temp[name] = self.temp.get(name, Decimal(0)) % by
            return
        if key in {"clear_variable", "clear_array", "set_country_flag", "clr_country_flag"}:
            {
                "clear_variable": lambda: here.vars.pop(value, None),
                "clear_array": lambda: here.arrays.pop(value, None),
                "set_country_flag": lambda: here.flags.add(value),
                "clr_country_flag": lambda: here.flags.discard(value),
            }[key]()
            self.writes.append((here.tag, key + ":" + value))
            return
        ((name, _, src),) = value
        new = self.value(src)
        if key == "add_to_array":
            self.array(name).append(new)
            self.writes.append((here.tag, "array:" + name))
            return
        temp = key.endswith("_temp_variable")
        store = self.temp if temp else here.vars
        old = store.get(name, Decimal(0))
        result = {
            "set": lambda: new,
            "add": lambda: old + new,
            "subtract": lambda: old - new,
            "multiply": lambda: old * new,
            "divide": lambda: old / new,
        }[key.split("_", 1)[0]]()
        if temp:
            self.temp[name] = result
        else:
            self.write(name, result)


# ----------------------------------------------------------------------------- loading


class Inputs:
    """Effects, triggers and the catalog every VM case uses."""

    def __init__(self) -> None:
        """Load the source and generated script."""
        self.cat = read_catalog()
        self.effects = {
            **declarations(SOURCE / "common" / "scripted_effects"),
            **self.cat.effects,
        }
        self.triggers = {
            **declarations(SOURCE / "common" / "scripted_triggers"),
            **declarations(MOD / "common" / "scripted_triggers", "rn_feature_switches.txt"),
        }

    def vm(self, root: str = "FRA", effects: dict[str, Any] | None = None) -> FlagVM:
        """Return a VM with a human player, a subject and a stranger.

        Args:
            root: Player tag.
            effects: Replacement effects (mutations).

        Returns:
            The VM.
        """
        vm = FlagVM(effects if effects is not None else self.effects, self.triggers, root)
        vm.nation(root, ai=False, government="democratic")
        vm.nation("POL", government="neutrality", overlord=root)
        vm.nation("ITA", government="fascism")
        vm.nation("GER", government="fascism")
        return vm


def capie(vm: FlagVM, *, cap: int = 6, flag: int = 1, epoch: Decimal | None = None) -> None:
    """Put the CAPIE records of a flag editor's Apply into the temps.

    Args:
        vm: VM.
        cap: ``capie_cap``.
        flag: ``capie_flag``.
        epoch: ``capie_epoch``; the stored opening epoch by default.
    """
    vm.temp = {
        "capie_cap": Decimal(cap),
        "capie_ver": Decimal(10400),
        "capie_flag": Decimal(flag),
        "capie_epoch": vm.nations[vm.root].vars.get("rn_fp_epoch", Decimal(0))
        if epoch is None
        else epoch,
        "capie_nf": Decimal(0),
    }


def open_own(vm: FlagVM) -> None:
    """Open the own picker as the politics tab does.

    Args:
        vm: VM.
    """
    vm.temp = {}
    vm.run("rn_fp_open_own")


def open_sub(vm: FlagVM, tag: str) -> None:
    """Open the subject picker from the diplomacy view of ``tag``.

    Args:
        vm: VM.
        tag: Selected country.
    """
    vm.temp = {}
    vm.scoped(tag, lambda: vm.run("rn_fp_open_sub"))


def pick(vm: FlagVM, index: int) -> None:
    """Click a grid cell.

    Args:
        vm: VM.
        index: Catalog index of the cell.
    """
    vm.temp = {"rn_fp_pick": Decimal(index)}
    vm.run("rn_fp_pick_cell")


def layer(vm: FlagVM, tag: str) -> str | None:
    """Return the stem of a country's flag layer, or None.

    Args:
        vm: VM.
        tag: Country.

    Returns:
        Stem.
    """
    n = vm.nations[tag]
    if "capie_cf_ver" not in n.vars:
        return None
    return decode(n.arrays.get("capie_cf_s", []), n.vars["capie_cf_len"])


def root_err(vm: FlagVM) -> int:
    """Return the status error stored on ROOT.

    Args:
        vm: VM.

    Returns:
        ``rn_cv1_st_err`` or 0.
    """
    return int(vm.nations[vm.root].vars.get("rn_cv1_st_err", 0))


# ----------------------------------------------------------------------------- catalog cases


def run_catalog(inp: Inputs) -> int:
    """Run the generated lookups for every index, cosmetic tag and pool.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    vm = inp.vm()
    cases = 0
    for n, stem in enumerate(cat.stems, start=1):
        target = vm.nations["ITA"]
        target.vars.clear()
        target.arrays.clear()
        vm.temp = {"rn_fp_w": Decimal(n)}
        vm.scoped("ITA", lambda: vm.run("rn_fp_write_stem"))
        assert decode(target.arrays["capie_cf_s"], target.vars["capie_cf_len"]) == stem, (n, stem)
        assert target.arrays["capie_cf_s"] == [Decimal(v) for v in pack(stem)]
        cases += 1
    for bad in (0, len(cat.stems) + 1):
        vm.nations["ITA"].vars.clear()
        vm.temp = {"rn_fp_w": Decimal(bad)}
        vm.scoped("ITA", lambda: vm.run("rn_fp_write_stem"))
        assert "capie_cf_len" not in vm.nations["ITA"].vars, ("no stem outside the catalog", bad)
        cases += 1
    other = cat.cosmetics[0]
    for cosmetic in cat.cosmetics:
        n = vm.nations["ITA"]
        n.vars.clear()
        n.arrays.clear()
        n.cosmetic = cosmetic
        vm.temp = {}
        vm.scoped("ITA", lambda: vm.run("rn_fp_cos_write"))
        assert decode(n.arrays["capie_cf_cos"], n.vars["capie_cf_cos_len"]) == cosmetic
        vm.scoped("ITA", lambda: vm.run("rn_fp_cos_match"))
        assert (vm.temp["rn_fp_cos_known"], vm.temp["rn_fp_cos_same"]) == (1, 1), cosmetic
        n.cosmetic = other if cosmetic != other else cat.cosmetics[1]
        vm.scoped("ITA", lambda: vm.run("rn_fp_cos_match"))
        assert (vm.temp["rn_fp_cos_known"], vm.temp["rn_fp_cos_same"]) == (1, 0), cosmetic
        cases += 1
    n = vm.nations["ITA"]
    n.cosmetic = None
    vm.scoped("ITA", lambda: vm.run("rn_fp_cos_write"))
    assert "capie_cf_cos_len" not in n.vars, "no known cosmetic tag: no snapshot"
    vm.scoped("ITA", lambda: vm.run("rn_fp_cos_match"))
    assert vm.temp["rn_fp_cos_known"] == 0
    dynamic = vm.nation("D01")
    for g, tag in enumerate([*cat.tags, ""], start=1):
        vm.temp = {"rn_fp_g": Decimal(g)}
        vm.nations[vm.root].arrays["rn_fp_list"] = []
        vm.run("rn_fp_fill_group")
        assert vm.nations[vm.root].arrays["rn_fp_list"] == [
            Decimal(i) for i in pool_of(cat, tag)
        ], tag
        if tag:
            dynamic.original = tag
            vm.scoped("D01", lambda: vm.run("rn_fp_group_of"))
            assert vm.temp["rn_fp_g"] == g, ("dynamic country pool by original tag", tag)
        cases += 1
    cases += _resolve_cases(vm, cat)
    cases += _letter_cases(vm, cat)
    return cases


def _resolve_cases(vm: FlagVM, cat: Catalog) -> int:
    """Compare the generated game-flag resolver with the reference chain.

    Args:
        vm: VM.
        cat: Catalog.

    Returns:
        Number of cases.
    """
    cases = 0
    probe = vm.nation("D02")
    samples = [(t, None) for t in cat.tags] + [(c[:3], c) for c in cat.cosmetics[::7]]
    for original, cosmetic in samples:
        for government in IDEOLOGIES:
            probe.original, probe.cosmetic, probe.government = original, cosmetic, government
            vm.temp = {}
            vm.scoped("D02", lambda: vm.run("rn_fp_resolve_game"))
            want = game_flag(cat, original, government, cosmetic)
            assert vm.temp["rn_fp_res"] == want, (original, cosmetic, government)
            cases += 1
    return cases


def _letter_cases(vm: FlagVM, cat: Catalog) -> int:
    """Check that the letters list every pool country exactly once.

    Args:
        vm: VM.
        cat: Catalog.

    Returns:
        Number of cases.
    """
    seen: list[str] = []
    for tag in cat.tags:
        vm.nation(tag)
    root = vm.nations[vm.root]
    for n in range(1, len(LETTERS) + 1):
        root.vars["rn_fp_letter"] = Decimal(n)
        root.arrays["rn_fp_list"] = []
        vm.run("rn_fp_fill_letter")
        seen += [r.tag for r in root.arrays["rn_fp_list"]]
    assert sorted(seen) == sorted(cat.tags), "every pool country under one letter"
    return len(LETTERS)


# ----------------------------------------------------------------------------- picker cases


def run_picker(inp: Inputs) -> int:  # noqa: PLR0915 - one linear scenario per behaviour
    """Run the own and the subject picker through Apply, rejections, Restore and the daily check.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    cases = 0
    fra_pool = pool_of(cat, "FRA")
    ger_pool = pool_of(cat, "GER")

    # Opening: current flag preselected, own pool on page 1, Apply disabled until a change.
    vm = inp.vm()
    open_own(vm)
    root = vm.nations["FRA"]
    init = game_flag(cat, "FRA", "democratic", None)
    assert root.vars["rn_fp_init"] == init == root.vars["rn_fp_sel"]
    assert "rn_fp_open_own" in root.flags
    assert "rn_fp_view_target" in root.flags
    assert root.arrays["rn_fp_cells"] == [Decimal(i) for i in fra_pool[:PAGE]]
    assert root.vars["rn_fp_epoch"] == PICKER_EPOCH
    cases += 1

    # A cell that is not on the page is ignored; one on the page is selected.
    pick(vm, ger_pool[0])
    assert root.vars["rn_fp_sel"] == init
    choice = fra_pool[-1] if fra_pool[-1] != init else fra_pool[0]
    pick(vm, choice)
    assert root.vars["rn_fp_sel"] == choice
    cases += 1

    # Rejections leave no write on the target.
    rejections: list[tuple[dict[str, Any], int]] = [
        ({"cap": 1}, ERR["capie"]),
        ({"cap": 5}, ERR["old"]),
        ({"flag": 0}, ERR["layer"]),
        ({"epoch": Decimal(-1)}, ERR["stale"]),
        ({"epoch": Decimal(99)}, ERR["stale"]),
    ]
    for kwargs, err in rejections:
        before = copy.deepcopy(root.vars), copy.deepcopy(root.arrays)
        capie(vm, **kwargs)
        vm.run("rn_fp_apply")
        assert root_err(vm) == err, (kwargs, root_err(vm))
        assert layer(vm, "FRA") is None
        assert "rn_ip_cd_flag_until" not in root.vars
        assert "rn_fp_open_own" in root.flags, "the picker stays open after a refusal"
        assert before[0]["rn_fp_sel"] == root.vars["rn_fp_sel"]
        cases += 1

    # Apply: the carrier, the snapshot, the cooldown, the picker closes; rev is the last write.
    capie(vm)
    vm.writes = []
    vm.run("rn_fp_apply")
    assert root_err(vm) == 0
    assert layer(vm, "FRA") == cat.stems[choice - 1]
    assert root.vars["rn_cf_idx"] == choice
    carrier = [
        w for t, w in vm.writes if t == "FRA" and w.startswith(("capie_cf", "array:capie_cf"))
    ]
    assert carrier[-1] == "capie_cf_rev", carrier
    assert root.vars["rn_ip_cd_flag_until"] > Decimal(VM_TODAY)
    assert "rn_fp_open_own" not in root.flags
    assert "capie_cf_cos_len" not in root.vars, "no cosmetic tag: no snapshot"
    cases += 1

    # Cooldown: Apply and Restore refused; the next opening shows the chosen flag as current.
    open_own(vm)
    assert root.vars["rn_fp_init"] == choice
    pick(vm, fra_pool[0])
    capie(vm)
    vm.run("rn_fp_apply")
    assert root_err(vm) == ERR["cooldown"]
    assert layer(vm, "FRA") == cat.stems[choice - 1]
    vm.temp = {}
    vm.run("rn_fp_reset")
    assert root_err(vm) == ERR["cooldown"]
    cases += 2

    # Restore after the cooldown: layer gone, cooldown restarted, nothing else changed.
    root.vars["rn_ip_cd_flag_until"] = Decimal(VM_TODAY)
    vm.temp = {}
    vm.run("rn_fp_reset")
    assert layer(vm, "FRA") is None
    assert "rn_cf_idx" not in root.vars
    assert root.vars["rn_ip_cd_flag_until"] > Decimal(VM_TODAY)
    assert root.vars["capie_cf_rev"] == 1
    cases += 1

    cases += _rule_cases(inp)
    cases += _subject_cases(inp)
    cases += _navigation_cases(inp)
    cases += _daily_cases(inp)
    return cases


def _apply(vm: FlagVM, index: int) -> int:
    """Select ``index`` (bypassing the page check) and Apply; return the error code.

    Args:
        vm: VM.
        index: Catalog index.

    Returns:
        ``rn_cv1_st_err``.
    """
    vm.nations[vm.root].vars["rn_fp_sel"] = Decimal(index)
    capie(vm)
    vm.run("rn_fp_apply")
    return root_err(vm)


def _rule_cases(inp: Inputs) -> int:
    """Check the pool rule at Apply, including a rule change while the picker is open.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    cases = 0
    fra, ger = pool_of(cat, "FRA"), pool_of(cat, "GER")
    for rule, index, err in (
        ("RN_FLAG_POOL_ALL", ger[0], 0),
        ("RN_FLAG_POOL_OWN", ger[0], ERR["pool"]),
        ("RN_FLAG_POOL_OWN", fra[0], 0),
        ("RN_FLAG_POOL_OWN_OVERLORD", ger[0], ERR["pool"]),
        ("RN_FLAG_POOL_OWN", len(cat.stems) + 1, ERR["pool"]),
    ):
        vm = inp.vm()
        open_own(vm)
        vm.rules["rn_flag_pool"] = rule
        assert _apply(vm, index) == err, (rule, index)
        assert (layer(vm, "FRA") is None) == (err != 0)
        cases += 1
    # Overlord's flag: offered first, accepted under OWN_OVERLORD and ALL, refused under OWN.
    pol_pool = pool_of(cat, "POL")
    for rule, err in (
        ("RN_FLAG_POOL_OWN_OVERLORD", 0),
        ("RN_FLAG_POOL_ALL", 0),
        ("RN_FLAG_POOL_OWN", ERR["pool"]),
    ):
        vm = inp.vm()
        vm.rules["rn_flag_pool"] = rule
        open_sub(vm, "POL")
        root = vm.nations["FRA"]
        ovl = game_flag(cat, "FRA", "democratic", None)
        offered = root.vars["rn_fp_ovl"]
        assert offered == (0 if rule == "RN_FLAG_POOL_OWN" else ovl), rule
        if offered:
            assert root.arrays["rn_fp_cells"][0] == ovl
            assert root.arrays["rn_fp_cells"][1:] == [Decimal(i) for i in pol_pool[: PAGE - 1]]
        assert _apply(vm, ovl) == err, rule
        if not err:
            # A snapshot: the overlord changes ideology, the subject keeps the file.
            vm.nations["FRA"].government = "fascism"
            assert layer(vm, "POL") == cat.stems[ovl - 1]
            vm.nations["POL"].overlord = None
            assert layer(vm, "POL") == cat.stems[ovl - 1], "kept after independence"
        cases += 1
    return cases


def _subject_cases(inp: Inputs) -> int:
    """Check the subject picker's rights and pinning.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    cases = 0
    vm = inp.vm()
    open_sub(vm, "ITA")
    assert "rn_fp_open_sub" not in vm.nations["FRA"].flags, "a stranger cannot be opened"
    open_sub(vm, "POL")
    root = vm.nations["FRA"]
    assert "rn_fp_open_sub" in root.flags
    assert root.vars["rn_fp_target"] == Ref("POL")
    cases += 1
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_OWN"
    assert _apply(vm, pool_of(cat, "POL")[0]) == ERR["rights"]
    assert layer(vm, "POL") is None
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_SUBJECTS"
    vm.nations["POL"].overlord = None
    assert _apply(vm, pool_of(cat, "POL")[0]) == ERR["rights"], "freed while open"
    cases += 2
    vm = inp.vm()
    vm.rules["rn_edit_rights"] = "RN_RIGHTS_HOST"
    open_sub(vm, "ITA")
    assert "rn_fp_open_sub" in vm.nations["FRA"].flags, (
        "the single-player host may open any country"
    )
    assert _apply(vm, pool_of(cat, "ITA")[0]) == 0
    assert layer(vm, "ITA") == cat.stems[pool_of(cat, "ITA")[0] - 1]
    assert "rn_ip_cd_flag_until" in vm.nations["ITA"].vars
    assert "rn_ip_cd_flag_until" not in vm.nations["FRA"].vars, "cooldown on the target"
    cases += 1
    return cases


def _navigation_cases(inp: Inputs) -> int:
    """Check the country list, letters, the "Other" pool and paging.

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    vm = inp.vm()
    for tag in cat.tags:
        vm.nation(tag)
    open_own(vm)
    root = vm.nations["FRA"]
    vm.temp = {}
    vm.run("rn_fp_show_list")
    assert root.vars["rn_fp_view"] == LIST_VIEW
    assert not root.arrays.get("rn_fp_cells", [])
    first = list(root.arrays["rn_fp_rows"])
    assert 0 < len(first) <= PAGE
    assert all(isinstance(r, Ref) for r in first)
    other_country = first[0].tag
    vm.temp = {}
    vm.scoped(other_country, lambda: vm.run("rn_fp_pick_country"))
    assert root.vars["rn_fp_view"] == 1
    assert root.vars["rn_fp_src"] == Ref(other_country)
    assert root.arrays["rn_fp_cells"] == [Decimal(i) for i in pool_of(cat, other_country)[:PAGE]]
    vm.temp = {"rn_fp_lt": Decimal(OTHER_LETTER)}
    vm.run("rn_fp_pick_letter")
    other = pool_of(cat, "")
    assert root.arrays["rn_fp_cells"] == [Decimal(i) for i in other[:PAGE]]
    pages = (len(other) + PAGE - 1) // PAGE
    assert root.vars["rn_fp_pages"] == pages
    for _ in range(pages + 2):
        vm.temp = {"rn_fp_step": Decimal(1)}
        vm.run("rn_fp_page_step")
    assert root.vars["rn_fp_page"] == pages - 1, "paging stops at the last page"
    assert root.arrays["rn_fp_cells"] == [Decimal(i) for i in other[(pages - 1) * PAGE :]]
    vm.temp = {}
    vm.run("rn_fp_show_target")
    assert "rn_fp_view_target" in root.flags
    assert root.vars["rn_fp_page"] == 0
    # Under the own-pool rule the list does not open and a forged row click does nothing.
    vm.rules["rn_flag_pool"] = "RN_FLAG_POOL_OWN"
    vm.run("rn_fp_show_list")
    assert root.vars["rn_fp_view"] == 1
    vm.scoped(other_country, lambda: vm.run("rn_fp_pick_country"))
    assert root.vars["rn_fp_src"] == Ref("FRA")
    return 4


def _daily_cases(inp: Inputs) -> int:
    """Check the daily cosmetic tag check (no cooldown; this mod's and other layers).

    Args:
        inp: Inputs.

    Returns:
        Number of cases.
    """
    cat = inp.cat
    known, known2 = cat.cosmetics[0], cat.cosmetics[1]
    cases = 0
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
    index = pool_of(cat, "FRA")[0]
    for at_apply, now, ours, reset in table:
        vm = inp.vm()
        target = vm.nations["FRA"]
        target.cosmetic = at_apply
        vm.temp = {"rn_cf_in": Decimal(index)}
        vm.scoped("FRA", lambda vm=vm: vm.run("rn_country_flag_carrier_set"))
        if not ours:
            target.vars.pop("rn_cf_idx")
        target.cosmetic = now
        vm.temp = {}
        vm.scoped("FRA", lambda vm=vm: vm.run("rn_fp_daily_check"))
        assert (layer(vm, "FRA") is None) == reset, (at_apply, now, ours)
        assert "rn_ip_cd_flag_until" not in target.vars, "the daily reset starts no cooldown"
        cases += 1
    return cases


# ----------------------------------------------------------------------------- mutations


def run_flag_mutations(inp: Inputs) -> int:
    """Remove one guard at a time; the picker cases must then fail.

    Args:
        inp: Inputs.

    Returns:
        Number of rejected mutations.
    """

    def without(effect: str, predicate: Any) -> dict[str, Any]:  # noqa: ANN401 - node predicate
        """Return the effects with the matching nodes of one effect removed (at any depth).

        Args:
            effect: Effect name.
            predicate: Node predicate.

        Returns:
            Mutated effect map.
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

        mutated = copy.deepcopy(inp.effects)
        mutated[effect] = prune(mutated[effect])
        assert removed, ("mutation matched nothing", effect)
        return mutated

    mutations = [
        without("rn_fp_apply", lambda n: n == ("rn_fp_rights", "=", "yes")),
        without("rn_fp_apply", lambda n: n[0] == "else_if"),
        without("rn_fp_apply", lambda n: "rn_fp_cooldown_active" in str(n) and n[0] == "if"),
        without("rn_fp_apply", lambda n: "rn_fp_sel_allowed" in str(n)),
        without("rn_country_flag_carrier_set", lambda n: n == ("rn_fp_cos_write", "=", "yes")),
        without("rn_fp_daily_check", lambda n: n[0] == "if"),
    ]
    rejected = 0
    for effects in mutations:
        mutant = Inputs.__new__(Inputs)
        mutant.cat, mutant.effects, mutant.triggers = inp.cat, effects, inp.triggers
        try:
            run_picker(mutant)
        except AssertionError:
            rejected += 1
    assert rejected == len(mutations), ("flag mutations not caught", rejected, len(mutations))
    return rejected


# ----------------------------------------------------------------------------- structure, geometry


def _windows() -> dict[str, list[Any]]:
    """Return the generated picker windows and list entries by name.

    Returns:
        Window name to body.
    """
    tree = parse((MOD / "interface" / "rn_flag_picker.gui").read_text(encoding="utf-8-sig"))
    return {
        get(v, "name"): v
        for k, _, v in walk(tree)
        if k == "containerWindowType" and any(n[0] == "name" for n in v)
    }


def _size(body: list[Any]) -> tuple[int, int]:  # noqa: PLR0911 - one return per element kind
    """Return the drawn size of a picker element.

    Args:
        body: Element.

    Returns:
        ``(width, height)``.

    Raises:
        AssertionError: The element has no known size.
    """
    sprite = next((v for k, _, v in body if k in {"spriteType", "quadTextureSprite"}), "")
    if sprite == "GFX_preset_button_save":
        side = round(30 * float(get(body, "scale")))
        return side, side
    if sprite in SPRITE_SIZE:
        w, h = SPRITE_SIZE[sprite]
        scale = float(get(body, "scale")) if any(k == "scale" for k, _, _ in body) else 1.0
        return round(w * scale), round(h * scale)
    if sprite in FRAME_SIZE:
        return FRAME_SIZE[sprite]
    if sprite.startswith("GFX_rnfm_"):
        return FLAG_SIZE["medium"]
    if sprite.startswith("GFX_rnf_"):
        return FLAG_SIZE["large"]
    if any(k == "maxWidth" for k, _, _ in body):
        return int(get(body, "maxWidth")), int(get(body, "maxHeight"))
    if any(k == "size" for k, _, _ in body):
        return xy(body, "size")
    msg = f"unknown size: {get(body, 'name')}"
    raise AssertionError(msg)


def _rects(window: list[Any]) -> dict[str, tuple[str, Rect]]:
    """Return every child of a window with its kind and rectangle (window coordinates).

    Args:
        window: Window body.

    Returns:
        Name to ``(kind, rect)``.
    """
    out: dict[str, tuple[str, Rect]] = {}
    for kind, _, body in window:
        if (
            isinstance(body, list)
            and any(k == "position" for k, _, _ in body)
            and kind != "background"
        ):
            x, y = xy(body)
            w, h = _size(body)
            out[str(get(body, "name"))] = (str(kind), (x, y, x + w, y + h))
    return out


def check_flag_geometry() -> None:
    """Check the picker and cell layouts and the name editor's tab row."""
    windows = _windows()
    for picker in flag_picker.PICKERS:
        win = windows[picker.key]
        w, h = xy(win, "size")
        x, y = xy(win)
        assert (w, h) == (flag_picker.WIDTH, flag_picker.HEIGHT)
        assert x + w <= PANEL_WIDTH, picker.key
        assert y + h <= ACTIONS_Y, picker.key
        rects = _rects(win)
        frame = (0, 0, w, h)
        controls = {n: r for n, (k, r) in rects.items() if k in {"buttonType", "gridBoxType"}}
        for name, (_, rect) in rects.items():
            assert inside(rect, frame), (picker.key, name, rect)
        names = sorted(controls)
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                both_grids = {a, b} == {"rn_fp_grid", "rn_fp_rows_grid"}
                assert both_grids or disjoint(controls[a], controls[b]), (picker.key, a, b)
        apply_ = controls[f"{picker.key}_apply"]
        assert apply_[0] == flag_picker.APPLY_X
        assert controls["rn_fp_cancel"][0] == flag_picker.CANCEL_X
        for grid in ("rn_fp_grid", "rn_fp_rows_grid"):
            assert controls[grid][2] < apply_[0], ("grid left of Apply", grid)
        assert inside(rects["rn_fp_preview"][1], rects["rn_fp_frame"][1])
        texts = [
            n
            for n, (k, _) in rects.items()
            if k == "instantTextboxType" and not n.startswith("capie_")
        ]
        status = rects["rn_fp_status"][1]
        letters = [r for n, (_, r) in rects.items() if n.startswith("rn_fp_letter_")]
        assert all(r[3] <= status[1] for r in letters), "letters above the status line"
        assert status[3] <= rects["rn_fp_reset"][1][1], "Restore under the status line"
        for name in texts:
            if name.startswith(("rn_fp_lt", "rn_fp_row")):
                continue
            rect = rects[name][1]
            for other, (kind, r) in rects.items():
                if kind == "buttonType" and not other.startswith("rn_fp_letter_"):
                    assert disjoint(rect, r), (picker.key, name, other)
        tabs = [r for n, (_, r) in rects.items() if "_tab_" in n]
        assert len(tabs) == len(picker.tabs)
        assert all(r[1] == 0 for r in tabs)
    cell = _rects(windows["rn_fp_cell"])
    assert inside(cell["rn_fp_cell_flag"][1], cell["rn_fp_cell_frame"][1])
    assert inside(cell["rn_fp_cell_frame"][1], (0, 0, *flag_picker.CELL))
    row = _rects(windows["rn_fp_row"])
    assert row["rn_fp_row_hit"][1] == (0, 0, *flag_picker.ROW)
    _check_name_editor_tabs()


def _check_name_editor_tabs() -> None:
    """Check the Name | Flag tab row of the politics country editor."""
    tree = parse(
        (SOURCE / "interface" / "rn_country_inline_ui.gui").read_text(encoding="utf-8-sig")
    )
    win = next(
        v
        for k, _, v in walk(tree)
        if k == "containerWindowType" and get(v, "name") == "rn_ip_country_window"
    )
    items = {
        get(b, "name"): b
        for k, _, b in win
        if isinstance(b, list) and any(n[0] == "name" for n in b)
    }
    tabs = [items["rn_ip_country_tab_name"], items["rn_ip_country_tab_flag"]]
    rects = []
    for tab in tabs:
        x, y = xy(tab)
        rects.append((x, y, x + 94, y + 31))
    for name in (
        "rn_ipc_name_frame",
        "rn_ipc_name_label",
        "rn_ip_country_apply",
        "rn_ip_country_cancel",
    ):
        x, y = xy(items[name])
        assert all(r[3] <= y for r in rects), ("tab row above", name)
    assert disjoint(rects[0], rects[1])
    w, h = xy(win, "size")
    assert xy(items["rn_ip_country_reset"])[1] + 34 <= h, "Restore name inside the taller editor"
    assert all(r[2] <= w for r in rects)


def check_flag_structure(models: dict[str, Any]) -> None:
    """Check grammar, carriers, Enter, referenced names and localisation of the pickers.

    Args:
        models: Source and generated scripted GUI models.
    """
    windows = _windows()
    generated = models_of(MOD / "common" / "scripted_guis", "rn_flag_picker.txt")
    rn_editors = {m for m in (*models, *generated) if m.startswith("capie_v1_ed__rn__")}
    assert len(rn_editors) <= MAX_EDITORS_PER_MOD, ("CAPIE registry limit", sorted(rn_editors))
    effects = {
        **declarations(SOURCE / "common" / "scripted_effects"),
        **declarations(MOD / "common" / "scripted_effects", "rn_flag_catalog.txt"),
    }
    triggers = {
        **declarations(SOURCE / "common" / "scripted_triggers"),
        **declarations(MOD / "common" / "scripted_triggers", "rn_feature_switches.txt"),
    }
    keys = _loc_keys()
    for picker in flag_picker.PICKERS:
        model = generated[picker.key]
        win = windows[picker.key]
        _check_grammar(picker, model, win)
        elements = {
            get(b, "name")
            for _, _, b in walk([*win, *windows["rn_fp_cell"], *windows["rn_fp_row"]])
            if isinstance(b, list) and any(n[0] == "name" for n in b)
        }
        _check_references(picker, model, elements, effects, triggers)
        for _, _, body in walk(win):
            if not isinstance(body, list):
                continue
            for k, _, v in body:
                if k in {"buttonText", "pdx_tooltip", "text"} and not str(v).startswith("["):
                    assert v in keys, (picker.key, k, v)


def _check_grammar(picker: flag_picker.Picker, model: list[Any], win: list[Any]) -> None:
    """Check one picker against the CAPIE grammar: no field, hidden epoch, Enter on Apply only.

    Args:
        picker: The editor.
        model: Its scripted GUI.
        win: Its window.
    """
    assert get(model, "window_name") == picker.key
    assert not any(k == "editBoxType" for k, _, _ in walk(win)), "no text field"
    epoch = get(get(model, "triggers"), f"capie_v1_ep__rn__{picker.editor}_visible")
    assert epoch == [("always", "=", "no")]
    buttons = {get(b, "name"): b for k, _, b in walk(win) if k == "buttonType"}
    with_shortcut = {n for n, b in buttons.items() if any(k == "shortcut" for k, _, _ in b)}
    assert with_shortcut == {f"{picker.key}_apply"}
    assert get(buttons[f"{picker.key}_apply"], "shortcut") == "RETURN"


def _check_references(
    picker: flag_picker.Picker,
    model: list[Any],
    elements: set[str],
    effects: dict[str, Any],
    triggers: dict[str, Any],
) -> None:
    """Check that every click and trigger names an element, and every call exists.

    Args:
        picker: The editor.
        model: Its scripted GUI.
        elements: Element names of its window and the two list entries.
        effects: Effect declarations.
        triggers: Scripted trigger declarations.
    """
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


def _loc_keys() -> set[str]:
    """Return the localisation keys every language defines (source and generated catalog).

    Returns:
        Keys present in every language.
    """
    per_lang = []
    for lang in LANGS:
        keys: set[str] = set()
        folder = MOD / "localisation" / lang
        for path in folder.glob("*.yml"):
            keys |= set(
                re.findall(r'^ (\S+?):\d* "', path.read_text(encoding="utf-8-sig"), re.MULTILINE)
            )
        per_lang.append(keys)
    common = per_lang[0]
    for keys in per_lang[1:]:
        common &= keys
    return common


def run_flag_cases() -> dict[str, int]:
    """Run every flag VM case.

    Returns:
        Case counts by group.
    """
    inp = Inputs()
    return {
        "flag_catalog_cases": run_catalog(inp),
        "flag_picker_cases": run_picker(inp),
        "flag_mutations_rejected": run_flag_mutations(inp),
    }
