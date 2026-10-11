"""Characters tab: a paged list of the player's characters with a role icon.

Scripted GUI cannot reach a character's portrait sprite (there is no
localisation getter for it), so each row shows a role icon instead: the country
flag for the leader, then army, navy or adviser. The country leader's row shares
the in-place leader editor's cooldown.
"""

from __future__ import annotations

from modgen.common import EMPTY_LOC_KEY, LIST_ROW_HEIGHT, LIST_WIDTH, TAB_CHARACTERS
from modgen.features.main_window import DynamicList, TabSpec
from modgen.gui import BUTTON_SMALL, WINDOW_END, PagedList, btn, entry_window, paged_list, txt
from modgen.script import defined_text

CHAR_ROLES = [
    ("is_country_leader", "LEADER"),
    ("is_army_leader", "ARMY"),
    ("is_navy_leader", "NAVY"),
    ("is_advisor", "ADVISER"),
]
"""Character role trigger and icon key suffix; the first match wins (a leader can also advise)."""

ROW_VARIABLE = "rn_row_character"
"""Typed variable that holds the character of a list row.

The native GUI scope bridge only carries country, state and unit-leader contexts,
so civilian characters are kept as a typed row variable instead of a scope.
"""

PAGED_LIST = PagedList("chars", "rn_chars_grid", "rn_cpage_prev", "rn_cpage_next", "RN_PAGE")
"""Element names of the Characters list."""

_EFFECTS = f"""			rn_char_rename_click = {{ var:{ROW_VARIABLE} = {{ ROOT = {{ rn_target_character = yes }} }} }}
			rn_cpage_prev_click = {{ subtract_from_variable = {{ rn_cpage = 1 }} rn_build_char_page = yes }}
			rn_cpage_next_click = {{ add_to_variable = {{ rn_cpage = 1 }} rn_build_char_page = yes }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI effects of the Characters tab."""

_TRIGGERS = f"""			rn_char_rename_click_enabled = {{ NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ is_country_leader = yes }} rn_ip_cooldown_active_leader = yes }} }} }}
			rn_cpage_prev_click_enabled = {{ check_variable = {{ rn_cpage > 0 }} }}
			rn_cpage_next_click_enabled = {{ check_variable = {{ rn_cpage_disp < rn_cpages }} }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI triggers of the Characters tab."""


def tab(content_y: int) -> TabSpec:
    """Return the Characters tab.

    Args:
        content_y: Y position where tab content starts.

    Returns:
        The tab specification.
    """
    return TabSpec(
        TAB_CHARACTERS,
        "chars",
        _EFFECTS,
        _TRIGGERS,
        tuple(paged_list(PAGED_LIST, content_y)),
        DynamicList(
            PAGED_LIST.grid,
            "rn_chars_page",
            "rn_char_entry",
            f"\t\t\t\tvalue = {ROW_VARIABLE}\n\t\t\t\tchange_scope = no",
        ),
    )


def list_entry() -> list[str]:
    """Return the row template of the Characters list.

    Returns:
        GUI blocks of the ``rn_char_entry`` window.
    """
    return [
        entry_window("rn_char_entry", LIST_WIDTH, LIST_ROW_HEIGHT),
        txt("rn_char_name", 6, 8, "RN_CHAR_NAME", w=390),
        btn(
            "rn_char_rename",
            420,
            2,
            BUTTON_SMALL,
            text="RN_BTN_RENAME",
            tooltip="RN_CHAR_RENAME_TT",
        ),
        WINDOW_END,
    ]


def role_icon_loc() -> str:
    """Return the ``RN_CharRoleIcon`` scripted localisation of a list row.

    Returns:
        A ``defined_text`` that picks the first matching role's icon key.
    """
    return defined_text(
        "RN_CharRoleIcon",
        [
            (f"var:{ROW_VARIABLE} = {{ {trigger} = yes }}", f"RN_CHAR_ICON_{role}")
            for trigger, role in CHAR_ROLES
        ],
        EMPTY_LOC_KEY,
    )
