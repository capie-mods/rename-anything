"""States tab and the panel in the selected state view.

Both offer the same three actions on an owned state: rename it (one state
rename per cooldown), reset its name, or open its cities on the Cities tab.
The state view panel is the only entry point on the map; there is no global
entry button any more (it covered the leader portrait and the decision list).
"""

from __future__ import annotations

from modgen.common import LIST_ROW_HEIGHT, LIST_WIDTH, TAB_CITIES, TAB_STATES
from modgen.features.main_window import DynamicList, TabSpec
from modgen.gui import (
    BUTTON_MEDIUM,
    BUTTON_SMALL,
    WINDOW_END,
    PagedList,
    background,
    btn,
    entry_window,
    paged_list,
    txt,
)

PAGED_LIST = PagedList("states", "rn_states_grid", "rn_spage_prev", "rn_spage_next", "RN_SPAGE")
"""Element names of the States list."""

_EFFECTS = f"""			rn_state_rename_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					ROOT = {{ rn_target_state = yes }}
				}}
			}}
			rn_state_reset_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					reset_state_name = yes
				}}
			}}
			rn_state_cities_click = {{
				ROOT = {{
					set_variable = {{ rn_sel_state = PREV }}
					set_temp_variable = {{ rn_newtab = {TAB_CITIES} }}
					rn_set_tab = yes
				}}
			}}
			rn_spage_prev_click = {{ subtract_from_variable = {{ rn_spage = 1 }} rn_build_state_page = yes }}
			rn_spage_next_click = {{ add_to_variable = {{ rn_spage = 1 }} rn_build_state_page = yes }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI effects of the States tab."""

_TRIGGERS = """			rn_state_rename_click_enabled = { ROOT = { NOT = { rn_cd_state_active = yes } } }
			rn_spage_prev_click_enabled = { check_variable = { rn_spage > 0 } }
			rn_spage_next_click_enabled = { check_variable = { rn_spage_disp < rn_spages } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI triggers of the States tab."""

STATE_VIEW_X = 476
"""X position of the panel inside the vanilla selected state view."""

STATE_VIEW_Y = 95
"""Y position of the panel inside the vanilla selected state view."""


def tab(content_y: int) -> TabSpec:
    """Return the States tab.

    Args:
        content_y: Y position where tab content starts.

    Returns:
        The tab specification.
    """
    return TabSpec(
        TAB_STATES,
        "states",
        _EFFECTS,
        _TRIGGERS,
        tuple(paged_list(PAGED_LIST, content_y)),
        DynamicList(
            PAGED_LIST.grid, "rn_states_page", "rn_state_entry", "\t\t\t\tchange_scope = yes"
        ),
    )


def list_entry() -> list[str]:
    """Return the row template of the States list.

    Returns:
        GUI blocks of the ``rn_state_entry`` window.
    """
    return [
        entry_window("rn_state_entry", LIST_WIDTH, LIST_ROW_HEIGHT),
        txt("rn_state_name", 6, 8, "RN_STATE_NAME", w=215),
        btn(
            "rn_state_rename",
            228,
            2,
            BUTTON_SMALL,
            text="RN_BTN_RENAME",
            tooltip="RN_CD_STATE_TT",
        ),
        btn("rn_state_reset", 324, 2, BUTTON_SMALL, text="RN_BTN_RESET"),
        btn("rn_state_cities", 420, 2, BUTTON_SMALL, text="RN_BTN_CITIES"),
        WINDOW_END,
    ]


def state_view_gui() -> str:
    """Return the scripted GUI of the panel in the selected state view.

    Returns:
        The ``rn_state_view_gui`` block (one tab of indentation).
    """
    return f"""	rn_state_view_gui = {{
		context_type = selected_state_context
		parent_window_token = selected_state_view
		window_name = "rn_state_view_window"
		visible = {{ is_owned_by = ROOT }}
		ai_enabled = {{ always = no }}
		effects = {{
			rn_sv_rename_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					ROOT = {{ rn_target_state = yes }}
				}}
			}}
			rn_sv_cities_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					ROOT = {{
						set_country_flag = rn_open
						clr_country_flag = rn_input
						set_variable = {{ rn_sel_state = PREV }}
						set_temp_variable = {{ rn_newtab = {TAB_CITIES} }}
						rn_set_tab = yes
					}}
				}}
			}}
			rn_sv_reset_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					reset_state_name = yes
					ROOT = {{ rn_gui_touch = yes }}
				}}
			}}
		}}
		triggers = {{
			rn_sv_rename_click_enabled = {{ ROOT = {{ NOT = {{ rn_cd_state_active = yes }} }} }}
		}}
	}}
"""


def state_view_window() -> list[str]:
    """Return the ``.gui`` panel shown in the selected state view.

    Returns:
        GUI blocks of the ``rn_state_view_window``, ending with its closing brace.
    """
    return [
        '\tcontainerWindowType = {\n\t\tname = "rn_state_view_window"\n'
        "\t\torientation = upper_left\n"
        f"\t\tposition = {{ x = {STATE_VIEW_X} y = {STATE_VIEW_Y} }}\n"
        "\t\tsize = { width = 140 height = 136 }\n"
        "\t\tclipping = no\n" + background("rn_sv_bg"),
        txt("rn_sv_title", 10, 8, "RN_SV_TITLE", w=120),
        btn(
            "rn_sv_rename",
            8,
            32,
            BUTTON_MEDIUM,
            text="RN_SV_RENAME",
            tooltip="RN_CD_STATE_TT",
        ),
        btn("rn_sv_cities", 8, 66, BUTTON_MEDIUM, text="RN_SV_CITIES"),
        btn("rn_sv_reset", 8, 100, BUTTON_MEDIUM, text="RN_SV_RESET"),
        WINDOW_END,
    ]
