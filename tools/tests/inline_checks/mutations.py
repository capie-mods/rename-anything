"""Contract mutations: broken copies of the parse trees that the structural checks must reject."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from inline_checks.tree import get, named, set_value

if TYPE_CHECKING:
    from collections.abc import Callable
from inline_checks.structure import structural


def contract_mutations() -> dict[
    str, Callable[[dict[str, Any], dict[str, Any], list[Any], dict[str, Any], dict[str, Any]], None]
]:
    """Return named mutations of the parse trees that the structural checks must reject.

    Returns:
        Mutation name to a function taking (effects, models, gui, triggers, locs).
    """

    def long_from_short(
        _e: dict[str, Any],
        _m: dict[str, Any],
        _g: list[Any],
        _t: dict[str, Any],
        loc: dict[str, Any],
    ) -> None:
        """Make a non-ruling long carrier fall back to the short name again.

        Args:
            _e: Effects (unused).
            _m: Models (unused).
            _g: GUI tree (unused).
            _t: Triggers (unused).
            loc: Scripted localisation, changed in place.
        """
        node = next(
            t
            for t in loc["RN_IPP_PARTY_LONG"]
            if t[0] == "text" and ("localization_key", "=", "RN_IPP_LONG_PLACEHOLDER") in t[2]
        )
        set_value(node[2], "localization_key", "RN_IPP_PARTY_SHORT_DEMOCRATIC")

    return {
        "partial group gate": lambda _e, _m, _g, t, _l: get(
            t["rn_ipp_party_target_matches"], "OR"
        ).pop(),
        "ctor temp enabled": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_country_gui"], "triggers"), "rn_ip_country_apply_click_enabled"
        ).append(("check_variable", "=", [("temp_var:rn_native_cap", "=", "1")])),
        "country geometry": lambda _e, _m, g, _t, _l: set_value(
            named(g)["rn_ip_country_window"], "size", [("width", "=", "420"), ("height", "=", "40")]
        ),
        "cancel under apply": lambda _e, _m, g, _t, _l: set_value(
            named(g)["rn_ip_leader_cancel"], "position", [("x", "=", "380"), ("y", "=", "5")]
        ),
        "missing enter": lambda _e, _m, g, _t, _l: named(g)["rn_ip_party_neutrality_apply"].remove(
            ("shortcut", "=", "RETURN")
        ),
        "narrow field": lambda _e, _m, g, _t, _l: set_value(
            named(g)["rn_ip_country_adj_edit"], "size", [("x", "=", "176"), ("y", "=", "20")]
        ),
        "status in guard": lambda _e, _m, _g, t, _l: t["rn_ipp_party_target_matches"].append(
            ("has_variable", "=", "rn_ip_status_err")
        ),
        "pencil ignores cooldown": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_party_neutrality_launcher_gui"], "triggers"),
            "rn_ip_party_neutrality_open_click_enabled",
        ).remove(("NOT", "=", [("rn_ip_cooldown_active_party", "=", "yes")])),
        "cooldown on reject": lambda e, _m, _g, _t, _l: e["rn_inline_pair_cancel_party"].append(
            ("rn_ip_cooldown_start_party", "=", "yes")
        ),
        "escape back": lambda _e, _m, g, _t, _l: named(g)["rn_ip_leader_cancel"].append(
            ("shortcut", "=", "ESCAPE")
        ),
        "government gate back": lambda _e, _m, _g, t, _l: t["rn_ipp_party_target_matches"].append(
            ("has_government", "=", "neutrality")
        ),
        "tab writes name": lambda e, _m, _g, _t, _l: get(
            e["rn_inline_pair_switch_party"], "if"
        ).append(("rn_inline_party_finish", "=", "yes")),
        "unscaled icon": lambda _e, _m, g, _t, _l: named(g)["rn_ip_party_neutrality_open"].remove(
            ("scale", "=", "0.67")
        ),
        "raw party carrier": lambda _e, _m, g, _t, _l: set_value(
            named(g)["rn_ip_party_neutrality_prefill"], "text", "[ROOT.GetRulingParty]"
        ),
        "short as long prefill": long_from_short,
        "bridge gate removed": lambda _e, m, _g, _t, _l: get(
            m["rn_ip_leader_gui"], "visible"
        ).remove(("rn_editor_bridge_available", "=", "yes")),
        "counter without success": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_leader_gui"], "effects"), "rn_ip_leader_apply_click"
        )[2][2][0][2].pop(0),
    }


def run_mutations(
    effects: dict[str, Any],
    models: dict[str, Any],
    gui: list[Any],
    triggers: dict[str, Any],
    locs: dict[str, Any],
) -> int:
    """Apply every contract mutation to copies and require a structural failure.

    Args:
        effects: Source effects plus the legacy mod effects.
        models: Source scripted GUI models.
        gui: Parsed source GUI files.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.

    Returns:
        Number of rejected mutations.

    Raises:
        AssertionError: A mutation was not rejected.
    """
    rejected = 0
    for name, mutate in contract_mutations().items():
        copies = copy.deepcopy((effects, models, gui, triggers, locs))
        mutate(*copies)
        try:
            structural(*copies)
        except AssertionError:
            rejected += 1
        else:
            msg = f"negative contract mutation survived: {name}"
            raise AssertionError(msg)
    return rejected
