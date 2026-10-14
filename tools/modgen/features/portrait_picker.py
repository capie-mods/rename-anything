"""Portrait picker: the "Portrait" tab of the leader editor and the subject's leader portrait.

Two CAPIE grammar editors without text fields, on the flag picker's pattern:
``capie_v1_ed__rnpt__portrait`` for the player's own country leader (politics view)
and ``capie_v1_ed__rnpt__subportrait`` for another country's leader (diplomacy
view). They use the mod id ``rnpt`` because CAPIE registers at most eight editors
per mod id (CONTRACT section 3) and ``rn`` already has seven. The choice lives in
``rn_pp_*`` variables on the player; the hand-written effects
(``tools/inline_editor/common/scripted_effects/rn_portrait_picker.txt``) check
everything again.

Layout (own picker 364 px wide, placed right of the politics view's leader frame
so the current portrait stays visible; the subject picker is 384 px for its four
tabs)::

    y   0  tabs                          Name | Portrait   or   Country | Leader | Party | Flag
    y  36  preview (leader frame, 0.5)   3 x 2 portraits (0.4), or 2 x 5 countries     Apply Cancel
    y 168  name of the selected portrait
    y 216  Leaders | Generals (rule)                                                   < 2 / 9 >
    y 250  This country | All (rule)
    y 284  A B C ... Z (country list)
    y 302  status line
    y 318                                                                    Restore portrait

Vanilla sprites only: the politics leader frame, the diplomacy leader frame for
the selected cell, standard buttons and arrows, plus the shared transparent hit
areas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from modgen.common import GEN_HEADER
from modgen.features.picker_common import (
    button,
    captioned,
    gridbox,
    icon,
    letter_lines,
    letter_row,
    text,
)
from modgen.features.portraits import GENERAL, LEADER

if TYPE_CHECKING:
    from modgen.features.portraits import PortraitCatalog

HEIGHT = 352
"""Window height (28 + 352 stays above the politics view's action row at 383)."""

TAB_PITCH = 96
"""Distance between two tabs."""

CONTENT_Y = 36
"""Top of the preview and the grid."""

PREVIEW_SCALE = 0.5
"""Scale of the preview frame and portrait (vanilla frame 172 x 258, portrait 156 x 210)."""

PREVIEW_FRAME = (0, CONTENT_Y)
"""Position of the scaled ``GFX_pol_leader_frame``."""

PREVIEW_PORTRAIT = (4, CONTENT_Y + 7)
"""Position of the scaled portrait (vanilla frame + (8, 14), halved)."""

NAME_Y = 168
"""Top of the selected portrait's name."""

NAME_W = 88
"""Width of the preview column."""

GRID_X = 92
"""Left edge of the grid."""

CELL = (72, 88)
"""Grid slot."""

CELL_SCALE = 0.4
"""Scale of a portrait in the grid (62 x 84)."""

CELL_PORTRAIT = (5, 2)
"""Position of the portrait in its slot."""

SELECTED_SCALE = 0.5
"""Scale of ``GFX_diplo_leader_frame`` (134 x 175) around the selected portrait."""

CELL_FRAME = (3, 0)
"""Position of the selection frame in its slot."""

GRID_COLUMNS = 3
"""Portraits per row."""

GRID_ROWS = 2
"""Rows; six portraits per page."""

PAGE = GRID_COLUMNS * GRID_ROWS
"""Portraits per page."""

ROW = (108, 16)
"""Country row of the country list."""

ROW_COLUMNS = 2
"""Country rows side by side."""

ROW_ROWS = 5
"""Country rows under each other; ten countries per page."""

KIND_Y = 216
"""Top of the Leaders | Generals row (and of the pager)."""

SCOPE_Y = 250
"""Top of the This country | All row."""

LETTER_Y = 284
"""Top of the letter row."""

LETTER_W = 14
"""Width of one letter."""

STATUS_Y = 302
"""Top of the status line."""

RESET_Y = 318
"""Top of "Restore portrait" (``GFX_button_123x34``)."""

SCRIPTED_GUI_FILE = "common/scripted_guis/rn_portrait_picker.txt"
"""Scripted GUI file, relative to ``mod/``."""

GUI_FILE = "interface/rn_portrait_picker.gui"
"""Window file, relative to ``mod/``."""

POOL_RULE = "rn_portrait_pool"
"""Game rule of the portrait pool."""

ALL_RULE = (
    "OR = { has_game_rule = { rule = rn_portrait_pool option = RN_PORTRAIT_POOL_ANY_LEADER } "
    "has_game_rule = { rule = rn_portrait_pool option = RN_PORTRAIT_POOL_ALL } }"
)
"""Trigger: the rule offers other countries' portraits."""

GENERALS_RULE = (
    "OR = { has_game_rule = { rule = rn_portrait_pool option = RN_PORTRAIT_POOL_OWN_GENERALS } "
    "has_game_rule = { rule = rn_portrait_pool option = RN_PORTRAIT_POOL_ALL } }"
)
"""Trigger: the rule offers generals' and admirals' portraits."""

SUBJECTS_ON = "NOT = { rn_feature_subjects_off = yes }"
"""Trigger: the host has not switched off changes to other countries."""

_ROOT_OK = "is_ai = no NOT = { has_country_flag = rn_open } NOT = { has_country_flag = rn_input }"
"""Player state every picker click needs."""


class Picker(NamedTuple):
    """One of the two portrait editors."""

    editor: str
    """CAPIE editor id (``portrait`` or ``subportrait``)."""

    context: str
    """Scripted GUI ``context_type``."""

    parent: str
    """``parent_window_token``."""

    position: tuple[int, int]
    """Window position."""

    width: int
    """Window width."""

    open_flag: str
    """Country flag on the player while this picker is open."""

    tabs: tuple[tuple[str, str, str], ...]
    """Tabs as ``(element suffix, text key, tooltip key)``."""

    @property
    def key(self) -> str:
        """Return the scripted GUI key and window name.

        Returns:
            ``capie_v1_ed__rnpt__<editor>``.
        """
        return f"capie_v1_ed__rnpt__{self.editor}"


OWN = Picker(
    "portrait",
    "player_context",
    "politics_tab",
    (186, 28),
    364,
    "rn_pp_open_own",
    (
        ("name", "RN_PP_TAB_NAME", "RN_PP_TAB_NAME_TT"),
        ("portrait", "RN_PP_TAB_PORTRAIT", "RN_PP_TAB_PORTRAIT_TT"),
    ),
)
"""Own country leader: in the politics view, right of the leader's portrait."""

SUBJECT = Picker(
    "subportrait",
    "selected_country_context",
    "selected_country_view_diplomacy",
    (65, 37),
    384,
    "rn_pp_open_sub",
    (
        ("country", "RN_SUB_TAB_COUNTRY", "RN_SUB_TAB_COUNTRY_TT"),
        ("leader", "RN_SUB_TAB_LEADER", "RN_SUB_TAB_LEADER_TT"),
        ("party", "RN_SUB_TAB_PARTY", "RN_SUB_TAB_PARTY_TT"),
        ("flag", "RN_FP_TAB_FLAG", "RN_FP_TAB_FLAG_TT"),
    ),
)
"""Another country's leader: in its diplomacy view."""

PICKERS = (OWN, SUBJECT)
"""Both editors."""


def letter_entries(catalog: PortraitCatalog) -> tuple[int, ...]:
    """Return the letters that have a country with portraits of either kind.

    Args:
        catalog: The catalog.

    Returns:
        Letters 1..26.
    """
    return tuple(
        n for n in range(1, 27) if catalog.letters[LEADER][n - 1] or catalog.letters[GENERAL][n - 1]
    )


def _scaled(scale: float) -> str:
    """Return a ``scale`` attribute line.

    Args:
        scale: Scale factor.

    Returns:
        Attribute line.
    """
    return f"\t\t\tscale = {scale}\n"


def window(picker: Picker, letters: tuple[int, ...]) -> str:
    """Return the window of one picker.

    Args:
        picker: The editor.
        letters: Letter entries.

    Returns:
        The ``containerWindowType`` block.
    """
    x, y = picker.position
    w = picker.width
    arrow_y = KIND_Y + 7
    tabs = "".join(
        button(
            f"rn_pp_{picker.editor}_tab_{suffix}",
            (i * TAB_PITCH, 0),
            "GFX_button_94x31",
            attrs=captioned(label, tip),
        )
        for i, (suffix, label, tip) in enumerate(picker.tabs)
    )
    parts = [
        f'\tcontainerWindowType = {{\n\t\tname = "{picker.key}"\n',
        f"\t\tposition = {{ x = {x} y = {y} }}\n",
        f"\t\tsize = {{ width = {w} height = {HEIGHT} }}\n",
        "\t\torientation = upper_left\n\t\tclipping = no\n",
        '\t\tbackground = { name = "Background" quadTextureSprite = "GFX_generic_bg2" }\n',
        "\t\t# CAPIE epoch carrier (hidden).\n",
        text(f"capie_v1_ep__rnpt__{picker.editor}", (0, 0), "[?ROOT.rn_pp_epoch|0]", (120, 14)),
        tabs,
        "\t\t# Preview: the selected portrait in the politics view's leader frame, at half size.\n",
        icon("rn_pp_preview", PREVIEW_PORTRAIT, "GFX_rnp_1", attrs=_scaled(PREVIEW_SCALE)),
        icon(
            "rn_pp_frame",
            PREVIEW_FRAME,
            "GFX_pol_leader_frame",
            attrs=_scaled(PREVIEW_SCALE) + "\t\t\talwaystransparent = yes\n",
        ),
        text("rn_pp_name", (0, NAME_Y), "RN_PP_NAME", (NAME_W, 40)),
        text("rn_pp_note", (0, CONTENT_Y + 60), "RN_PP_NOTE_NONE", (NAME_W, 40)),
        "\t\t# Portraits of one pool (rn_pp_grid) or countries (rn_pp_rows_grid).\n",
        gridbox("rn_pp_grid", (GRID_X, CONTENT_Y), CELL, GRID_COLUMNS, GRID_ROWS),
        gridbox("rn_pp_rows_grid", (GRID_X, CONTENT_Y), ROW, ROW_COLUMNS, ROW_ROWS),
        text("rn_pp_empty", (GRID_X, CONTENT_Y + 60), "RN_PP_EMPTY", (CELL[0] * GRID_COLUMNS, 28)),
        button(
            f"{picker.key}_apply",
            (w - 50, CONTENT_Y + 3),
            "GFX_preset_button_save",
            attrs=(
                "\t\t\tscale = 0.67 # 20x20\n"
                '\t\t\tpdx_tooltip = "RN_PP_APPLY_TT"\n\t\t\tshortcut = "RETURN"\n'
            ),
            quad=True,
        ),
        button(
            "rn_pp_cancel",
            (w - 24, CONTENT_Y + 5),
            "GFX_closebutton_16",
            attrs='\t\t\tpdx_tooltip = "RN_IP_CANCEL"\n',
            quad=True,
        ),
        "\t\t# Kind (game rule), pages, this country or every country (game rule), letters.\n",
        button(
            "rn_pp_kind_leaders",
            (0, KIND_Y),
            "GFX_button_94x31",
            attrs=captioned("RN_PP_LEADERS", "RN_PP_LEADERS_TT"),
        ),
        button(
            "rn_pp_kind_generals",
            (TAB_PITCH, KIND_Y),
            "GFX_button_94x31",
            attrs=captioned("RN_PP_GENERALS", "RN_PP_GENERALS_TT"),
        ),
        button(
            "rn_pp_prev",
            (w - 68, arrow_y),
            "GFX_opinion_arrow_left",
            attrs='\t\t\tpdx_tooltip = "RN_FP_PREV_TT"\n',
        ),
        text(
            "rn_pp_page",
            (w - 51, arrow_y + 1),
            "RN_PP_PAGE",
            (34, 14),
            extra="\t\t\tformat = centre\n",
        ),
        button(
            "rn_pp_next",
            (w - 17, arrow_y),
            "GFX_opinion_arrow_right",
            attrs='\t\t\tpdx_tooltip = "RN_FP_NEXT_TT"\n',
        ),
        button(
            "rn_pp_nav_own",
            (0, SCOPE_Y),
            "GFX_button_94x31",
            attrs=captioned("RN_FP_NAV_OWN", "RN_PP_NAV_OWN_TT"),
        ),
        button(
            "rn_pp_nav_all",
            (TAB_PITCH, SCOPE_Y),
            "GFX_button_94x31",
            attrs=captioned("RN_FP_NAV_ALL", "RN_PP_NAV_ALL_TT"),
        ),
        letter_row("rn_pp", letters, LETTER_Y, LETTER_W),
        text("rn_pp_status", (6, STATUS_Y), "[This.RN_PP_STATUS]", (w - 12, 14)),
        button(
            "rn_pp_reset",
            (w - 123, RESET_Y),
            "GFX_button_123x34",
            attrs=captioned("RN_PP_RESET", "RN_PP_RESET_TT"),
        ),
        "\t}\n",
    ]
    return "".join(parts)


def entries() -> str:
    """Return the two list entries: a portrait cell and a country row.

    Returns:
        The two ``containerWindowType`` blocks.
    """
    cell = (
        '\tcontainerWindowType = {\n\t\tname = "rn_pp_cell"\n'
        f"\t\tsize = {{ width = {CELL[0]} height = {CELL[1]} }}\n\t\tclipping = no\n"
        + button("rn_pp_cell_portrait", CELL_PORTRAIT, "GFX_rnp_1", attrs=_scaled(CELL_SCALE))
        + icon(
            "rn_pp_cell_sel",
            CELL_FRAME,
            "GFX_diplo_leader_frame",
            attrs=_scaled(SELECTED_SCALE) + "\t\t\talwaystransparent = yes\n",
        )
        + "\t}\n"
    )
    row = (
        '\tcontainerWindowType = {\n\t\tname = "rn_pp_row"\n'
        f"\t\tsize = {{ width = {ROW[0]} height = {ROW[1]} }}\n\t\tclipping = no\n"
        + button("rn_pp_row_hit", (0, 0), "GFX_rn_hit_row108")
        + text("rn_pp_row_name", (2, 1), "RN_FP_ROW", (ROW[0] - 4, 14))
        + text("rn_pp_row_name_on", (2, 1), "RN_FP_ROW_ON", (ROW[0] - 4, 14))
        + "\t}\n"
    )
    return cell + row


def gui(letters: tuple[int, ...]) -> str:
    """Return the window file.

    Args:
        letters: Letter entries.

    Returns:
        Contents of :data:`GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Portrait picker (tools/modgen/features/portrait_picker.py). Vanilla sprites only,\n"
        "# apart from the shared transparent hit areas.\n"
        "guiTypes = {\n" + "".join(window(p, letters) for p in PICKERS) + entries() + "}\n"
    )


# ----------------------------------------------------------------------------- scripted GUI


def _switched_on(picker: Picker) -> str:
    """Return the host-switch condition of the portrait buttons (ADR-0036).

    Args:
        picker: The editor.

    Returns:
        Trigger text.
    """
    out = "NOT = { rn_feature_portrait_off = yes }"
    if picker is SUBJECT:
        out += " NOT = { rn_feature_subjects_off = yes }"
    return out


def _visible(picker: Picker) -> str:
    """Return the window's visible trigger.

    Args:
        picker: The editor.

    Returns:
        Trigger body.
    """
    if picker is OWN:
        return (
            f"tag = ROOT {_ROOT_OK} has_country_flag = {picker.open_flag} "
            "is_in_array = { array = rn_pp_target_arr value = THIS }"
        )
    return (
        "NOT = { tag = ROOT } rn_sub_may_edit = yes "
        "is_in_array = { array = ROOT.rn_pp_target_arr value = THIS } "
        f"ROOT = {{ {_ROOT_OK} has_country_flag = {picker.open_flag} }}"
    )


def _tabs(picker: Picker) -> tuple[list[str], list[str]]:
    """Return the tab click effects and enabled triggers.

    Args:
        picker: The editor.

    Returns:
        ``(effects, triggers)``.
    """
    prefix = f"rn_pp_{picker.editor}_tab_"
    if picker is OWN:
        return (
            [
                (
                    f"\t\t\t{prefix}name_click = "
                    "{ ROOT = { rn_pp_to_name_editor = yes rn_ip_status_clear = yes } }\n"
                )
            ],
            [
                f"\t\t\t{prefix}portrait_click_enabled = {{ always = no }}\n",
                (
                    f"\t\t\t{prefix}name_click_enabled = "
                    "{ NOT = { rn_ip_cooldown_active_leader = yes } "
                    "NOT = { rn_feature_leader_off = yes } }\n"
                ),
            ],
        )
    effects: list[str] = []
    triggers: list[str] = []
    for suffix in ("country", "leader", "party"):
        on = f"NOT = {{ rn_feature_{suffix}_off = yes }} {SUBJECTS_ON}"
        limit = f"rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }} {on}"
        effects.append(
            f"\t\t\t{prefix}{suffix}_click = {{\n"
            f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {limit} }}\n"
            "\t\t\t\t\tROOT = { rn_pp_close = yes }\n\t\t\t\t\trn_sub_open_common = yes\n"
            f"\t\t\t\t\tROOT = {{ set_country_flag = rn_sub_open_{suffix} }}\n"
            "\t\t\t\t}\n\t\t\t}\n"
        )
        triggers.append(f"\t\t\t{prefix}{suffix}_click_enabled = {{ {limit} }}\n")
    effects.append(
        f"\t\t\t{prefix}flag_click = {{ ROOT = {{ rn_pp_close = yes }} rn_fp_open_sub = yes }}\n"
    )
    flag_on = f"NOT = {{ rn_feature_flag_off = yes }} {SUBJECTS_ON}"
    limit = f"rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }} {flag_on}"
    triggers.append(f"\t\t\t{prefix}flag_click_enabled = {{ {limit} }}\n")
    return effects, triggers


_EFFECTS = """\t\t\trn_pp_cancel_click = { ROOT = { rn_pp_close = yes rn_cv1_status_clear = yes } }
\t\t\trn_pp_reset_click = { ROOT = { rn_pp_reset = yes } }
\t\t\trn_pp_cell_portrait_click = { set_temp_variable = { rn_pp_pick = rn_pp_v } ROOT = { rn_pp_pick_cell = yes } }
\t\t\trn_pp_row_hit_click = { rn_pp_pick_country = yes }
\t\t\trn_pp_nav_own_click = { ROOT = { rn_pp_show_target = yes } }
\t\t\trn_pp_nav_all_click = { ROOT = { rn_pp_show_list = yes } }
\t\t\trn_pp_kind_leaders_click = { ROOT = { set_temp_variable = { rn_pp_k = 1 } rn_pp_set_kind = yes } }
\t\t\trn_pp_kind_generals_click = { ROOT = { set_temp_variable = { rn_pp_k = 2 } rn_pp_set_kind = yes } }
\t\t\trn_pp_prev_click = { ROOT = { set_temp_variable = { rn_pp_step = -1 } rn_pp_page_step = yes } }
\t\t\trn_pp_next_click = { ROOT = { set_temp_variable = { rn_pp_step = 1 } rn_pp_page_step = yes } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Click effects both pickers share."""

_TRIGGERS = """\t\t\trn_pp_preview_visible = { ROOT = { check_variable = { rn_pp_sel > 0 } } }
\t\t\trn_pp_name_visible = { ROOT = { check_variable = { rn_pp_sel > 0 } } }
\t\t\trn_pp_note_visible = { ROOT = { NOT = { check_variable = { rn_pp_sel > 0 } } } }
\t\t\trn_pp_grid_visible = { ROOT = { check_variable = { rn_pp_view = 1 } } }
\t\t\trn_pp_rows_grid_visible = { ROOT = { check_variable = { rn_pp_view = 2 } } }
\t\t\trn_pp_empty_visible = { ROOT = { check_variable = { rn_pp_view = 1 } check_variable = { rn_pp_cells^num = 0 } } }
\t\t\trn_pp_cell_sel_visible = { check_variable = { rn_pp_v = ROOT.rn_pp_sel } }
\t\t\trn_pp_row_name_visible = { NOT = { is_in_array = { array = ROOT.rn_pp_src_arr value = THIS } } }
\t\t\trn_pp_row_name_on_visible = { is_in_array = { array = ROOT.rn_pp_src_arr value = THIS } }
\t\t\trn_pp_kind_leaders_visible = { @GENERALS_RULE@ }
\t\t\trn_pp_kind_generals_visible = { @GENERALS_RULE@ }
\t\t\trn_pp_kind_leaders_click_enabled = { ROOT = { NOT = { check_variable = { rn_pp_kind = 1 } } } }
\t\t\trn_pp_kind_generals_click_enabled = { ROOT = { NOT = { check_variable = { rn_pp_kind = 2 } } } }
\t\t\trn_pp_nav_own_visible = { @ALL_RULE@ }
\t\t\trn_pp_nav_own_click_enabled = { ROOT = { NOT = { has_country_flag = rn_pp_view_target } } }
\t\t\trn_pp_nav_all_visible = { @ALL_RULE@ }
\t\t\trn_pp_nav_all_click_enabled = { ROOT = { NOT = { check_variable = { rn_pp_view = 2 } } } }
\t\t\trn_pp_prev_visible = { ROOT = { check_variable = { rn_pp_pages > 1 } } }
\t\t\trn_pp_next_visible = { ROOT = { check_variable = { rn_pp_pages > 1 } } }
\t\t\trn_pp_page_visible = { ROOT = { check_variable = { rn_pp_pages > 1 } } }
\t\t\trn_pp_prev_click_enabled = { ROOT = { check_variable = { rn_pp_page > 0 } } }
\t\t\trn_pp_next_click_enabled = { ROOT = { check_variable = { rn_pp_page_disp < rn_pp_pages } } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Visible and enabled triggers both pickers share."""

_PROPERTIES_AND_LISTS = """\t\tproperties = {
\t\t\trn_pp_preview = { image = "GFX_rnp_[?ROOT.rn_pp_sel|0]" }
\t\t\trn_pp_cell_portrait = { image = "GFX_rnp_[?rn_pp_v|0]" }
\t\t}
\t\tdynamic_lists = {
\t\t\trn_pp_grid = {
\t\t\t\tarray = ROOT.rn_pp_cells
\t\t\t\tvalue = rn_pp_v
\t\t\t\tchange_scope = no
\t\t\t\tentry_container = "rn_pp_cell"
\t\t\t}
\t\t\trn_pp_rows_grid = {
\t\t\t\tarray = ROOT.rn_pp_rows
\t\t\t\tchange_scope = yes
\t\t\t\tentry_container = "rn_pp_row"
\t\t\t}
\t\t}
"""
"""Portrait images by catalog index and the two lists."""


def scripted_gui(picker: Picker, letters: tuple[int, ...]) -> str:
    """Return the scripted GUI of one picker.

    Args:
        picker: The editor.
        letters: Letter entries.

    Returns:
        The ``<key> = { ... }`` block.
    """
    shown = f"{ALL_RULE} ROOT = {{ check_variable = {{ rn_pp_view = 2 }} }}"
    letter_effects, letter_triggers = letter_lines("rn_pp", letters, shown)
    tab_effects, tab_triggers = _tabs(picker)
    on = _switched_on(picker)
    lines = [
        f"\t{picker.key} = {{\n",
        f"\t\tcontext_type = {picker.context}\n",
        f"\t\tparent_window_token = {picker.parent}\n",
        f'\t\twindow_name = "{picker.key}"\n',
        f"\t\tvisible = {{ {_visible(picker)} }}\n",
        "\t\tai_enabled = { always = no }\n",
        "\t\tdirty = rn_pp_dirty\n" if picker is OWN else "",
        "\t\teffects = {\n",
        f"\t\t\t{picker.key}_apply_click = {{ ROOT = {{ rn_pp_apply = yes }} }}\n",
        _EFFECTS,
        *tab_effects,
        *letter_effects,
        "\t\t}\n",
        "\t\ttriggers = {\n",
        f"\t\t\tcapie_v1_ep__rnpt__{picker.editor}_visible = {{ always = no }}\n",
        (
            f"\t\t\t{picker.key}_apply_click_enabled = {{ ROOT = {{ "
            f"has_country_flag = {picker.open_flag} "
            "check_variable = { rn_pp_sel > 0 } "
            "NOT = { check_variable = { rn_pp_sel = rn_pp_init } } } "
            f"NOT = {{ rn_pp_cooldown_active = yes }} {on} }}\n"
        ),
        "\t\t\trn_pp_reset_visible = { ROOT = { has_country_flag = rn_pp_has_layer } }\n",
        (
            "\t\t\trn_pp_reset_click_enabled = { ROOT = { has_country_flag = rn_pp_has_layer } "
            f"NOT = {{ rn_pp_cooldown_active = yes }} {on} }}\n"
        ),
        _TRIGGERS.replace("@ALL_RULE@", ALL_RULE).replace("@GENERALS_RULE@", GENERALS_RULE),
        *tab_triggers,
        *letter_triggers,
        "\t\t}\n",
        _PROPERTIES_AND_LISTS,
        "\t}\n",
    ]
    return "".join(lines)


def scripted_guis(letters: tuple[int, ...]) -> str:
    """Return the scripted GUI file.

    Args:
        letters: Letter entries.

    Returns:
        Contents of :data:`SCRIPTED_GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Portrait picker (tools/modgen/features/portrait_picker.py). ROOT is the player; THIS\n"
        "# is the country whose leader's portrait changes. The effects (rn_portrait_picker.txt)\n"
        "# re-check the pinned leader, the rights and rules, the cooldown and the CAPIE records.\n"
        "scripted_gui = {\n" + "".join(scripted_gui(p, letters) for p in PICKERS) + "}\n"
    )


def write_files(catalog: PortraitCatalog) -> list[tuple[str, str]]:
    """Return the picker's text files.

    Args:
        catalog: The portrait catalog.

    Returns:
        ``(path relative to mod/, text)`` per file.
    """
    letters = letter_entries(catalog)
    return [(GUI_FILE, gui(letters)), (SCRIPTED_GUI_FILE, scripted_guis(letters))]
