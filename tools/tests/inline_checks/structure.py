"""Structural checks: the parse trees of the source must match the expected contract."""

from __future__ import annotations

from typing import Any

from inline_checks.constants import (
    ERR_COOLDOWN,
    FIELD_LABELS,
    GROUP_KEYS,
    GROUPS,
    MAX_NAME,
    REASONS,
    REV_CAP,
    RULES_ICON_X,
    TITLE_LINE_BOTTOM,
)
from inline_checks.fixtures import VM_MODULE
from inline_checks.geometry import geometry_audit
from inline_checks.tree import get, named, success_if, then, tokens, walk, xy
from modgen.features.cooldown import COOLDOWN_DAYS


def check_models(models: dict[str, Any], triggers: dict[str, Any]) -> dict[str, Any]:
    """Check the model set, the subject placeholder and the per-model guards.

    Args:
        models: Source scripted GUI models.
        triggers: Source scripted triggers.

    Returns:
        The six politics models (without the subject placeholder).
    """
    assert set(models) == {
        "rn_ip_leader_launcher_gui",
        "rn_ip_leader_gui",
        "rn_ip_party_neutrality_launcher_gui",
        "rn_ip_party_neutrality_gui",
        "rn_ip_country_launcher_gui",
        "rn_ip_country_gui",
        "rn_ip_subject_gui",
    }
    subject = models["rn_ip_subject_gui"]
    assert get(subject, "context_type") == "diplomacy_target_context"
    assert ("rn_ip_subject_rename_enabled", "=", "yes") in get(subject, "visible")
    assert triggers["rn_ip_subject_rename_enabled"] == [("always", "=", "no")]
    assert triggers["rn_ip_subject_country_capability"] == [("always", "=", "no")]
    country_enabled = get(get(subject, "triggers"), "rn_ips_country_click_enabled")
    assert ("rn_ip_subject_country_capability", "=", "yes") in country_enabled
    assert all([k for k, _, _ in body] == ["log"] for _, _, body in get(subject, "effects"))
    politics = {k: v for k, v in models.items() if k != "rn_ip_subject_gui"}
    for name, body in politics.items():
        assert get(body, "context_type") == "player_context"
        assert get(body, "parent_window_token") == "politics_tab"
        assert get(body, "ai_enabled") == [("always", "=", "no")]
        assert ("rn_editor_bridge_available", "=", "yes") in get(body, "visible")
        enabled = [v for k, _, v in get(body, "triggers") if k.endswith("_enabled")]
        for branch in [get(body, "visible"), *enabled]:
            resolved = (
                triggers["rn_ipp_party_target_matches"]
                if branch == [("rn_ipp_party_target_matches", "=", "yes")]
                else branch
            )
            assert ("tag", "=", "ROOT") in resolved, ("own country guard", name)
            assert ("is_ai", "=", "no") in resolved, ("own country guard", name)
            assert not any(v == "POL" for _, _, v in walk(branch)), name
        for key, _, trig in get(body, "triggers"):
            if key.endswith("_apply_click_enabled"):
                symbols = tokens(trig) | {k for k, _, _ in walk(trig)}
                assert not any("temp_var:" in v or "rn_native_" in v for v in symbols)
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in get(body, "visible")
    return politics


def check_callbacks(models: dict[str, Any]) -> None:
    """Check the Open, Apply and Cancel callbacks and the caption revision counters.

    Args:
        models: The six politics models.
    """
    kinds = {
        "leader": ("rn_ip_leader", "rn_inline_leader", "rn_ip_lui_rev", "rn_ip_leader_error"),
        "party": ("rn_ip_party_neutrality", "rn_inline_pair", "rn_ip_pui_rev", "rn_pair_err"),
        "country": ("rn_ip_country", "rn_inline_pair", None, "rn_pair_err"),
    }
    for kind, (prefix, helper_prefix, rev, err) in kinds.items():
        editor = models[prefix + "_gui"]
        launcher = models[prefix + "_launcher_gui"]
        assert get(editor, "window_name") == prefix + "_window"
        assert get(launcher, "window_name") == prefix + "_launcher_window"
        suffix = "" if kind == "leader" else "_" + kind
        open_helper = f"{helper_prefix}_open{suffix}"
        cancel_helper = f"{helper_prefix}_cancel{suffix}"
        apply_helper = f"{helper_prefix}_apply{suffix}"
        status = "rn_ip_status_record_" + ("leader" if kind == "leader" else "pair")
        open_click = get(get(launcher, "effects"), prefix + "_open_click")
        cancel_click = get(get(editor, "effects"), prefix + "_cancel_click")
        apply_click = get(get(editor, "effects"), prefix + "_apply_click")
        assert cancel_click == [(cancel_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in get(
                get(launcher, "triggers"), prefix + "_open_click_enabled"
            )
        if rev is None:
            assert open_click == [(open_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
            assert [k for k, _, _ in apply_click] == ["log", apply_helper, status, "log"]
        else:
            # Caption revision counter: explicit 0 before the first opening, +1 only after a
            # successful Apply, capped at REV_CAP, hidden carriers in launcher and editor.
            init = ("if", "=", [("limit", "=", [("NOT", "=", [("has_variable", "=", rev)])])])
            assert open_click[0][:2] == init[:2]
            assert open_click[0][2][0] == init[2][0]
            assert open_click[1:] == [(open_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
            assert [k for k, _, _ in apply_click] == ["log", apply_helper, "if", status, "log"]
            assert apply_click[2] == (
                "if",
                "=",
                [
                    (
                        "limit",
                        "=",
                        [
                            ("check_variable", "=", [(f"temp_var:{err}", "=", "0")]),
                            ("check_variable", "=", [(rev, "<", str(REV_CAP))]),
                        ],
                    ),
                    ("add_to_variable", "=", [(rev, "=", "1")]),
                ],
            )
            for model in (editor, launcher):
                assert get(get(model, "triggers"), prefix + "_rev_visible") == [
                    ("always", "=", "no")
                ]
        assert "before" in apply_click[0][2]
        assert "after" in apply_click[-1][2]
        assert "PASS" not in apply_click[-1][2]
        cancel_enabled = get(get(editor, "triggers"), prefix + "_cancel_click_enabled")
        assert not any(k == "has_government" for k, _, _ in walk(cancel_enabled))


def check_exclusive_open(effects: dict[str, Any]) -> None:
    """Check that at most one in-place editor (one Enter target) can be open.

    Args:
        effects: Source scripted effects.
    """
    flags = ["rn_ip_leader_open", "rn_ip_country_open", "rn_ip_party_neutrality_open"]
    for helper, need in (
        ("rn_inline_pair_open_country", flags),
        ("rn_inline_pair_open_party", flags),
        ("rn_inline_leader_open", flags[:2]),
    ):
        limit = get(get(effects[helper], "if"), "limit")
        assert all(("NOT", "=", [("has_country_flag", "=", f)]) in limit for f in need), helper
    leader_open = list(walk(effects["rn_inline_leader_open"]))
    assert ("clr_country_flag", "=", "rn_ip_party_neutrality_open") in leader_open


def check_tabs(effects: dict[str, Any], party: list[Any]) -> None:
    """Check the party tab switch helper and the four tab buttons.

    Args:
        effects: Source scripted effects.
        party: The party editor model.
    """
    switch = get(effects["rn_inline_pair_switch_party"], "if")
    limit = get(switch, "limit")
    for need in (
        ("has_country_flag", "=", "rn_ip_party_neutrality_open"),
        ("NOT", "=", [("rn_ip_cooldown_active_party", "=", "yes")]),
        (
            "NOT",
            "=",
            [("check_variable", "=", [("rn_ip_party_group", "=", "temp_var:rn_ip_party_tab")])],
        ),
    ):
        assert need in limit, ("tab switch guard", need)
    assert then(switch) == [
        ("clear_array", "=", "rn_ip_party_target"),
        ("add_to_array", "=", [("rn_ip_party_target", "=", "THIS")]),
        ("set_variable", "=", [("rn_ip_party_group", "=", "temp_var:rn_ip_party_tab")]),
        ("add_to_variable", "=", [("rn_ip_epoch", "=", "1")]),
    ], "tab switch = re-pin + group + new epoch only"
    for i, _ in GROUPS:
        assert get(get(party, "effects"), f"rn_ipp_tab_{i}_click") == [
            ("set_temp_variable", "=", [("rn_ip_party_tab", "=", str(i))]),
            ("rn_inline_pair_switch_party", "=", "yes"),
            ("rn_ip_status_clear", "=", "yes"),
        ]
        enabled = get(get(party, "triggers"), f"rn_ipp_tab_{i}_click_enabled")
        assert ("NOT", "=", [("check_variable", "=", [("rn_ip_party_group", "=", str(i))])]) in (
            enabled
        )
        assert ("has_country_flag", "=", "rn_ip_party_neutrality_open") in enabled


def group_gate(nodes: list[Any]) -> None:
    """Check the pinned-group gate: groups 1..4, no government condition.

    Args:
        nodes: Trigger or guard body.
    """
    want = (
        "OR",
        "=",
        [("check_variable", "=", [("rn_ip_party_group", "=", str(i))]) for i, _ in GROUPS],
    )
    assert list(walk(nodes)).count(want) == 1, "missing or different exact pinned-group gate"
    assert not any(k == "has_government" for k, _, _ in walk(nodes)), "any base group is allowed"


def check_guards(effects: dict[str, Any], triggers: dict[str, Any]) -> None:
    """Check the guards and the two-round Apply structure of the three editors.

    Args:
        effects: Source scripted effects plus the legacy mod effects.
        triggers: Source scripted triggers.
    """
    group_gate(triggers["rn_ipp_party_target_matches"])
    group_gate(effects["rn_inline_pair_guard_party"])
    for kind in ("party", "country", "leader"):
        name = "rn_inline_leader_guard" if kind == "leader" else "rn_inline_pair_guard_" + kind
        guard = list(walk(effects[name]))
        VM_MODULE.pure_audit(effects, name)
        assert ("tag", "=", "ROOT") in guard
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in guard
        assert ("check_variable", "=", [("temp_var:rn_ip_cmd_epoch", "=", "rn_ip_epoch")]) in guard
        assert ("check_variable", "=", [("rn_ip_epoch", ">", "0")]) in guard
        assert any(k == "round_temp_variable" for k, _, _ in guard)
    for kind in ("party", "country"):
        body = effects["rn_inline_pair_apply_" + kind]
        assert body[0] == ("rn_inline_pair_guard_" + kind, "=", "yes")
        first = success_if(body)
        assert first[0] == ("rn_inline_pair_validate", "=", "yes")
        second = success_if(first)
        assert second[0] == body[0]
        if kind == "party":
            check_party_branches(success_if(second))
    leader = effects["rn_inline_leader_apply"]
    assert leader[0] == ("rn_inline_leader_guard", "=", "yes")
    first = success_if(leader)
    assert first[:2] == [
        ("rn_inline_validate_payload", "=", "yes"),
        ("set_temp_variable", "=", [("rn_ip_leader_error", "=", "temp_var:rn_inline_error")]),
    ]
    second = success_if(first)
    assert second[0] == leader[0]
    final = success_if(second)
    assert final[1] == ("rn_inline_leader_refresh", "=", "yes")
    assert ("check_variable", "=", [("rn_ip_leader_current^num", "=", "1")]) in list(walk(final))
    assert len([n for n in walk(leader) if n[0] == "set_character_name"]) == 1
    assert not any(v == "POL" or v.startswith("POL_") for b in effects.values() for v in tokens(b))
    copies = [
        n for b in effects.values() for n in walk(b) if n[0] == "rn_inline_party_copy_validated"
    ]
    assert len(copies) == len(GROUPS)


def check_party_branches(final: list[Any]) -> None:
    """Check the four literal ``set_party_name`` branches of the party Apply.

    Args:
        final: Body after the second guard round.
    """
    branches = [v for k, _, v in final if k in {"if", "else_if"}]
    assert len(branches) == len(GROUPS)
    for branch, (i, group) in zip(branches, GROUPS, strict=True):
        assert get(branch, "limit") == [
            ("check_variable", "=", [("rn_ip_party_group", "=", str(i))])
        ]
        commands = then(branch)
        assert [k for k, _, _ in commands] == [
            "rn_inline_party_copy_validated",
            "meta_effect",
            "rn_inline_party_finish",
        ]
        setter = get(get(commands[1][2], "text"), "set_party_name")
        assert setter == [("ideology", "=", group), ("name", "=", "[S]"), ("long_name", "=", "[L]")]
        for token, prefix in (("S", "PS"), ("L", "PL")):
            want = "".join(f"[ROOT.RN_{prefix}_{slot}]" for slot in range(MAX_NAME))
            assert get(commands[1][2], token) == want


def check_status(
    effects: dict[str, Any], models: dict[str, Any], triggers: dict[str, Any], locs: dict[str, Any]
) -> None:
    """Check the status-line branches and that status variables stay display-only.

    Args:
        effects: Source scripted effects.
        models: The six politics models.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    party_status = [n for n in locs["RN_IPP_PARTY_STATUS"] if n[0] == "text"]
    assert [get(t[2], "localization_key") for t in party_status] == [
        "RN_IP_ERR_NO_BRIDGE",
        "RN_IP_ERR_NO_COUNTER",
        "RN_IP_ERR_RENAME_LIMIT",
        "RN_IP_ERR_CD_PARTY",
        *(f"RN_IP_ERR_PARTY_SHORT_{r}" for r in REASONS),
        "RN_IP_ERR_PARTY_SHORT",
        "RN_IP_ERR_PARTY_LONG_EMPTY",
        "RN_IP_ERR_PARTY_LONG_LONG",
        "RN_IP_ERR_PARTY_LONG_UNKNOWN",
        "RN_IP_ERR_PARTY_LONG_CHAR",
        "RN_IP_ERR_PARTY_LONG",
        "RN_IP_HINT",
        "RN_IPP_LONG_UNKNOWN",
        "RN_IPP_TARGET_CHANGED",
    ]
    assert all(
        ("rn_ipp_party_target_matches", "=", "yes") in get(t[2], "trigger")
        # NO_BRIDGE and the two cause-coded refusals apply to any target; so does the last line.
        for t in party_status[3:-1]
    )
    assert [get(t[2], "localization_key") for t in locs["RN_IP_STATUS"] if t[0] == "text"] == [
        "RN_IP_HINT",
        "RN_IP_ERR_NO_BRIDGE",
        "RN_IP_ERR_NO_COUNTER",
        "RN_IP_ERR_RENAME_LIMIT",
        "RN_IP_ERR_CD_LEADER",
        "RN_IP_ERR_CD_COUNTRY",
        "RN_IP_ERR_STALE",
        *(f"RN_IP_ERR_LEADER_{r}" for r in REASONS),
        "RN_IP_ERR_LEADER",
        *(f"RN_IP_ERR_COUNTRY_ADJ_{r}" for r in REASONS),
        "RN_IP_ERR_COUNTRY_ADJ",
        *(f"RN_IP_ERR_COUNTRY_NAME_{r}" for r in REASONS),
        "RN_IP_ERR_COUNTRY_NAME",
    ]
    for name, body in effects.items():
        if not name.startswith("rn_ip_status_"):
            assert not any("rn_ip_status_" in str(n) for n in walk(body)), ("status read", name)
    for name, body in triggers.items():
        assert not any("rn_ip_status_" in str(n) for n in walk(body)), name
    for name, body in models.items():
        for key, _, trig in get(body, "triggers"):
            assert not any("rn_ip_status_" in str(n) for n in walk(trig)), (name, key)


def check_party_carriers(locs: dict[str, Any]) -> None:
    """Check the short and long party carriers (I4-M1 placeholder for non-ruling groups).

    Args:
        locs: Source scripted localisation.
    """
    for name, ruling in (
        ("RN_IPP_PARTY_SHORT", "RN_IPP_PARTY_SHORT_CURRENT"),
        ("RN_IPP_PARTY_LONG", "RN_IPP_PARTY_LONG_CURRENT"),
    ):
        texts = [n[2] for n in locs[name] if n[0] == "text"]
        matches = ("rn_ipp_party_target_matches", "=", "yes")
        want = [
            [
                (
                    "trigger",
                    "=",
                    [
                        matches,
                        ("check_variable", "=", [("rn_ip_party_group", "=", str(i))]),
                        ("has_government", "=", g),
                    ],
                ),
                ("localization_key", "=", ruling),
            ]
            for i, g in GROUPS
        ]
        for i, _ in GROUPS:
            key = (
                "RN_IPP_PARTY_SHORT_" + GROUP_KEYS[i - 1]
                if name == "RN_IPP_PARTY_SHORT"
                else "RN_IPP_LONG_PLACEHOLDER"
            )
            group = ("check_variable", "=", [("rn_ip_party_group", "=", str(i))])
            want.append([("trigger", "=", [matches, group]), ("localization_key", "=", key)])
        want.append([("localization_key", "=", "RN_IPP_EMPTY")])
        assert texts == want, ("party carrier branches", name)


def check_cooldown(
    effects: dict[str, Any], models: dict[str, Any], triggers: dict[str, Any], locs: dict[str, Any]
) -> None:
    """Check the single constant, the guards, the start points and the pencil gates.

    Args:
        effects: Source scripted effects.
        models: The six politics models.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    constants = [
        n
        for body in effects.values()
        for n in walk(body)
        if n[0] == "set_temp_variable" and n[2][0][0] == "rn_ip_cd_days"
    ]
    assert len(constants) == 1
    assert effects["rn_ip_cooldown_days"] == [
        ("set_temp_variable", "=", [("rn_ip_cd_days", "=", str(COOLDOWN_DAYS))])
    ]
    starters = {
        "country": "rn_inline_pair_apply_country",
        "leader": "rn_inline_leader_apply",
        "party": "rn_inline_party_finish",
    }
    openers = {
        "country": "rn_inline_pair_open_country",
        "leader": "rn_inline_leader_open",
        "party": "rn_inline_pair_open_party",
    }
    prefixes = {
        "country": "rn_ip_country",
        "leader": "rn_ip_leader",
        "party": "rn_ip_party_neutrality",
    }
    for k in ("country", "leader", "party"):
        active = f"rn_ip_cooldown_active_{k}"
        assert triggers[active] == [
            ("set_temp_variable", "=", [("rn_ip_cd_left", "=", f"rn_ip_cd_{k}_until")]),
            ("subtract_from_temp_variable", "=", [("rn_ip_cd_left", "=", "global.num_days")]),
            ("check_variable", "=", [("rn_ip_cd_left", ">", "0")]),
        ]
        start = effects[f"rn_ip_cooldown_start_{k}"]
        assert ("set_variable", "=", [(f"rn_ip_cd_{k}_until", "=", "global.num_days")]) in start
        guard = effects["rn_inline_leader_guard" if k == "leader" else "rn_inline_pair_guard_" + k]
        err = "rn_ip_leader_error" if k == "leader" else "rn_pair_err"
        assert guard[-1] == (
            "if",
            "=",
            [
                (
                    "limit",
                    "=",
                    [
                        ("check_variable", "=", [(f"temp_var:{err}", "=", "0")]),
                        (active, "=", "yes"),
                    ],
                ),
                ("set_temp_variable", "=", [(err, "=", str(ERR_COOLDOWN))]),
            ],
        ), ("cooldown guard", k)
        callers = [
            n
            for n, b in effects.items()
            if any(x[0] == f"rn_ip_cooldown_start_{k}" for x in walk(b))
        ]
        assert callers == [starters[k]], ("start callers", k, callers)
        assert ("NOT", "=", [(active, "=", "yes")]) in get(get(effects[openers[k]], "if"), "limit")
        launcher = models[prefixes[k] + "_launcher_gui"]
        enabled = get(get(launcher, "triggers"), prefixes[k] + "_open_click_enabled")
        assert ("NOT", "=", [(active, "=", "yes")]) in enabled, ("pencil not disabled", k)
        assert active not in str(get(launcher, "visible")), "pencil must stay visible"
        days = [
            get(x[2], "localization_key")
            for x in locs[f"RN_IP_CD_LEFT_{k.upper()}"]
            if x[0] == "text"
        ]
        assert days == [f"RN_IP_CD_DAYS_{n}" for n in range(1, 31)] + ["RN_IP_CD_DAYS_MORE"]
    tail = next(v for key, _, v in reversed(effects["rn_inline_leader_apply"]) if key == "if")
    assert get(tail, "limit") == [
        ("check_variable", "=", [("temp_var:rn_ip_leader_error", "=", "0")])
    ]
    assert ("rn_ip_cooldown_start_leader", "=", "yes") in tail


def check_widgets(gui: list[Any]) -> None:
    """Check fields, carriers, labels and run the geometry audit.

    Args:
        gui: Parsed source GUI files.
    """
    fields = {
        "rn_ip_leader_edit",
        "rn_ip_party_neutrality_edit",
        "rn_ip_party_neutrality_long_edit",
        "rn_ip_country_name_edit",
        "rn_ip_country_adj_edit",
    }
    assert {get(body, "name") for kind, _, body in walk(gui) if kind == "editBoxType"} == fields
    widgets = named(gui)
    label = widgets["rn_ip_country_label"]
    assert get(label, "font") == "hoi_18mbs"
    assert get(label, "format") == "right"
    assert get(label, "text") == "[ROOT.GetName]"
    lx, ly = xy(widgets["rn_ip_country_launcher_window"])
    bx, by = xy(widgets["rn_ip_country_open"])
    assert ly + by + 20 <= TITLE_LINE_BOTTOM
    assert lx + xy(label)[0] + int(get(label, "maxWidth")) <= lx + bx
    assert lx + bx + 20 <= RULES_ICON_X
    for kind in ("leader", "party_neutrality", "country"):
        assert get(widgets[f"rn_ip_{kind}_epoch"], "text") == "[?ROOT.rn_ip_epoch|0]"
    assert get(widgets["rn_ip_party_neutrality_prefill"], "text") == "[ROOT.RN_IPP_PARTY_SHORT]"
    assert get(widgets["rn_ip_party_neutrality_long_prefill"], "text") == "[ROOT.RN_IPP_PARTY_LONG]"
    statuses = {
        "rn_ip_leader_status": "[ROOT.RN_IP_STATUS]",
        "rn_ip_country_status": "[ROOT.RN_IP_STATUS]",
        "rn_ip_party_neutrality_status": "[ROOT.RN_IPP_PARTY_STATUS]",
    }
    for status, text in statuses.items():
        assert get(widgets[status], "text") == text
        assert get(widgets[status], "font") == "Arial12"
    for label, text in FIELD_LABELS.items():
        assert get(widgets[label], "text") == text, label
        assert get(widgets[label], "font") == "Arial12", label
    revs = [
        b for k, _, b in walk(gui) if k == "instantTextboxType" and get(b, "name").endswith("_rev")
    ]
    assert (
        sorted(get(b, "text") for b in revs)
        == ["[?ROOT.rn_ip_lui_rev|0]"] * 2 + ["[?ROOT.rn_ip_pui_rev|0]"] * 2
    ), "caption counter carriers in both launchers and editors"
    geometry_audit(gui)


def structural(
    effects: dict[str, Any],
    models: dict[str, Any],
    gui: list[Any],
    triggers: dict[str, Any],
    locs: dict[str, Any],
) -> None:
    """Run every structural check on one set of parse trees.

    Args:
        effects: Source effects plus the legacy mod effects.
        models: Source scripted GUI models.
        gui: Parsed source GUI files.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    own = {
        k: v
        for k, v in effects.items()
        if not k.startswith(("rn_cd_", "rn_apply_", "rn_open_", "rn_close_"))
    }
    politics = check_models(models, triggers)
    check_callbacks(politics)
    check_exclusive_open(effects)
    check_tabs(effects, politics["rn_ip_party_neutrality_gui"])
    assert not any(
        k == "has_government"
        for k, _, _ in walk(get(politics["rn_ip_party_neutrality_gui"], "visible"))
    )
    check_guards(effects, triggers)
    check_status(own, politics, triggers, locs)
    check_cooldown(own, politics, triggers, locs)
    check_party_carriers(locs)
    check_widgets(gui)
