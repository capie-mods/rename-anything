"""Run the generated pair Apply source in a limited offline model and record a review.

This checker executes the real Paradox script text written by ``generate.py``
(``rn_inline_pair_apply.txt`` and ``rn_inline_party_buffers.txt``) together with
the shared payload helpers and the main mod's generated effects. It does that
with the small interpreter (``VM``) from ``probes/rn_inline_pair_qa/tools/
check.py``, extended here by ``ApplyVM`` with the commands Apply needs:
country triggers (tag, AI, flags, government, typed array membership),
persistent variable and flag writes, and ``meta_effect`` substitution. No HOI4
process, game parser, native setter or capability export is involved. A
``meta_effect`` is only recorded as a setter request with its text filled in;
nothing is renamed.

What it checks, in order:

1. Inputs. Both new files exist, the shared single and pair payload helpers
   still have their reviewed hashes, the main mod defines exactly the 85
   ``RN_CH_*`` characters and keeps ``rn_country_rename_enabled`` as
   ``always = yes``, and the eight new effects and 64 new ``RN_PS``/``RN_PL``
   loc entries do not collide with existing names.
2. Purity. The guards and the pair validator may only touch temp variables.
3. Rejections, for both kinds. Wrong tag, AI player, missing own flag, any
   other rename panel open, bad or fractional epochs, a missing command epoch,
   an empty, foreign, non-country or doubled pin, a missing or wrong country
   capability, a wrong party group or government, and broken payload fields
   must each be refused with the expected error, field and bad slot. A
   refusal must leave every persistent variable, array and flag unchanged and
   emit no setter request.
   Some of these mutations are applied only after the first full validation
   ("late") to prove that the second guard runs before any write.
4. Success, for both kinds and two payload length combinations. Both guards
   and one pair validation run before the first write, exactly one setter
   request is emitted with the expected literal text, only the kind's two
   buffers change, the legacy ``rn_buf`` input stays untouched and the panel
   is closed with a bumped epoch.
5. Lifecycle. The uncalled Open and Cancel helpers pin the country, set and
   clear the flag and bump the epoch without touching buffers, and Open does
   nothing while another rename panel is open.
6. Party loc slots. Every slot of both party buffers renders each of the 84
   character codes correctly and renders nothing past the stored length.
7. Mutation test. With the late guard removed from the country Apply, the
   write barrier must fire before the first persistent write.

When everything passes, ``static-review.json`` in this folder is rewritten with
the case counts and the SHA-256 of every input and of the generator and
checker themselves, and one PASS line is printed. Any failure prints
``FAIL: <reason>`` to stderr and exits with code 1.

What this does not prove: it is not an HOI4 interpreter. Arithmetic, scopes and
command semantics follow the documented assumptions of the borrowed VM, and
the GUI, native transport, capability export and multiplayer are not
exercised. A fresh game process is still needed for any runtime claim.

Usage::

    python probes/rn_inline_pair_apply_source/check.py
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, override

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
"""This probe folder (``probes/rn_inline_pair_apply_source``)."""

REPO = HERE.parents[1]
"""Repository root."""

SHARED = REPO / "probes/rn_in_place_ui/common"
"""``common`` folder of the in-place UI fixture holding the shared and generated sources."""

sys.path.insert(0, str(REPO / "probes/rn_inline_pair_qa/tools"))
# The import has to follow the sys.path change above: it loads the pair QA checker
# (probes/rn_inline_pair_qa/tools/check.py), not this file.
from check import BUFFERS, VM, parse, payload, pure_audit  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Callable

APPLY = SHARED / "scripted_effects/rn_inline_pair_apply.txt"
"""Generated guard, lifecycle and Apply effects under test."""

PARTY_LOC = SHARED / "scripted_localisation/rn_inline_party_buffers.txt"
"""Generated party buffer scripted localisation under test."""

PAIR_SHA256 = "e278dfac3a4e3ac5ccca7d7cf74da9d87f0de728d30bca875d543f24956f6fc7"
"""Reviewed SHA-256 of the shared pair payload validator."""

SINGLE_SHA256 = "cd171d6203bd66dc7905c7c3d0e1a2750c4b8eabab45f0540d75d3af2ce10800"
"""Reviewed SHA-256 of the shared single payload validator."""

MAIN_CHAR_KEYS = 85
"""Number of ``RN_CH_*`` keys (codes 0 to 84) the main mod must define."""

NEW_EFFECTS = 8
"""Number of effects the generated Apply file must declare."""

PARTY_SLOTS = 32
"""Slots per party name buffer."""

GUARD_RUNS_BEFORE_WRITE = 2
"""Times the full guard must have run before the first persistent write."""

OTHER_PANEL_FLAGS = (
    "rn_open",
    "rn_input",
    "rn_ip_leader_open",
    "rn_ip_country_open",
    "rn_ip_party_neutrality_open",
)
"""Every rename panel flag; Open must refuse while any of them is set."""

Node = tuple[str, str, Any]
"""Parsed script node as (key, operator, value); the value is a string or a node list."""


class Country:
    """Minimal stand-in for a typed country scope, compared by tag."""

    def __init__(self, tag: str) -> None:
        """Create a country scope for ``tag``."""
        self.tag = tag

    @override
    def __eq__(self, other: object) -> bool:
        """Return True when ``other`` is a Country with the same tag."""
        return isinstance(other, Country) and self.tag == other.tag

    @override
    def __hash__(self) -> int:
        """Hash by tag, consistent with equality."""
        return hash(self.tag)

    @override
    def __repr__(self) -> str:
        """Return ``Country(<tag>)``."""
        return "Country(" + self.tag + ")"


class ApplyVM(VM):
    """Source VM extended with the country context and write commands that Apply uses.

    Every persistent write passes through :meth:`assert_write_barrier`, which
    (while ``enforce`` is set) requires one completed pair validation and two
    guard runs with no error before it.
    """

    def __init__(
        self,
        effects: dict[str, list[Node]],
        locs: dict[str, list[Node]],
        chars: dict[str, str],
        kind: str,
    ) -> None:
        """Build a POL human-player state with valid payloads and an open panel.

        Args:
            effects: Effect name to parsed body.
            locs: Scripted loc name to its ``text`` entries.
            chars: ``RN_CH_<n>`` key to character.
            kind: ``country`` or ``party``.
        """
        tag = "POL"
        temp = {
            **payload("rn_native_", 1, 84),
            **payload("rn_nativeb_", 32, 1),
            "rn_ip_cmd_epoch": Decimal(7),
            "rn_native_cap": Decimal(1),
        }
        persistent = {"rn_ip_epoch": Decimal(7), "rn_ip_party_group": Decimal(4)}
        arrays: dict[str, list[object]] = {
            name: [Decimal(11 + i), Decimal(84 - i)] for i, (name, _length) in enumerate(BUFFERS)
        }
        for i, (_, length) in enumerate(BUFFERS):
            persistent[length] = Decimal(i + 2)
        arrays["rn_ip_country_target"] = [Country(tag)]
        arrays["rn_ip_party_target"] = [Country(tag)]
        super().__init__(effects, temp, persistent, arrays)
        self.tag, self.ai, self.government = tag, False, "neutrality"
        self.kind = kind
        self.flags = {"rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"}
        self.locs: dict[str, list[Node]] = locs
        self.chars: dict[str, str] = chars
        self.requests: list[list[Node]] = []
        self.guard_count, self.pair_count, self.pair_complete = 0, 0, False
        self.enforce: bool = True
        self.late_mutation: Callable[[ApplyVM], None] | None = None
        self.trace: list[str] = []

    @override
    def value(self, token: str) -> Any:
        """Resolve THIS/ROOT to the player country, otherwise defer to the base VM."""
        if token in {"THIS", "ROOT"}:
            return Country(self.tag)
        return super().value(token)

    @override
    def condition(self, nodes: list[Node]) -> bool:
        """Evaluate trigger nodes, adding the country triggers Apply relies on."""
        for key, _, value in nodes:
            if key == "tag":
                answer = self.tag == value
            elif key == "is_ai":
                answer = self.ai == (value == "yes")
            elif key == "has_country_flag":
                answer = value in self.flags
            elif key == "has_government":
                answer = self.government == value
            elif key == "is_in_array":
                params = {k: v for k, _, v in value}
                answer = self.value(params["value"]) in self.arrays.get(params["array"], [])
            elif key == "rn_country_rename_enabled":
                answer = value == "yes"  # Actual main-mod trigger is always=yes.
            else:
                answer = super().condition([(key, "=", value)])
            if not answer:
                return False
        return True

    @override
    def run(self, name: str) -> None:
        """Run an effect and count pair validations and guard runs.

        After the first successful pair validation a pending ``late_mutation``
        callback is applied once, before the late guard runs.
        """
        super().run(name)
        if name == "rn_inline_pair_validate":
            self.pair_count += 1
            self.pair_complete = self.value("temp_var:rn_pair_err") == 0
            if self.pair_complete and self.late_mutation:
                callback, self.late_mutation = self.late_mutation, None
                callback(self)
        if name == "rn_inline_pair_guard_" + self.kind:
            self.guard_count += 1

    def assert_write_barrier(self, key: str) -> None:
        """Fail if a persistent write happens before both validations and both guards."""
        if self.enforce:
            assert self.pair_count == 1, ("write before both payloads valid", key)
            assert self.pair_complete, ("write before both payloads valid", key)
            assert self.guard_count == GUARD_RUNS_BEFORE_WRITE, ("write before late guard", key)
            assert self.value("temp_var:rn_pair_err") == 0, ("write before late guard", key)
        self.trace.append(key)

    def localized(self, name: str) -> str:
        """Resolve a scripted localisation entry to its character text.

        Args:
            name: Scripted loc name such as ``RN_PS_3``.

        Returns:
            The text of the first entry whose trigger holds.
        """
        for _, _, text in self.locs[name]:
            if not isinstance(text, list):
                continue
            trigger = next((v for k, _, v in text if k == "trigger"), [])
            if not trigger or self.condition(trigger):
                key = next(v for k, _, v in text if k == "localization_key")
                return self.chars[key]
        raise AssertionError(("unresolved scripted loc", name))

    @override
    def execute(self, nodes: list[Node]) -> None:
        """Execute effect nodes, handling persistent writes and ``meta_effect`` here.

        Base VM owns branch control; only the missing primitive operations are added.
        """
        if len(nodes) != 1 or nodes[0][0] in {"if", "else_if", "else"}:
            self._execute_block(nodes)
            return
        key, _, value = nodes[0]
        if key in {"set_variable", "add_to_variable"}:
            self.assert_write_barrier(key)
            name, _, source = value[0]
            prior = (
                self.persistent.get(name, Decimal(0)) if key == "add_to_variable" else Decimal(0)
            )
            self.persistent[name] = prior + self.value(source)
        elif key == "clear_variable":
            self.assert_write_barrier(key)
            self.persistent.pop(value, None)
        elif key in {"set_country_flag", "clr_country_flag"}:
            self.assert_write_barrier(key)
            (self.flags.add if key == "set_country_flag" else self.flags.discard)(value)
        elif key == "meta_effect":
            self.assert_write_barrier(key)
            self.requests.append(self._meta_effect_request(value))
        else:
            if key in {"clear_array", "add_to_array"}:
                self.assert_write_barrier(key)
            super().execute(nodes)

    def _execute_block(self, nodes: list[Node]) -> None:
        """Execute a node list one statement at a time with if/else_if/else chaining."""
        branch_taken = None
        for key, op, value in nodes:
            if key in {"if", "else_if", "else"}:
                if key == "if":
                    branch_taken = False
                limit = next((v for k, _, v in value if k == "limit"), [])
                if branch_taken is not True and (key == "else" or self.condition(limit)):
                    self.execute([n for n in value if n[0] != "limit"])
                    branch_taken = True
            else:
                branch_taken = None
                self.execute([(key, op, value)])

    def _meta_effect_request(self, value: list[Node]) -> list[Node]:
        """Return the ``text`` block of a ``meta_effect`` with its parameters substituted."""
        params = {k: v for k, _, v in value}
        substitutions = {
            k: re.sub(r"\[ROOT\.([^]]+)\]", lambda m: self.localized(m[1]), v)
            for k, v in params.items()
            if k != "text"
        }
        text = copy.deepcopy(params["text"])

        def substitute(items: list[Node]) -> list[Node]:
            """Replace ``[NAME]`` placeholders in every string value, recursively."""
            out = []
            for k, op, v in items:
                if isinstance(v, list):
                    new_value: Any = substitute(v)
                else:
                    new_value = v
                    for token, literal in substitutions.items():
                        new_value = new_value.replace("[" + token + "]", literal)
                out.append((k, op, new_value))
            return out

        return substitute(text)

    def state(self) -> tuple[Any, ...]:
        """Return a deep copy of the persistent variables, arrays and flags."""
        return copy.deepcopy((self.persistent, self.arrays, self.flags))


def parse_file(path: Path, encoding: str = "utf-8-sig") -> list[Node]:
    """Parse one Paradox script file with the borrowed parser.

    Args:
        path: File to read.
        encoding: Text encoding; ``utf-8-sig`` also accepts a BOM.

    Returns:
        The top-level nodes.
    """
    return parse(path.read_text(encoding=encoding))


def loc_name(body: list[Node]) -> str:
    """Return the ``name`` of a ``defined_text`` body."""
    return cast("str", next(v for k, _, v in body if k == "name"))


def load() -> tuple[dict[str, list[Node]], dict[str, list[Node]], dict[str, str]]:
    """Load and cross-check every input file.

    Returns:
        Effect bodies by name, scripted loc ``text`` entries by name, and the
        ``RN_CH_*`` character table.
    """
    assert APPLY.exists(), "missing new Apply/party-buffer implementation"
    assert PARTY_LOC.exists(), "missing new Apply/party-buffer implementation"
    pair = SHARED / "scripted_effects/rn_inline_pair_payload.txt"
    single = SHARED / "scripted_effects/rn_inline_payload.txt"
    assert hashlib.sha256(pair.read_bytes()).hexdigest() == PAIR_SHA256
    assert hashlib.sha256(single.read_bytes()).hexdigest() == SINGLE_SHA256
    main_effects = REPO / "mod/common/scripted_effects/rename_anything_generated_effects.txt"
    main_loc = REPO / "mod/common/scripted_localisation/rename_anything_scripted_loc.txt"
    paths = [single, pair, APPLY, main_effects]
    effects = {name: body for path in paths for name, _, body in parse_file(path)}
    locs = {}
    for path in (PARTY_LOC, main_loc):
        for _, _, body in parse_file(path):
            locs[loc_name(body)] = [n for n in body if n[0] == "text"]
    source = (REPO / "mod/localisation/english/rename_anything_chars_l_english.yml").read_text(
        encoding="utf-8-sig"
    )
    chars = {
        name: json.loads(literal)
        for name, literal in re.findall(r'^ (RN_CH_\d+):\s*(".*")\s*$', source, re.MULTILINE)
    }
    assert len(chars) == MAIN_CHAR_KEYS
    trigger_source = REPO / "mod/common/scripted_triggers/rename_anything_triggers.txt"
    triggers = {k: v for k, _, v in parse_file(trigger_source)}
    assert triggers["rn_country_rename_enabled"] == [("always", "=", "yes")], (
        "country setter enable assumption changed"
    )
    new_effects = parse_file(APPLY, "utf-8")
    assert len(new_effects) == NEW_EFFECTS
    assert len({name for name, _, _ in new_effects}) == NEW_EFFECTS
    pair_names = {name for path in (single, pair) for name, _, _ in parse_file(path)}
    main_names = {name for name, _, _ in parse_file(paths[-1])}
    assert not {name for name, _, _ in new_effects} & (pair_names | main_names), (
        "effect name collision"
    )
    new_loc_names = [loc_name(body) for _, _, body in parse_file(PARTY_LOC, "utf-8")]
    assert set(new_loc_names) == {
        f"RN_{prefix}_{i}" for prefix in ("PS", "PL") for i in range(PARTY_SLOTS)
    }
    assert len(new_loc_names) == 2 * PARTY_SLOTS
    main_loc_names = {loc_name(body) for _, _, body in parse_file(main_loc)}
    assert not set(new_loc_names) & main_loc_names, "scripted localisation name collision"
    return effects, locs, chars


class KindChecks:
    """Rejection, success and lifecycle checks for one Apply kind."""

    def __init__(
        self,
        effects: dict[str, list[Node]],
        locs: dict[str, list[Node]],
        chars: dict[str, str],
        kind: str,
    ) -> None:
        """Store the loaded sources for ``kind`` (``country`` or ``party``)."""
        self.effects, self.locs, self.chars, self.kind = effects, locs, chars, kind
        self.own_flag = "rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"
        self.target = "rn_ip_country_target" if kind == "country" else "rn_ip_party_target"
        self.rejection_cases = 0
        self.success_cases = 0
        self.lifecycle_cases = 0

    def fresh(self) -> ApplyVM:
        """Return a new VM in the valid starting state."""
        return ApplyVM(self.effects, self.locs, self.chars, self.kind)

    def reject(
        self,
        mutate: Callable[[ApplyVM], object],
        want: int,
        field: int = 0,
        bad: int = -1,
        *,
        late: bool = False,
    ) -> None:
        """Apply one mutation and require a clean refusal with the expected error.

        Args:
            mutate: Change applied to the VM (before Apply, or after the first
                full validation when ``late`` is set).
            want: Expected ``rn_pair_err``.
            field: Expected ``rn_pair_field``.
            bad: Expected ``rn_pair_bad``.
            late: Apply the mutation after the first successful validation.
        """
        kind = self.kind
        vm = self.fresh()
        expected = []
        if late:

            def callback(current: ApplyVM) -> None:
                """Mutate the VM mid-Apply and remember the resulting state."""
                mutate(current)
                expected.append(current.state())

            vm.late_mutation = callback
        else:
            mutate(vm)
            expected.append(vm.state())
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.state() == expected[0], (kind, want, "rejection mutated persistent state")
        assert not vm.requests, (kind, want, "rejected setter/write")
        assert not vm.trace, (kind, want, "rejected setter/write")
        actual = tuple(
            int(vm.value("temp_var:" + n)) for n in ("rn_pair_err", "rn_pair_field", "rn_pair_bad")
        )
        assert actual == (want, field, bad), (kind, actual, (want, field, bad))
        self.rejection_cases += 1

    def rejections(self) -> None:
        """Run every context, epoch, pin, capability and payload rejection case."""
        kind, own_flag, target, reject = self.kind, self.own_flag, self.target, self.reject
        reject(lambda vm: setattr(vm, "tag", "GER"), 7)
        reject(lambda vm: setattr(vm, "ai", True), 7)
        reject(lambda vm: vm.flags.discard(own_flag), 7)
        other_flags = [
            "rn_open",
            "rn_input",
            "rn_ip_leader_open",
            "rn_ip_party_neutrality_open" if kind == "country" else "rn_ip_country_open",
        ]
        for flag in other_flags:
            reject(lambda vm, f=flag: vm.flags.add(f), 7)
        reject(lambda vm: vm.persistent.update(rn_ip_epoch=Decimal(0)), 8)
        reject(lambda vm: vm.temp.update(rn_ip_cmd_epoch=Decimal(8)), 8)
        reject(lambda vm: vm.temp.pop("rn_ip_cmd_epoch"), 8)
        reject(
            lambda vm: (
                vm.persistent.update(rn_ip_epoch=Decimal("7.5")),
                vm.temp.update(rn_ip_cmd_epoch=Decimal("7.5")),
            ),
            8,
        )
        for wrong in ([], [Country("GER")], [Decimal(1)], [Country("POL"), Country("POL")]):
            reject(lambda vm, values=wrong: vm.arrays.update({target: values}), 9)
        if kind == "country":
            for capability in (Decimal(0), Decimal(2), Decimal("1.00001")):
                reject(lambda vm, c=capability: vm.temp.update(rn_native_cap=c), 10)
            reject(lambda vm: vm.temp.pop("rn_native_cap"), 10)
        else:
            reject(lambda vm: vm.persistent.update(rn_ip_party_group=Decimal(3)), 9)
            reject(lambda vm: setattr(vm, "government", "fascism"), 9)
        for prefix, field in (("rn_native_", 1), ("rn_nativeb_", 2)):
            for suffix, value, err, bad in [
                ("ok", "0", 1, -1),
                ("len", "1.00001", 4, -1),
                ("0", "1.5", 5, 0),
                ("0", "85", 5, 0),
            ]:
                reject(
                    lambda vm, p=prefix, s=suffix, v=value: vm.temp.update({p + s: Decimal(v)}),
                    err,
                    field,
                    bad,
                )

            def bad_padding(vm: ApplyVM, p: str = prefix) -> None:
                """Declare length 1 but leave a non-zero fraction in slot 31."""
                vm.temp[p + "len"] = Decimal(1)
                for i in range(1, 32):
                    vm.temp[p + str(i)] = Decimal(0)
                vm.temp[p + "31"] = Decimal("0.00001")

            reject(bad_padding, 6, field, 31)
        reject(lambda vm: vm.flags.add("rn_input"), 7, late=True)
        reject(lambda vm: vm.persistent.update(rn_ip_epoch=Decimal(8)), 8, late=True)
        reject(lambda vm: vm.arrays.update({target: [Country("GER")]}), 9, late=True)
        if kind == "country":
            reject(lambda vm: vm.temp.update(rn_native_cap=Decimal(0)), 10, late=True)
        else:
            reject(lambda vm: setattr(vm, "government", "democratic"), 9, late=True)

    def successes(self) -> None:
        """Apply valid payloads and check the single setter request and every buffer."""
        kind, chars = self.kind, self.chars
        for alen, blen in [(1, 32), (32, 1)]:
            vm = self.fresh()
            vm.temp.update(payload("rn_native_", alen, 84))
            vm.temp.update(payload("rn_nativeb_", blen, 1))
            before = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            assert vm.guard_count == GUARD_RUNS_BEFORE_WRITE
            assert vm.pair_count == 1
            assert len(vm.requests) == 1
            assert vm.value("temp_var:rn_pair_err") == 0
            assert vm.value("temp_var:rn_pair_field") == 0
            assert vm.arrays["rn_buf"] == before[1]["rn_buf"]
            assert vm.persistent["rn_len"] == before[0]["rn_len"]
            destinations = (
                ("rn_cname", "rn_cadj") if kind == "country" else ("rn_pshort", "rn_plong")
            )
            lengths = (
                ("rn_cname_len", "rn_cadj_len")
                if kind == "country"
                else ("rn_pshort_len", "rn_plong_len")
            )
            assert vm.arrays[destinations[0]] == [Decimal(84 - i) for i in range(alen)]
            assert vm.arrays[destinations[1]] == [Decimal(1 + i) for i in range(blen)]
            assert vm.persistent[lengths[0]] == alen
            assert vm.persistent[lengths[1]] == blen
            for array, length in BUFFERS:
                if array not in destinations:
                    assert vm.arrays[array] == before[1][array]
                    assert vm.persistent[length] == before[0][length]
            assert self.own_flag not in vm.flags
            assert vm.arrays[self.target] == []
            assert vm.persistent["rn_ip_epoch"] == 8  # noqa: PLR2004
            first_name = "".join(chars[f"RN_CH_{84 - i}"] for i in range(alen))
            second_name = "".join(chars[f"RN_CH_{1 + i}"] for i in range(blen))
            if kind == "party":
                assert "rn_ip_party_group" not in vm.persistent
                params = {k: v for k, _, v in vm.requests[0][0][2]}
                assert params == {
                    "ideology": "neutrality",
                    "name": first_name,
                    "long_name": second_name,
                }
            else:
                assert vm.requests == [
                    [("set_cosmetic_tag", "=", "RN1|" + first_name + "|" + second_name + "|")]
                ]
            self.success_cases += 1

    def lifecycle(self) -> None:
        """Check the uncalled Open/Cancel helpers and Open's panel exclusion."""
        kind, own_flag, target = self.kind, self.own_flag, self.target
        # These entries are deliberately not called from Apply or any GUI.
        # Explicit Open/Cancel is a separate lifecycle contract, not a rejection.
        vm = self.fresh()
        vm.enforce = False
        vm.flags.clear()
        before_buffers = {name: list(vm.arrays[name]) for name, _ in BUFFERS}
        vm.run("rn_inline_pair_open_" + kind)
        assert vm.arrays[target] == [Country("POL")]
        assert own_flag in vm.flags
        assert vm.persistent["rn_ip_epoch"] == 8  # noqa: PLR2004
        assert not vm.requests
        if kind == "party":
            assert vm.persistent["rn_ip_party_group"] == 4  # noqa: PLR2004
        vm.run("rn_inline_pair_cancel_" + kind)
        assert vm.arrays[target] == []
        assert own_flag not in vm.flags
        assert vm.persistent["rn_ip_epoch"] == 9  # noqa: PLR2004
        assert {name: vm.arrays[name] for name, _ in BUFFERS} == before_buffers
        assert not vm.requests
        self.lifecycle_cases += 1
        for other in OTHER_PANEL_FLAGS:
            vm = self.fresh()
            vm.enforce = False
            vm.flags = {other}
            before = vm.state()
            vm.run("rn_inline_pair_open_" + kind)
            assert vm.state() == before, ("Open failed exclusion", kind, other)
            assert not vm.requests, ("Open failed exclusion", kind, other)
            self.lifecycle_cases += 1


def party_slot_checks(
    effects: dict[str, list[Node]], locs: dict[str, list[Node]], chars: dict[str, str]
) -> int:
    """Render every party buffer slot with every character code and past the length.

    Returns:
        The number of slot renderings checked.
    """
    loc_checks = 0
    vm = ApplyVM(effects, locs, chars, "party")
    for prefix, array, length in (
        ("PS", "rn_pshort", "rn_pshort_len"),
        ("PL", "rn_plong", "rn_plong_len"),
    ):
        vm.persistent[length] = Decimal(32)
        for slot in range(PARTY_SLOTS):
            for code in range(1, 85):
                vm.arrays[array] = [Decimal(code)] * 32
                assert vm.localized(f"RN_{prefix}_{slot}") == chars[f"RN_CH_{code}"]
                loc_checks += 1
            vm.persistent[length] = Decimal(slot)
            assert vm.localized(f"RN_{prefix}_{slot}") == "", (
                "length suppression failed",
                prefix,
                slot,
            )
            vm.persistent[length] = Decimal(32)
            loc_checks += 1
    return loc_checks


def late_guard_mutation(
    effects: dict[str, list[Node]], locs: dict[str, list[Node]], chars: dict[str, str]
) -> None:
    """Remove the late country guard and require the write barrier to fire."""
    # Removing the second guard must trip the write barrier before any write.
    mutated = copy.deepcopy(effects)
    seen = 0

    def remove_late_guard(nodes: list[Node]) -> None:
        """Delete the nested (late) guard call, walking the tree in reverse."""
        nonlocal seen
        for i in range(len(nodes) - 1, -1, -1):
            key, _, value = nodes[i]
            if key in {"if", "else_if", "else"}:
                remove_late_guard(value)
            elif key == "rn_inline_pair_guard_country":
                seen += 1
                if seen == 1:  # Reverse walk encounters the nested late call first.
                    del nodes[i]

    remove_late_guard(mutated["rn_inline_pair_apply_country"])
    assert seen == 2  # noqa: PLR2004
    vm = ApplyVM(mutated, locs, chars, "country")
    try:
        vm.run("rn_inline_pair_apply_country")
    except AssertionError as exc:
        if "write before late guard" not in str(exc):
            raise AssertionError(str(exc)) from None
    else:
        msg = "missing late-guard mutation survived"
        raise AssertionError(msg)


def main() -> None:
    """Run every check in order and write ``static-review.json`` on success."""
    effects, locs, chars = load()
    for kind in ("country", "party"):
        pure_audit(effects, "rn_inline_pair_guard_" + kind)
    pure_audit(effects, "rn_inline_pair_validate")
    assertions, rejection_cases, lifecycle_cases = 0, 0, 0
    for kind in ("country", "party"):
        checks = KindChecks(effects, locs, chars, kind)
        checks.rejections()
        checks.successes()
        checks.lifecycle()
        rejection_cases += checks.rejection_cases
        assertions += checks.success_cases
        lifecycle_cases += checks.lifecycle_cases
    loc_checks = party_slot_checks(effects, locs, chars)
    late_guard_mutation(effects, locs, chars)
    report_files = [
        APPLY,
        PARTY_LOC,
        HERE / "generate.py",
        HERE / "check.py",
        HERE / "README.md",
        HERE / "contract.json",
        SHARED / "scripted_effects/rn_inline_pair_payload.txt",
        SHARED / "scripted_effects/rn_inline_payload.txt",
        REPO / "mod/common/scripted_effects/rename_anything_generated_effects.txt",
        REPO / "mod/common/scripted_triggers/rename_anything_triggers.txt",
        REPO / "mod/localisation/english/rename_anything_chars_l_english.yml",
    ]
    report = {
        "scope": (
            "Limited offline source-model only; setter requests recorded, "
            "no engine/rename/capability/GUI runtime proof"
        ),
        "rejection_invariance_cases": rejection_cases,
        "successful_source_request_cases": assertions,
        "future_lifecycle_source_cases": lifecycle_cases,
        "party_slot_localisation_checks": loc_checks,
        "missing_late_guard_mutation": "rejected before first persistent write",
        "both_payloads_before_writes": True,
        "late_full_guard_before_writes": True,
        "legacy_buffer_untouched": True,
        "activated": False,
        "findings": [],
        "files": {
            str(p.relative_to(REPO)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in report_files
        },
    }
    (HERE / "static-review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"Offline Apply source-model PASS: {rejection_cases} rejections, {assertions} emitted "
        f"requests, {lifecycle_cases} lifecycle cases, {loc_checks} slot checks; "
        "late-guard mutation rejected. No runtime claim."
    )


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
