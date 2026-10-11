"""Limited execution: the real Apply paths run in the borrowed ApplyVM."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from inline_checks.constants import (
    ERR_CAPABILITY,
    ERR_CLOSED,
    ERR_CODE,
    ERR_COOLDOWN,
    ERR_EPOCH,
    ERR_NATIVE,
    ERR_TARGET,
    GROUP_KEYS,
    GROUPS,
    MAX_NAME,
    REFUSED_KEYS,
    REFUSED_SENTINELS,
    REV_CAP,
    STALE_SENTINEL,
    STATUS_NO_BRIDGE,
    VM_EPOCH,
    VM_TODAY,
)
from inline_checks.fixtures import NATIVE_ALPHABET, ApplyVM, Country
from inline_checks.tree import get
from modgen.features.cooldown import COOLDOWN_DAYS

if TYPE_CHECKING:
    from collections.abc import Callable


class ProductVM(ApplyVM):
    """ApplyVM with ROOT tracking, a fixed day counter and the editor's own triggers."""

    def __init__(  # noqa: PLR0913 - the four ApplyVM inputs plus tag and triggers
        self,
        effects: dict[str, Any],
        locs: dict[str, Any],
        chars: dict[str, str],
        kind: str,
        *,
        tag: str,
        triggers: dict[str, Any],
    ) -> None:
        """Create a VM for an own country other than the base VM's POL.

        Args:
            effects: Effect name to parsed body.
            locs: Scripted loc name to its ``text`` entries.
            chars: Localisation key to text.
            kind: ``party`` or ``country``.
            tag: Own country tag; the open editor is pinned to it.
            triggers: Source scripted triggers evaluated by name.
        """
        super().__init__(effects, locs, chars, kind)
        self.tag = tag
        self.root_tag = tag
        self.arrays["rn_ip_country_target"] = [Country(tag)]
        self.arrays["rn_ip_party_target"] = [Country(tag)]
        self.triggers = triggers
        self.persistent["global.num_days"] = Decimal(VM_TODAY)

    def condition(self, nodes: list[Any]) -> bool:
        """Evaluate a trigger list.

        Args:
            nodes: Trigger nodes.

        Returns:
            Whether every trigger holds.
        """
        for key, op, value in nodes:
            if key == "tag" and value == "ROOT":
                answer = self.tag == self.root_tag
            elif key in {"rn_ipp_party_target_matches", "rn_ipp_party_pinned_rules"}:
                answer = self.condition(self.triggers[key]) == (value == "yes")
            elif key in {"set_temp_variable", "subtract_from_temp_variable"}:
                # HOI4 allows temp-variable arithmetic in triggers (vanilla ai_strategy/ENG.txt).
                name, _, src = value[0]
                if key == "set_temp_variable":
                    self.temp[name] = self.value(src)
                else:
                    self.temp[name] = self.temp.get(name, Decimal(0)) - self.value(src)
                answer = True
            elif key.startswith("rn_ip_cooldown_active_"):
                kind = key.removeprefix("rn_ip_cooldown_active_")
                left = self.persistent.get(f"rn_ip_cd_{kind}_until", Decimal(0)) - self.value(
                    "global.num_days"
                )
                answer = (left > 0) == (value == "yes")
            else:
                answer = super().condition([(key, op, value)])
            if not answer:
                return False
        return True


class Context:
    """Everything one ApplyVM case needs: effects, localisation, characters and triggers."""

    def __init__(
        self,
        effects: dict[str, Any],
        locmap: dict[str, Any],
        chars: dict[str, str],
        triggers: dict[str, Any],
    ) -> None:
        """Store the shared inputs.

        Args:
            effects: Source plus legacy effects.
            locmap: Scripted localisation name to text branches.
            chars: Localisation key to text (character table and editor strings).
            triggers: Source scripted triggers.
        """
        self.effects = effects
        self.locmap = locmap
        self.chars = chars
        self.triggers = triggers

    def vm(self, kind: str, tag: str = "FRA", effects: dict[str, Any] | None = None) -> ProductVM:
        """Create a fresh VM for one case.

        Args:
            kind: ``party`` or ``country``.
            tag: Own country tag.
            effects: Replacement effects for negative cases.

        Returns:
            The VM, with an open editor, a fresh epoch and a valid payload.
        """
        return ProductVM(
            effects if effects is not None else self.effects,
            self.locmap,
            self.chars,
            kind,
            tag=tag,
            triggers=self.triggers,
        )


def run_party_groups(ctx: Context) -> int:
    """Run the four party groups under every government, plus the I4-M1 placeholder.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for tag in ("GER", "ENG", "FRA"):
        for group, government in GROUPS:
            vm = ctx.vm("party", tag)
            vm.government = government
            vm.persistent["rn_ip_party_group"] = Decimal(group)
            vm.run("rn_inline_pair_apply_party")
            assert len(vm.requests) == 1
            assert vm.pair_count == 1
            assert vm.guard_count == 2  # noqa: PLR2004 - both guard rounds
            request = get(vm.requests[0], "set_party_name")
            assert get(request, "ideology") == government
            assert len(get(request, "long_name")) == MAX_NAME
            assert vm.persistent["rn_ip_epoch"] == VM_EPOCH + 1
            ruling = ctx.vm("party", tag)
            ruling.government = government
            ruling.persistent["rn_ip_party_group"] = Decimal(group)
            assert ruling.localized("RN_IPP_PARTY_SHORT") == ctx.chars["RN_IPP_PARTY_SHORT_CURRENT"]
            assert ruling.localized("RN_IPP_PARTY_LONG") == ctx.chars["RN_IPP_PARTY_LONG_CURRENT"]
            assert ruling.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IP_HINT"]
            cases += 1 + run_non_ruling(ctx, tag, group, government)
            cases += run_placeholder(ctx, tag, group)
            bad = ctx.vm("party", tag)
            bad.persistent["rn_ip_party_group"] = Decimal(len(GROUPS) + 1)
            state = bad.state()
            bad.run("rn_inline_pair_apply_party")
            assert bad.state() == state
            assert not bad.requests
            assert bad.temp["rn_pair_err"] == ERR_TARGET
            assert bad.localized("RN_IPP_PARTY_SHORT") == ""
            assert bad.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IPP_TARGET_CHANGED"]
            bad.enforce = False
            bad.run("rn_inline_pair_cancel_party")
            assert "rn_ip_party_neutrality_open" not in bad.flags
            cases += 1
    return cases


def run_non_ruling(ctx: Context, tag: str, group: int, government: str) -> int:
    """Rename a pinned group while another ideology (or a custom one) rules.

    Args:
        ctx: Shared VM inputs.
        tag: Own country tag.
        group: Pinned group number.
        government: Ideology of the pinned group.

    Returns:
        Number of cases.
    """
    cases = 0
    for other in [g for _, g in GROUPS if g != government] + ["custom_ideology"]:
        vm = ctx.vm("party", tag)
        vm.government = other
        vm.persistent["rn_ip_party_group"] = Decimal(group)
        assert vm.condition(ctx.triggers["rn_ipp_party_target_matches"])
        short_key = "RN_IPP_PARTY_SHORT_" + GROUP_KEYS[group - 1]
        assert vm.localized("RN_IPP_PARTY_SHORT") == ctx.chars[short_key]
        assert vm.localized("RN_IPP_PARTY_LONG") == ctx.chars["RN_IPP_LONG_PLACEHOLDER"] == "?"
        assert vm.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IPP_LONG_UNKNOWN"]
        vm.run("rn_inline_pair_apply_party")
        assert len(vm.requests) == 1
        assert get(get(vm.requests[0], "set_party_name"), "ideology") == government
        cases += 1
    return cases


def run_placeholder(ctx: Context, tag: str, group: int) -> int:
    """Prove that an unchanged ``?`` placeholder never reaches the setter (I4-M1).

    Args:
        ctx: Shared VM inputs.
        tag: Own country tag.
        group: Pinned group number.

    Returns:
        Number of cases.
    """
    placeholder = ctx.chars["RN_IPP_LONG_PLACEHOLDER"]
    table = {ctx.chars[k] for k in ctx.chars if k.startswith("RN_CH_")}
    assert placeholder
    assert all(c not in NATIVE_ALPHABET and c not in table for c in placeholder)
    empty_b = {f"rn_nativeb_{i}": Decimal(0) for i in range(MAX_NAME)}
    mutations: list[tuple[str, Callable[[ProductVM], None], int]] = [
        (
            "native ok=0",
            lambda v: v.temp.update(rn_nativeb_ok=Decimal(0), rn_nativeb_len=Decimal(0), **empty_b),
            ERR_NATIVE,
        ),
        ("forged code 85", lambda v: v.temp.update(rn_nativeb_0=Decimal(85)), ERR_CODE),
    ]
    for label, mutate, want in mutations:
        vm = ctx.vm("party", tag)
        vm.government = "custom_ideology"
        vm.persistent["rn_ip_party_group"] = Decimal(group)
        mutate(vm)
        state = vm.state()
        vm.run("rn_inline_pair_apply_party")
        assert vm.state() == state, label
        assert not vm.requests, label
        assert vm.temp["rn_pair_err"] == want, label
        assert vm.temp["rn_pair_field"] == 2, label  # noqa: PLR2004 - field B
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IP_ERR_PARTY_LONG_UNKNOWN"]
    return len(mutations)


def run_tabs(ctx: Context) -> int:
    """Switch between every pair of tabs and check the no-op cases.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for start, _ in GROUPS:
        for tab, ideology in GROUPS:
            vm = ctx.vm("party")
            vm.enforce = False
            vm.persistent["rn_ip_party_group"] = Decimal(start)
            vm.arrays["rn_ip_party_target"] = [Country("FRA")]
            before = vm.state()
            vm.temp["rn_ip_party_tab"] = Decimal(tab)
            vm.run("rn_inline_pair_switch_party")
            if tab == start:
                assert vm.state() == before
            else:
                assert vm.persistent["rn_ip_party_group"] == tab
                assert vm.persistent["rn_ip_epoch"] == VM_EPOCH + 1
                assert not vm.requests
                assert not any(k.startswith("rn_ip_cd_") for k in vm.persistent)
                vm.enforce = True
                vm.pair_count = vm.guard_count = 0
                vm.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH + 1)
                vm.run("rn_inline_pair_apply_party")
                assert get(get(vm.requests[0], "set_party_name"), "ideology") == ideology
            cases += 1
    for blocker in ("closed", "cooldown", "bad tab"):
        vm = ctx.vm("party")
        vm.enforce = False
        vm.temp["rn_ip_party_tab"] = Decimal(len(GROUPS) + 1 if blocker == "bad tab" else 2)
        if blocker == "closed":
            vm.flags.clear()
        if blocker == "cooldown":
            vm.persistent["rn_ip_cd_party_until"] = Decimal(VM_TODAY + 3)
        before = vm.state()
        vm.run("rn_inline_pair_switch_party")
        assert vm.state() == before, blocker
        cases += 1
    return cases


def run_no_bridge(ctx: Context) -> int:
    """Apply without the bridge's command epoch: no write and the extension message.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    for kind in ("party", "country"):
        vm = ctx.vm(kind)
        vm.temp.pop("rn_ip_cmd_epoch")
        state = vm.state()
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.state() == state
        assert not vm.requests
        assert vm.temp["rn_pair_err"] == ERR_EPOCH
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.persistent["rn_ip_status_err"] == STATUS_NO_BRIDGE
        status = "RN_IP_STATUS" if kind == "country" else "RN_IPP_PARTY_STATUS"
        assert vm.localized(status) == ctx.chars["RN_IP_ERR_NO_BRIDGE"]
        stale = ctx.vm(kind)
        stale.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
        stale.run("rn_inline_pair_apply_" + kind)
        stale.enforce = False
        stale.run("rn_ip_status_record_pair")
        assert stale.persistent["rn_ip_status_err"] == ERR_EPOCH, "a real stale epoch stays stale"
    return 4


def _reject_field(vm: ProductVM, field: int, code: int | None) -> None:
    """Make the native encoder reject one field, optionally with its reason.

    Args:
        vm: VM to change.
        field: 1 (``rn_native_*``) or 2 (``rn_nativeb_*``).
        code: Encoder ``InputError`` sent as ``rn_native_err`` / ``rn_nativeb_err``,
            or None for a bridge that sends no reason.
    """
    prefix = "rn_native" if field == 1 else "rn_nativeb"
    vm.temp[f"{prefix}_ok"] = Decimal(0)
    vm.temp[f"{prefix}_len"] = Decimal(0)
    for i in range(MAX_NAME):
        vm.temp[f"{prefix}_{i}"] = Decimal(0)
    if code is not None:
        vm.temp[f"{prefix}_err"] = Decimal(code)


def run_error_reasons(ctx: Context) -> int:
    """Run rejected fields through the real Apply and check the one-line reason.

    The encoder's ``InputError`` (1 empty, 2 too long, 3..6 character classes)
    picks the reference string; no reason or an unknown one keeps the generic
    line. A non-ruling party's full name keeps the "type it in place of ?" line
    for a character error, because that is the untouched placeholder.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    reasons: dict[int | None, str] = {
        1: "_EMPTY",
        2: "_LONG",
        3: "_CHAR",
        4: "_CHAR",
        5: "_CHAR",
        6: "_CHAR",
        7: "",
        None: "",
    }
    fields = {
        ("country", 1): "RN_IP_ERR_COUNTRY_NAME",
        ("country", 2): "RN_IP_ERR_COUNTRY_ADJ",
        ("party", 1): "RN_IP_ERR_PARTY_SHORT",
        ("party", 2): "RN_IP_ERR_PARTY_LONG",
    }
    cases = 0
    for (kind, field), base in fields.items():
        for code, suffix in reasons.items():
            vm = ctx.vm(kind)
            vm.government = "democratic"
            vm.persistent["rn_ip_party_group"] = Decimal(1)
            _reject_field(vm, field, code)
            state = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            assert vm.state() == state, (kind, field, code)
            assert not vm.requests, (kind, field, code)
            assert vm.temp["rn_pair_err"] == ERR_NATIVE, (kind, field, code)
            assert vm.temp["rn_pair_field"] == field, (kind, field, code)
            vm.enforce = False
            vm.run("rn_ip_status_record_pair")
            status = "RN_IP_STATUS" if kind == "country" else "RN_IPP_PARTY_STATUS"
            assert vm.localized(status) == ctx.chars[base + suffix], (kind, field, code)
            cases += 1
    for code, want in ((1, "RN_IP_ERR_PARTY_LONG_EMPTY"), (6, "RN_IP_ERR_PARTY_LONG_UNKNOWN")):
        vm = ctx.vm("party")
        vm.government = "custom_ideology"
        _reject_field(vm, 2, code)
        vm.run("rn_inline_pair_apply_party")
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.localized("RN_IPP_PARTY_STATUS") == ctx.chars[want], code
        cases += 1
    for code, suffix in reasons.items():
        vm = ctx.vm("country")
        vm.enforce = False
        vm.flags.add("rn_ip_leader_open")
        vm.temp["rn_ip_leader_error"] = Decimal(ERR_NATIVE)
        if code is not None:
            vm.temp["rn_native_err"] = Decimal(code)
        vm.run("rn_ip_status_record_leader")
        assert vm.localized("RN_IP_STATUS") == ctx.chars["RN_IP_ERR_LEADER" + suffix], code
        cases += 1
    vm = ctx.vm("country")
    vm.enforce = False
    vm.temp["rn_native_err"] = Decimal(2)
    vm.run("rn_ip_status_clear")
    assert "rn_ip_status_why" not in vm.persistent
    assert vm.localized("RN_IP_STATUS") == ctx.chars["RN_IP_HINT"]
    return cases + 1


def run_stale_sentinel(ctx: Context) -> int:
    """A command epoch of -1 (editor widget the bridge did not open) shows the stale line.

    This is the script half of the proposed fix for an editor that was left open
    when the politics panel closed: nothing is written and the player reads
    "This editor is out of date. Cancel and open it again."

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    assert ctx.chars["RN_IPP_TARGET_CHANGED"] == ctx.chars["RN_IP_ERR_STALE"]
    for kind in ("party", "country"):
        vm = ctx.vm(kind)
        vm.temp["rn_ip_cmd_epoch"] = Decimal(STALE_SENTINEL)
        state = vm.state()
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.state() == state, kind
        assert not vm.requests, kind
        assert vm.temp["rn_pair_err"] == ERR_EPOCH, kind
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.persistent["rn_ip_status_err"] == ERR_EPOCH, kind
        status = "RN_IP_STATUS" if kind == "country" else "RN_IPP_PARTY_STATUS"
        assert vm.localized(status) == ctx.chars["RN_IP_ERR_STALE"], kind
    return 2


def run_refused_sentinels(ctx: Context) -> int:
    """Cause-coded refusals (-2, -3) show their own line; nothing is written.

    The guard still returns 8 (any negative command epoch differs from the
    opening epoch); only the status line tells the player that reopening the
    editor will not help. The leader editor gets the same lines.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for sentinel, code in REFUSED_SENTINELS.items():
        want = ctx.chars[REFUSED_KEYS[code]]
        assert want != ctx.chars["RN_IP_ERR_STALE"]
        for kind in ("party", "country"):
            vm = ctx.vm(kind)
            vm.temp["rn_ip_cmd_epoch"] = Decimal(sentinel)
            state = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            assert vm.state() == state, (kind, sentinel)
            assert not vm.requests, (kind, sentinel)
            assert vm.temp["rn_pair_err"] == ERR_EPOCH, (kind, sentinel)
            vm.enforce = False
            vm.run("rn_ip_status_record_pair")
            assert vm.persistent["rn_ip_status_err"] == code, (kind, sentinel)
            status = "RN_IP_STATUS" if kind == "country" else "RN_IPP_PARTY_STATUS"
            assert vm.localized(status) == want, (kind, sentinel)
            cases += 1
        vm = ctx.vm("country")
        vm.enforce = False
        vm.flags.add("rn_ip_leader_open")
        vm.temp["rn_ip_cmd_epoch"] = Decimal(sentinel)
        vm.temp["rn_ip_leader_error"] = Decimal(ERR_EPOCH)
        vm.run("rn_ip_status_record_leader")
        assert vm.persistent["rn_ip_status_err"] == code, ("leader", sentinel)
        assert vm.localized("RN_IP_STATUS") == want, ("leader", sentinel)
        cases += 1
    for sentinel in (STALE_SENTINEL, -4, 0):
        vm = ctx.vm("country")
        vm.enforce = False
        vm.temp["rn_ip_cmd_epoch"] = Decimal(sentinel)
        vm.temp["rn_pair_err"] = Decimal(ERR_EPOCH)
        vm.temp["rn_pair_field"] = Decimal(0)
        vm.run("rn_ip_status_record_pair")
        expected = STATUS_NO_BRIDGE if sentinel == 0 else ERR_EPOCH
        assert vm.persistent["rn_ip_status_err"] == expected, sentinel
        cases += 1
    return cases


PARTY_LOCS = ("RN_IPP_PARTY_SHORT", "RN_IPP_PARTY_LONG", "RN_IPP_PARTY_STATUS")
"""Party scripted localisation evaluated every frame while the party editor is open."""


def _repeated_target_check(locmap: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the earlier form of the party texts: the target check in every branch.

    The current form checks ``rn_ipp_party_target_matches`` once, as the first
    branch (empty carrier or stale line when it fails). The earlier form put the
    check into each target-dependent branch instead.

    Args:
        locmap: Scripted localisation name to its ``text`` entries.

    Returns:
        A copy with the three party texts in the earlier form.
    """
    matches = ("rn_ipp_party_target_matches", "=", "yes")
    guard = ("trigger", "=", [("NOT", "=", [matches])])
    old = copy.deepcopy(locmap)
    for name in PARTY_LOCS:
        texts = old[name]
        at = next(i for i, (_, _, body) in enumerate(texts) if guard in body)
        kept = texts[:at]
        for _, op, body in texts[at + 1 : -1]:
            trigger = get(body, "trigger")
            rest = [n for n in body if n[0] != "trigger"]
            kept.append(("text", op, [("trigger", "=", [matches, *trigger]), *rest]))
        kept.append(texts[-1])
        old[name] = kept
    return old


def _render_party(ctx: Context, locmap: dict[str, Any], state: tuple[Any, ...]) -> tuple[Any, ...]:
    """Render the three party texts for one editor state.

    Args:
        ctx: Shared VM inputs.
        locmap: Scripted localisation to render with.
        state: Target kind, group, government, status code, field and reason.

    Returns:
        The short carrier, long carrier and status line.
    """
    target, group, government, status, field, why = state
    vm = ProductVM(ctx.effects, locmap, ctx.chars, "party", tag="FRA", triggers=ctx.triggers)
    vm.government = government
    vm.persistent["rn_ip_party_group"] = Decimal(group or 1)
    if target == "closed":
        vm.flags.discard("rn_ip_party_neutrality_open")
    elif target == "foreign":
        vm.arrays["rn_ip_party_target"] = [Country("GER")]
    elif target == "group":
        vm.persistent["rn_ip_party_group"] = Decimal(len(GROUPS) + 1)
    if status is not None:
        vm.persistent["rn_ip_status_err"] = Decimal(status)
        vm.persistent["rn_ip_status_field"] = Decimal(field)
        if why is not None:
            vm.persistent["rn_ip_status_why"] = Decimal(why)
    return tuple(vm.localized(name) for name in PARTY_LOCS)


def run_party_loc_equivalence(ctx: Context) -> int:
    """Prove the single target check gives the same party texts as the repeated one.

    Every combination of target state (matching, editor closed, foreign pin,
    group out of range), government, group, status code, field and reason is
    rendered with both forms and must give the same text.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of compared states.
    """
    old = _repeated_target_check(ctx.locmap)
    assert old != ctx.locmap
    targets = ("match", "closed", "foreign", "group")
    statuses: list[int | None] = [None, ERR_NATIVE, ERR_CODE, ERR_CLOSED, ERR_EPOCH, ERR_TARGET]
    statuses += [ERR_COOLDOWN, STATUS_NO_BRIDGE, *REFUSED_KEYS]
    cases = 0
    for target in targets:
        for group, government in [*GROUPS, (0, "custom_ideology")]:
            for status in statuses:
                for field, why in ((1, None), (1, 1), (2, None), (2, 2), (2, 3)):
                    state = (target, group, government, status, field, why)
                    renders = [_render_party(ctx, locmap, state) for locmap in (ctx.locmap, old)]
                    assert renders[0] == renders[1], state
                    cases += 1
    return cases


def run_caption_counter(ctx: Context, models: dict[str, Any]) -> int:
    """Run the real party Apply callback and check the caption revision counter.

    Args:
        ctx: Shared VM inputs.
        models: The six politics models.

    Returns:
        Number of cases.
    """
    block = get(
        get(models["rn_ip_party_neutrality_gui"], "effects"), "rn_ip_party_neutrality_apply_click"
    )
    block = [n for n in block if n[0] != "log"]
    cases = 0
    for start, success, want in ((0, True, 1), (5, False, 5), (REV_CAP, True, REV_CAP)):
        vm = ctx.vm("party")
        vm.persistent["rn_ip_pui_rev"] = Decimal(start)
        if not success:
            vm.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
            # The rejected callback records its UI status, a write the barrier would flag.
            vm.enforce = False
        vm.execute(block)
        assert vm.persistent["rn_ip_pui_rev"] == want, (start, success)
        cases += 1
    return cases


def run_cooldown(ctx: Context) -> int:
    """Run the cooldown cases: start, boundaries, independence and the late guard.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    expiry = Decimal(VM_TODAY + COOLDOWN_DAYS)
    cases = 0
    for kind in ("party", "country"):
        other = "country" if kind == "party" else "party"
        ok = ctx.vm(kind)
        ok.run("rn_inline_pair_apply_" + kind)
        assert ok.persistent[f"rn_ip_cd_{kind}_until"] == expiry
        assert f"rn_ip_cd_{other}_until" not in ok.persistent
        assert "rn_ip_cd_leader_until" not in ok.persistent
        rejected = ctx.vm(kind)
        rejected.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
        before = rejected.state()
        rejected.run("rn_inline_pair_apply_" + kind)
        assert rejected.state() == before
        cases += 2
        for until, blocked in (
            (VM_TODAY + 1, True),
            (expiry, True),
            (VM_TODAY, False),
            (VM_TODAY - 1, False),
        ):
            vm = ctx.vm(kind)
            vm.persistent[f"rn_ip_cd_{kind}_until"] = Decimal(until)
            before = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            if blocked:
                assert vm.state() == before, (kind, until)
                assert vm.temp["rn_pair_err"] == ERR_COOLDOWN, (kind, until)
            else:
                assert vm.persistent[f"rn_ip_cd_{kind}_until"] == expiry, (kind, until)
            cases += 1
        vm = ctx.vm(kind)
        vm.persistent[f"rn_ip_cd_{other}_until"] = Decimal(VM_TODAY + 3)
        vm.persistent["rn_ip_cd_leader_until"] = Decimal(VM_TODAY + 3)
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.temp["rn_pair_err"] == 0, ("types independent", kind)
        cases += 1 + run_late_cooldown(ctx, kind)
    for k in ("country", "leader", "party"):
        vm = ctx.vm("party")
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY + 3)
        assert vm.localized(f"RN_IP_CD_LEFT_{k.upper()}") == ctx.chars["RN_IP_CD_DAYS_3"]
        assert vm.localized(f"RN_IP_CD_{k.upper()}") == ctx.chars[f"RN_IP_CD_{k.upper()}_ACTIVE"]
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY)
        assert vm.localized(f"RN_IP_CD_{k.upper()}") == ""
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY + 45)
        assert vm.localized(f"RN_IP_CD_LEFT_{k.upper()}") == ctx.chars["RN_IP_CD_DAYS_MORE"]
        cases += 1
    return cases


def run_late_cooldown(ctx: Context, kind: str) -> int:
    """A cooldown that starts between the two guard rounds rejects without writes.

    Args:
        ctx: Shared VM inputs.
        kind: ``party`` or ``country``.

    Returns:
        Number of cases.
    """
    vm = ctx.vm(kind)
    observed: list[Any] = []

    def late(v: ProductVM) -> None:
        """Start the cooldown after the first guard round (a queued command).

        Args:
            v: The VM being run.
        """
        v.persistent[f"rn_ip_cd_{kind}_until"] = Decimal(VM_TODAY + 2)
        observed.append(v.state())

    vm.late_mutation = late
    vm.run("rn_inline_pair_apply_" + kind)
    assert vm.state() == observed[0]
    assert vm.temp["rn_pair_err"] == ERR_COOLDOWN
    return 1


def run_rejections(ctx: Context) -> int:
    """Reject every bad input before and after validation, with zero writes.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    mutations: list[tuple[str, Callable[[ProductVM], None], int]] = [
        ("epoch", lambda v: v.temp.update(rn_ip_cmd_epoch=Decimal(VM_EPOCH - 1)), ERR_EPOCH),
        ("fractional epoch", lambda v: v.persistent.update(rn_ip_epoch=Decimal("7.25")), ERR_EPOCH),
        ("root mismatch", lambda v: setattr(v, "root_tag", "GER"), ERR_CLOSED),
        ("foreign pin", lambda v: v.arrays.update(rn_ip_party_target=[Country("GER")]), ERR_TARGET),
        (
            "duplicate pin",
            lambda v: v.arrays.update(rn_ip_party_target=[Country("FRA"), Country("FRA")]),
            ERR_TARGET,
        ),
        ("legacy", lambda v: v.flags.add("rn_input"), ERR_CLOSED),
        ("legacy-open", lambda v: v.flags.add("rn_open"), ERR_CLOSED),
        (
            "group out of range",
            lambda v: v.persistent.update(rn_ip_party_group=Decimal(0)),
            ERR_TARGET,
        ),
        ("invalid B", lambda v: v.temp.update(rn_nativeb_31=Decimal("1.5")), ERR_CODE),
    ]
    cases = 0
    for late in (False, True):
        for label, mutate, want in mutations:
            if late and label == "invalid B":
                continue
            vm = ctx.vm("party")
            observed: list[Any] = []
            if late:

                def callback(
                    v: ProductVM,
                    fn: Callable[[ProductVM], None] = mutate,
                    seen: list[Any] = observed,
                ) -> None:
                    """Apply the mutation between the two guard rounds.

                    Args:
                        v: The VM being run.
                        fn: The mutation (bound now, not at call time).
                        seen: Receives the state right after the mutation.
                    """
                    fn(v)
                    seen.append(v.state())

                vm.late_mutation = callback
            else:
                mutate(vm)
            before = vm.state()
            vm.run("rn_inline_pair_apply_party")
            assert vm.state() == (observed[0] if late else before), (late, label)
            assert not vm.requests, (late, label)
            assert vm.temp["rn_pair_err"] == want, (late, label)
            cases += 1
    for cap, want in ((0, ERR_CAPABILITY), (2, ERR_CAPABILITY), (1, 0)):
        vm = ctx.vm("country")
        vm.temp["rn_native_cap"] = Decimal(cap)
        before = vm.state()
        vm.run("rn_inline_pair_apply_country")
        assert vm.temp["rn_pair_err"] == want
        assert (vm.state() == before) if want else (len(vm.requests) == 1)
        cases += 1
    for group, government in [*GROUPS, (0, "custom_ideology")]:
        vm = ctx.vm("party")
        vm.flags.clear()
        vm.government = government
        vm.enforce = False
        before = vm.state()
        vm.run("rn_inline_pair_open_party")
        if group:
            assert vm.persistent["rn_ip_party_group"] == group
        else:
            assert vm.state() == before
        cases += 1
    return cases


def run_missing_late_guard(ctx: Context) -> None:
    """A party Apply without its second guard round must trip the VM's write barrier.

    Args:
        ctx: Shared VM inputs.

    Raises:
        AssertionError: The broken Apply was not caught.
    """
    broken = copy.deepcopy(ctx.effects)
    late = get(next(v for k, _, v in broken["rn_inline_pair_apply_party"] if k == "if"), "if")
    late.remove(("rn_inline_pair_guard_party", "=", "yes"))
    try:
        ctx.vm("party", effects=broken).run("rn_inline_pair_apply_party")
    except AssertionError as exc:
        assert "write before late guard" in str(exc)  # noqa: PT017 - plain script, no pytest
    else:
        msg = "negative fixture missing late guard survived"
        raise AssertionError(msg)
