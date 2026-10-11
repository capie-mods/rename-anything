"""Cities tab: the victory point (VP) provinces of one selected state.

A state scope cannot be compared with a numeric ID in HOI4 script, so
``rn_load_selected_state`` resolves the selected state with one ``state = <id>``
branch per vanilla state and stores the literal ID and up to
:data:`~modgen.common.VP_SLOTS` VP provinces on the player country. The VP names
are then looked up in two levels: by state-ID bucket
(:data:`~modgen.common.STATE_BUCKET` IDs per bucket), then by exact state ID.

No localisation getter returns a province's custom name, so the codes applied by
``set_province_name`` are also kept on the state (``rn_vpn_<k>``) and copied to
ROOT (``rn_vpc_<k>``) when the Cities tab loads a state. A row then reads
"Original (now New)". Names changed before this existed are not known.
"""

from __future__ import annotations

from modgen.common import (
    EMPTY_LOC_KEY,
    PROVINCE_DIGITS,
    STATE_BUCKET,
    TAB_CITIES,
    VP_SLOTS,
    StateTable,
    bucket_has_slot,
    slots_expr,
    state_buckets,
)
from modgen.features.main_window import DynamicList, TabSpec
from modgen.features.text_buffers import NameBuffer
from modgen.gui import BUTTON_SMALL, WINDOW_END, btn, entry_window, gridbox, txt
from modgen.script import check_variable, defined_text

VP_NAME_BUFFERS = [NameBuffer(f"VC{k}", f"rn_vpc_{k}", f"rn_vpc_{k}_len") for k in range(VP_SLOTS)]
"""Cities rows: ROOT copies of the names applied here, one buffer per VP slot."""

VP_ROW_PITCH = 44
"""Vertical distance between two VP rows on the Cities tab."""

VP_ROWS_Y = 86
"""Offset of the first VP row below the start of the tab content."""

SELECTED_STATE_WIDTH = 420
"""Width of the one-row grid that shows the selected state's name."""

SELECTED_STATE_HEIGHT = 30
"""Height of that grid and of its row."""

DECIMAL_BASE = 10
"""Base of the province ID digits."""


def vp_key(province: int, keys: set[int]) -> str:
    """Return the localisation key that names a VP province.

    Args:
        province: Province ID.
        keys: Province IDs that have a vanilla ``VICTORY_POINTS_<id>`` key.

    Returns:
        The vanilla key if it exists, otherwise the generated ``RN_PROVNAME_<id>``.
    """
    return f"VICTORY_POINTS_{province}" if province in keys else f"RN_PROVNAME_{province}"


def province_expr() -> str:
    """Return the localisation text that prints the target province ID.

    Returns:
        ``[ROOT.RN_PD_0]`` through ``[ROOT.RN_PD_4]`` concatenated.
    """
    return "".join(f"[ROOT.RN_PD_{k}]" for k in range(PROVINCE_DIGITS))


def province_digit_loc() -> str:
    """Return the ``RN_PD_<k>`` tables that print the target province ID digit by digit.

    Leading zeros are suppressed: digit ``k`` prints nothing while the province ID
    is below ``10 ** (PROVINCE_DIGITS - 1 - k)``. The last digit always prints.

    Returns:
        One ``defined_text`` per digit.
    """
    out = []
    for k in range(PROVINCE_DIGITS):
        branches = []
        if k < PROVINCE_DIGITS - 1:
            limit = DECIMAL_BASE ** (PROVINCE_DIGITS - 1 - k)
            branches.append((check_variable(f"rn_tprov < {limit}"), EMPTY_LOC_KEY))
        branches.extend(
            (check_variable(f"rn_pd_{k} = {d}"), f"RN_DIG_{d}") for d in range(DECIMAL_BASE)
        )
        out.append(defined_text(f"RN_PD_{k}", branches, "RN_DIG_0"))
    return "".join(out)


def vp_name_loc(states: StateTable, keys: set[int]) -> str:
    """Return the two-level VP name lookup and the target province name.

    Args:
        states: State table.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        ``RN_VpName_<k>`` (by bucket), ``RN_VpName_<k>_<bucket>`` (by state ID) for
        every slot, then ``RN_TProvName``.
    """
    buckets = state_buckets(states)
    out = []
    for k in range(VP_SLOTS):
        out.append(
            defined_text(
                f"RN_VpName_{k}",
                [
                    (
                        check_variable(f"rn_sel_state_id < {(b + 1) * STATE_BUCKET}"),
                        f"RN_VPB_{k}_{b}",
                    )
                    for b in buckets
                    if bucket_has_slot(states, b, k)
                ],
                EMPTY_LOC_KEY,
            )
        )
        for b in buckets:
            items = [(s, v[k]) for s, v in states.items() if s // STATE_BUCKET == b and len(v) > k]
            if not items:
                continue
            out.append(
                defined_text(
                    f"RN_VpName_{k}_{b}",
                    [(check_variable(f"rn_sel_state_id = {s}"), vp_key(p, keys)) for s, p in items],
                    EMPTY_LOC_KEY,
                )
            )
    out.append(
        defined_text(
            "RN_TProvName",
            [(check_variable(f"rn_tslot = {k}"), f"RN_TPROV_{k}") for k in range(VP_SLOTS)],
            EMPTY_LOC_KEY,
        )
    )
    return "".join(out)


def vp_row_loc() -> str:
    """Return the ``RN_VpRow_<k>`` rows: "Original (now New)" when a name is stored.

    Returns:
        One ``defined_text`` per VP slot.
    """
    return "".join(
        defined_text(
            f"RN_VpRow_{k}",
            [(check_variable(f"rn_vpc_{k}_len > 0"), f"RN_VPROW_NOW_{k}")],
            f"RN_TPROV_{k}",
        )
        for k in range(VP_SLOTS)
    )


def load_selected_state_effect(states: StateTable) -> str:
    """Return ``rn_load_selected_state``: state scope to literal ID and VP slots.

    CURRENT is the selected state; ROOT is the player country. A typed state
    variable (including ``THIS.id``) cannot be compared to ordinary numeric IDs,
    so the effect resolves the state by trigger and assigns a numeric literal,
    loading the VPs in the same pass. It runs when the Cities tab opens or a
    state is selected, never once per frame.

    Args:
        states: State table, including states without VPs.

    Returns:
        The effect with its comment line, followed by a blank line.
    """
    out = [
        (
            "# State scope -> literal numeric ID and VP slots on ROOT (player). "
            "Includes states without VPs.\n"
        ),
        "rn_load_selected_state = {\n",
    ]
    for i, (s, vps) in enumerate(states.items()):
        kw = "if" if i == 0 else "else_if"
        sets = "".join(f" set_variable = {{ rn_vp_{k} = {p} }}" for k, p in enumerate(vps))
        out.append(
            f"\t{kw} = {{ limit = {{ state = {s} }} ROOT = {{ "
            f"set_variable = {{ rn_sel_state_id = {s} }} "
            f"set_variable = {{ rn_vp_cnt = {len(vps)} }}{sets} }} }}\n"
        )
    out.append("\trn_vp_names_to_root = yes\n}\n\n")
    return "".join(out)


def vp_name_effects() -> str:
    """Return the effects that keep the city names applied by this mod.

    ``set_province_name`` leaves no trace that localisation can read, so the
    applied codes are also stored on the state, one array per VP slot
    (``rn_vpn_<k>`` and ``rn_vpn_<k>_len``). ``rn_vp_names_to_root`` copies them
    to ROOT (``rn_vpc_<k>``) for the Cities rows, which print them through the
    ``RN_VC<k>_<i>`` buffers.

    Returns:
        The ``rn_vp_store_name``, ``rn_vp_forget_name`` and ``rn_vp_names_to_root``
        effects (all in STATE scope; ROOT is the player country).
    """
    o = [
        (
            "# City names applied here, kept per VP slot on the STATE (no getter returns a\n"
            "# custom province name). STATE scope; ROOT.rn_tslot is the slot and ROOT.rn_buf\n"
            "# holds the applied codes.\n"
            "rn_vp_store_name = {\n"
        )
    ]
    o.extend(
        f"\tif = {{ limit = {{ check_variable = {{ ROOT.rn_tslot = {k} }} }}\n"
        f"\t\tclear_array = rn_vpn_{k}\n"
        "\t\tfor_each_loop = { array = ROOT.rn_buf value = rn_v"
        f" add_to_array = {{ rn_vpn_{k} = rn_v }} }}\n"
        f"\t\tset_variable = {{ rn_vpn_{k}_len = ROOT.rn_len }}\n\t}}\n"
        for k in range(VP_SLOTS)
    )
    o.append("}\n# Reset of a city name: forget the stored codes of slot ROOT.rn_tslot.\n")
    o.append("rn_vp_forget_name = {\n")
    o.extend(
        f"\tif = {{ limit = {{ check_variable = {{ ROOT.rn_tslot = {k} }} }}"
        f" clear_array = rn_vpn_{k} clear_variable = rn_vpn_{k}_len }}\n"
        for k in range(VP_SLOTS)
    )
    o.append("}\n# Copy this state's stored names to ROOT for the Cities rows.\n")
    o.append("rn_vp_names_to_root = {\n")
    o.extend(
        f"\tROOT = {{ clear_array = rn_vpc_{k} set_variable = {{ rn_vpc_{k}_len = 0 }} }}\n"
        f"\tfor_each_loop = {{ array = rn_vpn_{k} value = rn_v"
        f" add_to_array = {{ array = ROOT.rn_vpc_{k} value = rn_v }} }}\n"
        f"\tif = {{ limit = {{ has_variable = rn_vpn_{k}_len }}"
        f" ROOT = {{ set_variable = {{ rn_vpc_{k}_len = PREV.rn_vpn_{k}_len }} }} }}\n"
        for k in range(VP_SLOTS)
    )
    o.append("}\n\n")
    return "".join(o)


def reset_vp_effect() -> str:
    """Return ``rn_reset_vp``, which clears a city name override.

    This also works for VPs without a vanilla localisation key.

    Returns:
        The effect with its comment line.
    """
    return f"""# Reset a city (VP province) name by clearing the override. This also works for VPs without a loc key.
rn_reset_vp = {{ # temp rn_k = slot
	rn_target_vp = yes
	if = {{
		limit = {{ check_variable = {{ rn_tprov > 0 }} }}
		for_each_scope_loop = {{
			array = rn_tstate
			if = {{
				limit = {{ is_owned_by = ROOT }}
				meta_effect = {{
					text = {{ reset_province_name = [P] }}
					P = "{province_expr()}"
				}}
				rn_vp_forget_name = yes
				rn_vp_names_to_root = yes
			}}
		}}
	}}
}}
"""  # noqa: E501 - generated script lines are emitted verbatim


def _effects() -> str:
    """Return the per-slot Rename and Reset click effects of the Cities tab.

    Returns:
        Scripted GUI effect lines.
    """
    return "".join(
        f"\t\t\trn_vp_rename_{k}_click = {{ set_temp_variable = {{ rn_k = {k} }}"
        " rn_target_vp = yes rn_open_input = yes }\n"
        f"\t\t\trn_vp_reset_{k}_click = {{ set_temp_variable = {{ rn_k = {k} }}"
        " rn_reset_vp = yes }\n"
        for k in range(VP_SLOTS)
    )


def _triggers() -> str:
    """Return the Cities tab triggers: row visibility, Reset and cooldown-gated Rename.

    Renaming a city is disabled (not hidden) during the city cooldown.

    Returns:
        Scripted GUI trigger lines.
    """
    visible = "".join(
        f"\t\t\t{el}_{k}_visible = {{ check_variable = {{ rn_vp_cnt > {k} }} }}\n"
        for k in range(VP_SLOTS)
        for el in ("rn_vp_name", "rn_vp_rename", "rn_vp_reset")
    )
    reset = "".join(
        f"\t\t\trn_vp_reset_{k}_click_enabled = {{ check_variable = {{ rn_vp_cnt > {k} }} }}\n"
        for k in range(VP_SLOTS)
    )
    rename = "".join(
        f"\t\t\trn_vp_rename_{k}_click_enabled = {{ check_variable = {{ rn_vp_cnt > {k} }}"
        " NOT = { rn_cd_vp_active = yes } }\n"
        for k in range(VP_SLOTS)
    )
    no_cities = "\t\t\trn_no_cities_visible = { NOT = { check_variable = { rn_vp_cnt > 0 } } }\n"
    return no_cities + visible + reset + rename


def _elements(y0: int) -> tuple[str, ...]:
    """Return the elements of the Cities tab.

    Args:
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    o = [
        txt("rn_sel_state_lbl", 20, y0 + 8, "RN_SEL_STATE_LBL", w=100),
        gridbox(
            "rn_selstate_grid",
            (110, y0 + 4),
            (SELECTED_STATE_WIDTH, SELECTED_STATE_HEIGHT),
            SELECTED_STATE_HEIGHT,
        ),
        txt("rn_cities_hint", 20, y0 + 38, "RN_CITIES_HINT", w=520, h=40),
        txt("rn_no_cities", 20, y0 + 90, "RN_NO_CITIES", w=520),
    ]
    for k in range(VP_SLOTS):
        y = y0 + VP_ROWS_Y + k * VP_ROW_PITCH
        o.append(
            txt(
                f"rn_vp_name_{k}",
                20,
                y + 2,
                f"RN_VPROW_{k}",
                w=300,
                h=40,
                extra=" vertical_alignment = center",
            )
        )
        o.append(
            btn(
                f"rn_vp_rename_{k}",
                330,
                y + 2,
                BUTTON_SMALL,
                text="RN_BTN_RENAME",
                tooltip="RN_CD_VP_TT",
            )
        )
        o.append(btn(f"rn_vp_reset_{k}", 430, y + 2, BUTTON_SMALL, text="RN_BTN_RESET"))
    o.append(txt("rn_cities_note", 20, y0 + 314, "RN_CITIES_NOTE", w=520, h=60))
    return tuple(o)


def tab(content_y: int) -> TabSpec:
    """Return the Cities tab.

    Args:
        content_y: Y position where tab content starts.

    Returns:
        The tab specification.
    """
    return TabSpec(
        TAB_CITIES,
        "cities",
        _effects(),
        _triggers(),
        _elements(content_y),
        DynamicList(
            "rn_selstate_grid",
            "rn_sel_state_arr",
            "rn_selstate_entry",
            "\t\t\t\tchange_scope = yes",
        ),
    )


def list_entry() -> list[str]:
    """Return the row template that shows the selected state's name.

    Returns:
        GUI blocks of the ``rn_selstate_entry`` window.
    """
    return [
        entry_window("rn_selstate_entry", SELECTED_STATE_WIDTH, SELECTED_STATE_HEIGHT),
        txt("rn_selstate_name", 0, 4, "RN_TARGET_ENTRY", w=410),
        WINDOW_END,
    ]


def chars_loc_entries(states: StateTable) -> list[str]:
    """Return the language-independent VP name indirections of the Cities tab.

    Args:
        states: State table.

    Returns:
        ``RN_VPB``, ``RN_TPROV`` and ``RN_VPROW`` lines, slot by slot.
    """
    buckets = state_buckets(states)
    out: list[str] = []
    for k in range(VP_SLOTS):
        out.extend(
            f' RN_VPB_{k}_{b}: "[ROOT.RN_VpName_{k}_{b}]"\n'
            for b in buckets
            if bucket_has_slot(states, b, k)
        )
        out.append(f' RN_TPROV_{k}: "[ROOT.RN_VpName_{k}]"\n')
        out.append(f' RN_VPROW_{k}: "[ROOT.RN_VpRow_{k}]"\n')
    return out


def missing_name_entries(states: StateTable, keys: set[int]) -> list[str]:
    """Return ``RN_PROVNAME_<id>`` lines for VP provinces without a vanilla name.

    Args:
        states: State table.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        One ``#<id>`` line per unnamed province, sorted by ID.
    """
    missing = sorted({p for v in states.values() for p in v if p not in keys})
    return [f' RN_PROVNAME_{p}: "#{p}"\n' for p in missing]


def now_row_entries(now: str) -> list[str]:
    """Return the ``RN_VPROW_NOW_<k>`` lines: original name and the name applied here.

    Args:
        now: The word for "now" in the file's language.

    Returns:
        One line per VP slot.
    """
    return [
        f' RN_VPROW_NOW_{k}: "[ROOT.RN_VpName_{k}] ({now} {slots_expr(buffer.prefix)})"\n'
        for k, buffer in enumerate(VP_NAME_BUFFERS)
    ]
