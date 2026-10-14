"""Host switches (ADR-0036): structure and VM cases.

Structure. Every feature has its rule (default on, descriptions on the options,
"Rename Anything:" names in every language), and only the generated trigger file
reads those rules. Every enabled trigger that checks a cooldown also checks the
matching switch, every button greyed out by a switch has a tooltip with the
switch line, every tooltip key exists in every language, and both diplomatic
actions show the switch as a readable prerequisite.

VM. With one switch off at a time, the real effects write nothing and report the
switch: the politics name and party editors (``rn_pair_err`` 21), the subject
editors for each kind and for "other countries", the subject's Restore name,
the faction editor, the flag picker (Apply, Restore, opening) and the legacy
country name, its Restore and the typed country buffers.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from inline_checks.capie_cases import APPLY, KIND_FLAGS, _case, _faction_case
from inline_checks.constants import MOD, SOURCE
from inline_checks.fixtures import parse
from inline_checks.flag_cases import Inputs, capie, layer, open_own, open_sub, root_err
from inline_checks.tree import declarations, get, models_of, walk
from modgen.common import LANGS
from modgen.features.switches import ERR_FEATURE_OFF, FEATURES

if TYPE_CHECKING:
    from inline_checks.vm_cases import Context

COOLDOWN_SWITCH = {
    "rn_ip_cooldown_active_country": "country",
    "rn_ip_cooldown_active_leader": "leader",
    "rn_ip_cooldown_active_party": "party",
    "rn_fp_cooldown_active": "flag",
    "rn_fac_cooldown_active": "factions",
    "rn_cd_state_active": "states",
    "rn_cd_vp_active": "states",
}
"""Cooldown trigger to the switch of the same feature."""


def _off(feature: str) -> str:
    """Return the rule option that switches a feature off.

    Args:
        feature: Feature id.

    Returns:
        Option name.
    """
    return f"RN_FEATURE_{feature.upper()}_OFF"


def _loc(lang: str) -> dict[str, str]:
    """Return every localisation key and text of one language in ``mod/``.

    Args:
        lang: Game language.

    Returns:
        Key to text.
    """
    out: dict[str, str] = {}
    for path in (MOD / "localisation" / lang).glob("*.yml"):
        text = path.read_text(encoding="utf-8-sig")
        out.update(re.findall(r'^ (\S+?):\d* "(.*)"$', text, re.MULTILINE))
    return out


def _all_models() -> dict[str, Any]:
    """Return the source and generated scripted GUI models.

    Returns:
        Model name to body.
    """
    return {
        **models_of(SOURCE / "common" / "scripted_guis"),
        **models_of(MOD / "common" / "scripted_guis", "rename_anything_*.txt"),
        **models_of(MOD / "common" / "scripted_guis", "rn_flag_picker.txt"),
    }


def _buttons() -> dict[str, list[Any]]:
    """Return every button of the source and generated GUI files by name.

    Returns:
        Button name to body (the last one wins for names shared by two windows).
    """
    paths = [*sorted((SOURCE / "interface").glob("*.gui"))]
    paths += [MOD / "interface" / "rename_anything.gui", MOD / "interface" / "rn_flag_picker.gui"]
    out: dict[str, list[Any]] = {}
    for path in paths:
        for kind, _, body in walk(parse(path.read_text(encoding="utf-8-sig"))):
            if kind == "buttonType":
                out[str(get(body, "name"))] = body
    return out


def check_switch_structure() -> None:
    """Check the rules, the single reading place, the trigger coupling and the tooltips."""
    rules = parse((MOD / "common" / "game_rules" / "rn_feature_rules.txt").read_text("utf-8"))
    by_name = {k: v for k, _, v in rules}
    texts = {lang: _loc(lang) for lang in LANGS}
    for f in FEATURES:
        rule = by_name[f"rn_feature_{f.id}"]
        assert not any(k == "desc" for k, _, _ in rule), "rule-level desc is a parser error"
        assert get(get(rule, "default"), "name") == f"RN_FEATURE_{f.id.upper()}_ON"
        assert get(get(rule, "option"), "name") == _off(f.id)
        for block in ("default", "option"):
            for key in ("text", "desc"):
                loc_key = get(get(rule, block), key)
                assert all(loc_key in texts[lang] for lang in LANGS), (f.id, loc_key)
        name = get(rule, "name")
        assert all(texts[lang][name].startswith("Rename Anything: ") for lang in LANGS)
    readers = [
        p.relative_to(MOD).as_posix()
        for p in MOD.rglob("*.txt")
        if "rule = rn_feature_" in p.read_text(encoding="utf-8-sig")
    ]
    assert readers == ["common/scripted_triggers/rn_feature_switches.txt"], readers
    _check_coupling_and_tooltips(texts)
    actions = get(
        declarations(SOURCE / "common" / "scripted_diplomatic_actions")[
            "scripted_diplomatic_actions"
        ],
        "rn_rename_subject",
    )
    tips = [
        get(v, "tooltip") for k, _, v in get(actions, "selectable") if k == "custom_trigger_tooltip"
    ]
    assert "RN_FEAT_SUBJECTS_ALLOWED" in tips


def _check_coupling_and_tooltips(texts: dict[str, dict[str, str]]) -> None:
    """Each cooldown in an enabled trigger has its switch, and a switched button explains itself.

    Args:
        texts: Localisation of every language.
    """
    buttons = _buttons()
    for model, body in _all_models().items():
        for name, _, trigger in get(body, "triggers"):
            if not name.endswith("_click_enabled"):
                continue
            keys = {k for k, _, _ in walk(trigger)}
            for cooldown, feature in COOLDOWN_SWITCH.items():
                if cooldown in keys:
                    assert f"rn_feature_{feature}_off" in keys, (model, name, cooldown)
            switches = {k for k in keys if k.startswith("rn_feature_")}
            button = buttons.get(name.removesuffix("_click_enabled"))
            if not switches or button is None:
                continue
            tip = next((v for k, _, v in button if k == "pdx_tooltip"), None)
            assert tip is not None, ("greyed out without a tooltip", model, name)
            for lang in ("english", "polish"):
                assert "RN_FEAT_" in texts[lang][tip], ("no switch line", model, name, tip, lang)
            assert all(tip in texts[lang] for lang in LANGS), (name, tip)


# ----------------------------------------------------------------------------- VM


def _politics(ctx: Context) -> int:
    """The politics country and party editors refuse with 21 and write nothing.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    for kind in ("country", "party"):
        vm = ctx.vm(kind)
        vm.rules[f"rn_feature_{kind}"] = _off(kind)
        before = vm.state()
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.temp["rn_pair_err"] == ERR_FEATURE_OFF, kind
        assert vm.state() == before, kind
        vm.enforce = False  # the status line is written after a refusal, by design
        vm.run("rn_ip_status_record_pair")
        assert vm.persistent["rn_ip_status_err"] == ERR_FEATURE_OFF
        other = "party" if kind == "country" else "country"
        vm = ctx.vm(kind)
        vm.rules[f"rn_feature_{other}"] = _off(other)
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.temp["rn_pair_err"] == 0, ("switches are independent", kind)
    return 4


def _subjects(ctx: Context) -> int:
    """Subject editors: "other countries" and each kind's switch refuse with 21.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    names = {1: ("Dominium", "dominialny"), 2: ("Jan Nowak",), 3: ("Ruch", "Ruch Ludowy")}
    feature = {1: "country", 2: "leader", 3: "party"}
    cases = 0
    for kind, fields in names.items():
        for switch in (feature[kind], "subjects"):
            vm = _case(ctx, kind=kind, names=fields)
            vm.rules[f"rn_feature_{switch}"] = _off(switch)
            before = vm.subject_state()
            vm.run(APPLY[kind])
            assert vm.temp["rn_cv1_err"] == ERR_FEATURE_OFF, (kind, switch)
            assert vm.subject_state() == before, (kind, switch)
            assert vm.persistent["rn_cv1_st_err"] == ERR_FEATURE_OFF
            assert KIND_FLAGS[kind] in vm.flags, "the editor stays open"
            cases += 1
    for switch in ("country", "subjects"):
        vm = _case(ctx, kind=1, names=names[1])
        vm.subject["flags"].add("rn_custom_name")
        vm.subject["persistent"]["capie_cn_ver"] = Decimal(1)
        vm.rules[f"rn_feature_{switch}"] = _off(switch)
        before = vm.subject_state()
        vm.run("rn_sub_reset_country")
        assert vm.temp["rn_cv1_err"] == ERR_FEATURE_OFF, switch
        assert vm.subject_state() == before, switch
        cases += 1
    return cases


def _factions(ctx: Context) -> int:
    """The faction editor refuses Apply and Restore with 21.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    vm = _faction_case(ctx, own=True)
    vm.rules["rn_feature_factions"] = _off("factions")
    before = vm.subject_state()
    vm.run("rn_fac_apply")
    assert vm.temp["rn_cv1_err"] == ERR_FEATURE_OFF
    assert vm.subject_state() == before
    vm = _faction_case(ctx, own=True)
    vm.subject["persistent"]["capie_fn_ver"] = Decimal(1)
    vm.rules["rn_feature_factions"] = _off("factions")
    before = vm.subject_state()
    vm.run("rn_fac_reset")
    assert vm.temp["rn_cv1_err"] == ERR_FEATURE_OFF
    assert vm.subject_state() == before
    return 2


def _flags() -> int:
    """The flag picker: no opening, and Apply and Restore refuse with 21.

    Returns:
        Number of cases.
    """
    inp = Inputs()
    vm = inp.vm()
    vm.rules["rn_feature_flag"] = _off("flag")
    open_own(vm)
    assert "rn_fp_open_own" not in vm.nations["FRA"].flags, "no opening while switched off"
    vm = inp.vm()
    vm.rules["rn_feature_subjects"] = _off("subjects")
    open_sub(vm, "POL")
    assert "rn_fp_open_sub" not in vm.nations["FRA"].flags
    for switch, target in (("flag", None), ("subjects", "POL")):
        vm = inp.vm()
        if target:
            open_sub(vm, target)
        else:
            open_own(vm)
        root = vm.nations["FRA"]
        root.vars["rn_fp_sel"] = Decimal(1)
        vm.rules[f"rn_feature_{switch}"] = _off(switch)
        capie(vm)
        vm.run("rn_fp_apply")
        assert root_err(vm) == ERR_FEATURE_OFF, switch
        assert layer(vm, target or "FRA") is None, switch
    vm = inp.vm()
    open_own(vm)
    vm.temp = {"rn_cf_in": Decimal(1)}
    vm.scoped("FRA", lambda: vm.run("rn_country_flag_carrier_set"))
    vm.rules["rn_feature_flag"] = _off("flag")
    vm.temp = {}
    vm.run("rn_fp_reset")
    assert root_err(vm) == ERR_FEATURE_OFF
    assert layer(vm, "FRA") is not None, "Restore refused: the layer stays"
    return 5


def _legacy(ctx: Context) -> int:
    """The legacy country Apply, Restore and the typed country buffers write nothing.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    vm = ctx.vm("country")
    vm.enforce = False
    vm.rules["rn_feature_country"] = _off("country")
    vm.persistent.update(rn_cname_len=Decimal(3), rn_cadj_len=Decimal(3))
    before = vm.state()
    vm.run("rn_apply_country_name")
    assert vm.state() == before
    vm.persistent["capie_cn_ver"] = Decimal(1)
    before = vm.state()
    vm.run("rn_reset_country_name")
    assert vm.state() == before
    return 2


def run_switch_cases(ctx: Context) -> int:
    """Run every switch VM case.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    return _politics(ctx) + _subjects(ctx) + _factions(ctx) + _flags() + _legacy(ctx)
