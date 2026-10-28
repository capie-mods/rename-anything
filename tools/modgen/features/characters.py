"""Characters tab: a paged list of the player's characters with a mini portrait and a role icon.

Scripted GUI cannot reach a character's portrait sprite: the game's Character
localisation object has no portrait getter (documentation/loc_objects), and a
scripted GUI ``image`` property only takes a sprite name from localisation.
Vanilla scripted GUIs (``GER_inner_circle``) hard-code one sprite per known
character. So each row starts with a role icon, a vanilla text-icon sprite
whose tooltip names the role: country leader, army leader, navy leader or
adviser. The country leader's row shares the in-place leader editor's cooldown.

Mini portrait: a second grid drawn over the rows iterates the numeric array ``rn_chars_pp``
(one portrait value per row, built with the page by ``rn_build_char_page``) and shows
``GFX_rnchp_<value>``, the way the flag picker builds its cell images (:mod:`char_portraits`).

Native portrait experiment (review R2, off by default): ``tools/gen.py --native-portrait-test``
adds a third grid that iterates the page's characters with ``change_scope = yes`` and an icon
whose scripted GUI property is ``image = "portrait"``. In hoi4.exe 1.19.4.0 the updater
(``BDD5B0``) draws that value natively through ``B9B1F0`` when the entry scope's character has a
unit-leader object (``57CB60`` -> ``141023EE0``, character ``+0xA8``), with the game's fallback
``GFX_leader_unknown``; for any other scope it sets the sprite named ``portrait``. The shipped
mod never contains it: the updater evaluates every image property on refresh whether or not the
icon is shown, so a dormant icon would still run for every player.
"""

from __future__ import annotations

from modgen.common import LIST_ROW_HEIGHT, LIST_WIDTH, PAGE, TAB_CHARACTERS
from modgen.features.char_portraits import DLC_BLOCK, DLC_OFFSET, DLC_SMALL, SMALL_OFFSET
from modgen.features.main_window import DynamicList, TabSpec
from modgen.gui import (
    BUTTON_SMALL,
    WINDOW_END,
    PagedList,
    btn,
    entry_window,
    gridbox,
    paged_list,
    txt,
)

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

PORTRAIT_X = 6
"""X of the mini portrait at the start of a row."""

PORTRAIT_WIDTH = 26
"""Width reserved for the mini portrait (a 156 x 210 portrait at :data:`LARGE_SCALE`)."""

LARGE_SCALE = 0.16
"""Scale of a large portrait (156 x 210 -> 25 x 34) in a 36 px row."""

SMALL_SCALE = 0.42
"""Scale of a small idea-style portrait (about 60 x 68 -> 25 x 29)."""

PORTRAIT_GRID = "rn_chars_pp_grid"
"""Grid over the list rows that shows the mini portraits."""

PORTRAIT_ENTRY = "rn_char_pp_entry"
"""Row template of :data:`PORTRAIT_GRID`."""

PORTRAIT_ARRAY = "rn_chars_pp"
"""Country array: the portrait value of each row of the page, in row order."""

PORTRAIT_VALUE = "rn_pv"
"""Value variable of a :data:`PORTRAIT_GRID` row."""

NATIVE_GRID = "rn_chars_np_grid"
"""Grid of the native portrait experiment (:func:`native_entry`)."""

NATIVE_ENTRY = "rn_char_np_entry"
"""Row template of :data:`NATIVE_GRID`."""

NATIVE_ICON = "rn_char_np"
"""Icon of a :data:`NATIVE_GRID` row; its property is ``image = "portrait"``."""

NATIVE_VALUE = "rn_np_char"
"""Value variable of a :data:`NATIVE_GRID` row (the row's character, also its scope)."""

NATIVE_X = 420 - 6 - PORTRAIT_WIDTH
"""X of the experiment's portrait box in a row: just before the Rename button (x 420)."""

NATIVE_DEFAULT = "GFX_rn_key"
"""Default sprite of :data:`NATIVE_ICON`: a key tile, so a row the property never touched shows."""

ROLE_ICON_BOX = 20
"""Square, in pixels, in which each role icon is centred after the portrait."""

ROLE_ICON_X = PORTRAIT_X + PORTRAIT_WIDTH + 4
"""X of the role icon box inside a row."""

NAME_X = ROLE_ICON_X + ROLE_ICON_BOX + 6
"""X of the character name, after the role icon and a 6 px gap."""

NAME_WIDTH = 382 - PORTRAIT_WIDTH - 4
"""Width of the character name; it ends 6 px before the Rename button at x 420."""

ROW_VARIABLE = "rn_row_character"
"""Typed variable that holds the character of a list row.

The native GUI scope bridge only carries country, state and unit-leader contexts,
so civilian characters are kept as a typed row variable instead of a scope.
"""

PAGED_LIST_ARRAY = "rn_chars_page"
"""Country array of the characters on the shown page, in row order (``rn_build_char_page``)."""

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


def portrait_triggers(packs: tuple[str, ...] = ()) -> str:
    """Return the visible triggers of the three portrait icons of a row.

    ``l`` shows a large picture (catalog, extra large, unknown) and ``s`` a small one. A DLC-block
    value (:data:`~modgen.features.char_portraits.DLC_OFFSET`) shows its picture only when the
    local player owns that DLC and the unknown portrait (``u``) otherwise. ``has_dlc`` appears only
    in these ``_visible`` triggers: it decides what the local UI shows, never game state.

    Args:
        packs: ``has_dlc`` names of the DLC blocks, in block order.

    Returns:
        The trigger lines.
    """
    v = PORTRAIT_VALUE

    def in_range(lo: int, hi: int) -> str:
        return f"NOT = {{ check_variable = {{ {v} < {lo} }} }} check_variable = {{ {v} < {hi} }}"

    large = [f"check_variable = {{ {v} < {SMALL_OFFSET} }}"]
    small = [f"AND = {{ {in_range(SMALL_OFFSET, DLC_OFFSET)} }}"]
    unknown = []
    for p, name in enumerate(packs):
        start = DLC_OFFSET + p * DLC_BLOCK
        owned = f'has_dlc = "{name}"'
        large.append(f"AND = {{ {in_range(start, start + DLC_SMALL)} {owned} }}")
        small.append(f"AND = {{ {in_range(start + DLC_SMALL, start + DLC_BLOCK)} {owned} }}")
        unknown.append(f"AND = {{ {in_range(start, start + DLC_BLOCK)} NOT = {{ {owned} }} }}")
    return (
        f"\t\t\trn_char_pp_l_visible = {{ OR = {{ {' '.join(large)} }} }}\n"
        f"\t\t\trn_char_pp_s_visible = {{ OR = {{ {' '.join(small)} }} }}\n"
        f"\t\t\trn_char_pp_u_visible = {{ OR = {{ {' '.join(unknown) or 'always = no'} }} }}\n"
    )


_PROPERTIES = (
    f'\t\t\trn_char_pp_l = {{ image = "GFX_rnchp_[?{PORTRAIT_VALUE}|0]" }}\n'
    f'\t\t\trn_char_pp_s = {{ image = "GFX_rnchp_[?{PORTRAIT_VALUE}|0]" }}\n'
)
"""Row images: the sprite number is the row's numeric value."""

_TRIGGERS = f"""			rn_char_rename_click_enabled = {{ NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ is_country_leader = yes }} rn_ip_cooldown_active_leader = yes }} }} NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ is_country_leader = yes }} rn_feature_leader_off = yes }} }} NOT = {{ AND = {{ var:{ROW_VARIABLE} = {{ NOT = {{ is_country_leader = yes }} }} rn_feature_characters_off = yes }} }} }}
			rn_cpage_prev_click_enabled = {{ check_variable = {{ rn_cpage > 0 }} }}
			rn_cpage_next_click_enabled = {{ check_variable = {{ rn_cpage_disp < rn_cpages }} }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI triggers of the Characters tab."""


def tab(content_y: int, dlc_packs: tuple[str, ...] = (), *, native_test: bool = False) -> TabSpec:
    """Return the Characters tab.

    Args:
        content_y: Y position where tab content starts.
        dlc_packs: ``has_dlc`` names of the mini portraits' DLC blocks (:func:`portrait_triggers`).
        native_test: Add the native portrait experiment (:data:`NATIVE_GRID`, review R2).

    Returns:
        The tab specification.
    """
    native_elements: tuple[str, ...] = ()
    native_lists: tuple[DynamicList, ...] = ()
    native_property = ""
    if native_test:
        native_elements = (
            gridbox(
                NATIVE_GRID,
                (20 + NATIVE_X, content_y),
                (PORTRAIT_WIDTH, PAGE * LIST_ROW_HEIGHT),
                LIST_ROW_HEIGHT,
            ),
        )
        native_lists = (
            DynamicList(
                NATIVE_GRID,
                PAGED_LIST_ARRAY,
                NATIVE_ENTRY,
                f"\t\t\t\tvalue = {NATIVE_VALUE}\n\t\t\t\tchange_scope = yes",
            ),
        )
        native_property = f'\t\t\t{NATIVE_ICON} = {{ image = "portrait" }}\n'
    return TabSpec(
        TAB_CHARACTERS,
        "chars",
        _EFFECTS,
        portrait_triggers(dlc_packs) + _ROLE_TRIGGERS + _TRIGGERS,
        (
            *paged_list(PAGED_LIST, content_y),
            gridbox(
                PORTRAIT_GRID,
                (20, content_y),
                (PORTRAIT_X + PORTRAIT_WIDTH, PAGE * LIST_ROW_HEIGHT),
                LIST_ROW_HEIGHT,
            ),
            *native_elements,
        ),
        DynamicList(
            PAGED_LIST.grid,
            PAGED_LIST_ARRAY,
            "rn_char_entry",
            f"\t\t\t\tvalue = {ROW_VARIABLE}\n\t\t\t\tchange_scope = no",
        ),
        _PROPERTIES + native_property,
        (
            DynamicList(
                PORTRAIT_GRID,
                PORTRAIT_ARRAY,
                PORTRAIT_ENTRY,
                f"\t\t\t\tvalue = {PORTRAIT_VALUE}\n\t\t\t\tchange_scope = no",
            ),
            *native_lists,
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


def portrait_entry() -> list[str]:
    """Return the row template of the mini portrait grid.

    Returns:
        GUI blocks of the ``rn_char_pp_entry`` window.
    """
    return [
        entry_window(PORTRAIT_ENTRY, PORTRAIT_X + PORTRAIT_WIDTH, LIST_ROW_HEIGHT),
        portrait_icon("l", "GFX_rnchp_0", LARGE_SCALE, (156, 210)),
        portrait_icon("s", "GFX_rnchp_0", SMALL_SCALE, (60, 68)),
        portrait_icon("u", "GFX_rnchp_0", LARGE_SCALE, (156, 210)),
        WINDOW_END,
    ]


def native_entry() -> list[str]:
    """Return the row template of the native portrait experiment (:data:`NATIVE_GRID`).

    The icon uses the large-portrait scale, so a 156 x 210 portrait fills the same 25 x 34 box as
    the mini portrait.

    Returns:
        GUI blocks of the ``rn_char_np_entry`` window.
    """
    x = (PORTRAIT_WIDTH - round(156 * LARGE_SCALE)) // 2
    y = (LIST_ROW_HEIGHT - round(210 * LARGE_SCALE)) // 2
    return [
        entry_window(NATIVE_ENTRY, PORTRAIT_WIDTH, LIST_ROW_HEIGHT),
        (
            f'\t\ticonType = {{ name = "{NATIVE_ICON}" position = {{ x = {x} y = {y} }}'
            f' spriteType = "{NATIVE_DEFAULT}" scale = {LARGE_SCALE} }}\n'
        ),
        WINDOW_END,
    ]


def portrait_icon(kind: str, sprite: str, scale: float, size: tuple[int, int]) -> str:
    """Return one icon of the mini portrait grid, centred in the portrait box.

    Args:
        kind: ``l`` (156 x 210: catalog or unknown), ``s`` (small idea-style portrait) or ``u``
            (the unknown portrait for a DLC picture the local player does not own).
        sprite: Default sprite (the scripted GUI property replaces it for ``l`` and ``s``).
        scale: Icon scale.
        size: Texture width and height in pixels.

    Returns:
        The ``iconType`` line.
    """
    x = PORTRAIT_X + (PORTRAIT_WIDTH - round(size[0] * scale)) // 2
    y = (LIST_ROW_HEIGHT - round(size[1] * scale)) // 2
    return (
        f'\t\ticonType = {{ name = "rn_char_pp_{kind}" position = {{ x = {x} y = {y} }}'
        f' spriteType = "{sprite}" scale = {scale} }}\n'
    )


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
