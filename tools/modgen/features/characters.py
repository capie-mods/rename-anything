"""Characters tab: a paged list of the player's characters with a role icon.

Scripted GUI cannot reach a character's portrait sprite: the game's Character
localisation object has no portrait getter (documentation/loc_objects), and a
scripted GUI ``image`` property only takes a sprite name from localisation.
Vanilla scripted GUIs (``GER_inner_circle``) hard-code one sprite per known
character. So each row starts with a role icon, a vanilla text-icon sprite
whose tooltip names the role: country leader, army leader, navy leader or
adviser. The country leader's row shares the in-place leader editor's cooldown.
"""

from __future__ import annotations

from modgen.common import LIST_ROW_HEIGHT, LIST_WIDTH, TAB_CHARACTERS
from modgen.features.main_window import DynamicList, TabSpec
from modgen.gui import BUTTON_SMALL, WINDOW_END, PagedList, btn, entry_window, paged_list, txt

CHAR_ROLES = [
    ("is_country_leader", "LEADER", "GFX_pol_idea", (20, 16)),
    ("is_army_leader", "ARMY", "GFX_army_experience", (14, 14)),
    ("is_navy_leader", "NAVY", "GFX_navy_experience", (14, 14)),
    ("is_advisor", "ADVISER", "GFX_pol_power", (18, 19)),
]
"""Character role trigger, key suffix, vanilla sprite and its texture size in pixels.

The first matching role wins (a leader can also advise), so each icon's visible
trigger excludes every earlier role.
"""

ROLE_ICON_BOX = 20
"""Square, in pixels, in which each role icon is centred at the start of a row."""

ROLE_ICON_X = 6
"""X of the role icon box inside a row."""

NAME_X = ROLE_ICON_X + ROLE_ICON_BOX + 6
"""X of the character name, after the role icon and a 6 px gap."""

NAME_WIDTH = 382
"""Width of the character name; it ends 6 px before the Rename button at x 420."""

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


def _role_visible(index: int) -> str:
    """Return the visible trigger of one role icon: this role and none of the earlier ones.

    Args:
        index: Position of the role in :data:`CHAR_ROLES`.

    Returns:
        The trigger body.
    """
    trigger, _, _, _ = CHAR_ROLES[index]
    earlier = " ".join(f"NOT = {{ {t} = yes }}" for t, _, _, _ in CHAR_ROLES[:index])
    body = f"{trigger} = yes {earlier}".strip()
    return f"var:{ROW_VARIABLE} = {{ {body} }}"


_ROLE_TRIGGERS = "".join(
    f"\t\t\trn_char_role_{role.lower()}_visible = {{ {_role_visible(i)} }}\n"
    for i, (_, role, _, _) in enumerate(CHAR_ROLES)
)
"""Visible triggers of the four role icons of a row."""

_TRIGGERS = f"""			rn_char_rename_click_enabled = {{ NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ is_country_leader = yes }} rn_ip_cooldown_active_leader = yes }} }} NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ is_country_leader = yes }} rn_feature_leader_off = yes }} }} NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ NOT = {{ is_country_leader = yes }} }} rn_feature_characters_off = yes }} }} }}
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
        _ROLE_TRIGGERS + _TRIGGERS,
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
        *(role_icon(role, sprite, size) for _, role, sprite, size in CHAR_ROLES),
        txt("rn_char_name", NAME_X, 8, "RN_CHAR_NAME", w=NAME_WIDTH),
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


def role_icon(role: str, sprite: str, size: tuple[int, int]) -> str:
    """Return one role icon of a list row, centred in its box, with the role as tooltip.

    Args:
        role: Key suffix from :data:`CHAR_ROLES`.
        sprite: Vanilla sprite.
        size: Texture width and height in pixels.

    Returns:
        The ``iconType`` line.
    """
    x = ROLE_ICON_X + (ROLE_ICON_BOX - size[0]) // 2
    y = (LIST_ROW_HEIGHT - size[1]) // 2
    return (
        f'\t\ticonType = {{ name = "rn_char_role_{role.lower()}" position = {{ x = {x} y = {y} }}'
        f' spriteType = "{sprite}" pdx_tooltip = "RN_CHAR_ROLE_{role}" }}\n'
    )
