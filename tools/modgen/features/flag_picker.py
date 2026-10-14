"""Flag picker: the "Flag" tab of the politics name editor and of the subject editor.

Two CAPIE grammar editors without text fields (CONTRACT section 3) share one
layout: ``capie_v1_ed__rn__flag`` for the player's own country (politics view,
``player_context``) and ``capie_v1_ed__rn__subflag`` for a country the player may
rename (diplomacy view, ``selected_country_context``). They are grammar editors
so that their Apply carries ``capie_cap`` and ``capie_flag`` (API level 6); the
choice itself lives in script variables on the player (``rn_fp_*``) and the
hand-written effects in ``tools/inline_editor/common/scripted_effects/rn_flag_picker.txt``
do every check again.

Layout (420 px wide, local coordinates; design.txt 5.2 with review K5 and K6)::

    y   0  tabs                              Name | Flag   or  Country | Leader | Party | Flag
    y  36  preview (large flag frame)        grid of 5 x 2 medium flags, or 2 x 5 countries
    y  98  name of the selected flag         Apply, Cancel at x 370 / 396 (as in the editors)
    y 122                                    This country | All countries        < 2 / 4 >
    y 158  A B C ... Z Other                 (country list only)
    y 180  status line
    y 196                                    Restore game flag (only while a layer is set)

Nothing here is a new visual: frames, arrows and buttons are vanilla sprites. The
only own textures are two transparent hit areas for the country rows and the
letters, which vanilla has no small text button for.
"""

from __future__ import annotations

from typing import NamedTuple

from modgen.common import GEN_HEADER
from modgen.features.flags import LETTERS, OTHER_LETTER, FlagCatalog
from modgen.features.textures import TEXTURE_DIR, tga, transparent_px

WIDTH = 420
"""Window width, the same as the name editors."""

HEIGHT = 230
"""Window height: tabs, grid, navigation, letters, status and the Restore button."""

TAB_W = 94
"""Width of a tab button (``GFX_button_94x31``)."""

TAB_PITCH = 96
"""Distance between two tabs, as in the subject editor."""

CONTENT_Y = 36
"""Top of the preview and the grid."""

PREVIEW_FRAME = (0, CONTENT_Y)
"""Position of ``GFX_large_flag_frame`` (92 x 58)."""

PREVIEW_FLAG = (5, CONTENT_Y + 2)
"""Position of the large flag inside the frame (vanilla politics view: frame + (5, 2))."""

NAME_Y = 98
"""Top of the selected flag's name under the preview."""

NAME_W = 100
"""Width of the preview column."""

GRID_X = 104
"""Left edge of the grid and of the country rows."""

CELL = (52, 40)
"""Grid slot: ``GFX_small_flag_frame_selectable`` frame (51 x 36) plus spacing."""

CELL_FLAG = (5, 4)
"""Position of the medium flag (41 x 26) inside the frame (vanilla garrison view)."""

GRID_COLUMNS = 5
"""Flags per grid row."""

GRID_ROWS = 2
"""Grid rows; ten flags per page."""

GRID_W = CELL[0] * GRID_COLUMNS
"""Width of the grid and of the country list."""

ROW = (130, 16)
"""Country row of the "All countries" list."""

ROW_COLUMNS = 2
"""Country rows side by side."""

ROW_ROWS = 5
"""Country rows under each other; ten countries per page."""

NAV_Y = 122
"""Top of the navigation row."""

ARROW = 17
"""Side of ``GFX_opinion_arrow_left`` / ``_right``."""

LETTER_Y = 158
"""Top of the letter row."""

LETTER_W = 14
"""Width of one letter's hit area."""

LETTER_H = 16
"""Height of one letter's hit area."""

OTHER_X = 368
"""Left edge of the "Other" entry after Z."""

OTHER_W = 52
"""Width of the "Other" entry."""

STATUS_Y = 180
"""Top of the status line."""

APPLY_X = 370
"""X of Apply, the same as in the name editors."""

CANCEL_X = 396
"""X of Cancel, the same as in the name editors."""

RESET_POS = (297, 196)
"""Position of "Restore game flag" (``GFX_button_123x34``), right-aligned like "Restore name"."""

HIT_ROW_SPRITE = "GFX_rn_hit_row"
"""Transparent hit area of a country row."""

HIT_LETTER_SPRITE = "GFX_rn_hit_letter"
"""Transparent hit area of a letter."""

GFX_FILE = "interface/rn_flag_picker.gfx"
"""Sprite file of the hit areas, relative to ``mod/``."""

GUI_FILE = "interface/rn_flag_picker.gui"
"""Window file, relative to ``mod/``."""

SCRIPTED_GUI_FILE = "common/scripted_guis/rn_flag_picker.txt"
"""Scripted GUI file, relative to ``mod/``."""

ALL_RULE = "has_game_rule = { rule = rn_flag_pool option = RN_FLAG_POOL_ALL }"
"""Trigger: the game rule allows every flag."""


class Picker(NamedTuple):
    """One of the two flag editors."""

    editor: str
    """CAPIE editor id (``flag`` or ``subflag``)."""

    context: str
    """Scripted GUI ``context_type``."""

    parent: str
    """``parent_window_token``."""

    position: tuple[int, int]
    """Window position in the parent view (the name editor's)."""

    open_flag: str
    """Country flag on the player while this picker is open."""

    tabs: tuple[tuple[str, str, str], ...]
    """Tabs as ``(element suffix, text key, tooltip key)``; the ``flag`` tab is the open one."""

    @property
    def key(self) -> str:
        """Return the scripted GUI key and window name.

        Returns:
            ``capie_v1_ed__rn__<editor>``.
        """
        return f"capie_v1_ed__rn__{self.editor}"


OWN = Picker(
    "flag",
    "player_context",
    "politics_tab",
    (18, 28),
    "rn_fp_open_own",
    (
        ("name", "RN_FP_TAB_NAME", "RN_FP_TAB_NAME_TT"),
        ("flag", "RN_FP_TAB_FLAG", "RN_FP_TAB_FLAG_TT"),
    ),
)
"""Own country: in the politics view, where the country name editor opens."""

SUBJECT = Picker(
    "subflag",
    "selected_country_context",
    "selected_country_view_diplomacy",
    (65, 37),
    "rn_fp_open_sub",
    (
        ("country", "RN_SUB_TAB_COUNTRY", "RN_SUB_TAB_COUNTRY_TT"),
        ("leader", "RN_SUB_TAB_LEADER", "RN_SUB_TAB_LEADER_TT"),
        ("party", "RN_SUB_TAB_PARTY", "RN_SUB_TAB_PARTY_TT"),
        ("flag", "RN_FP_TAB_FLAG", "RN_FP_TAB_FLAG_TT"),
    ),
)
"""Another country (subject, or any country for the host): in its diplomacy view."""

PICKERS = (OWN, SUBJECT)
"""Both editors."""


def letter_x(n: int) -> int:
    """Return the left edge of letter ``n`` (1-based) or of "Other".

    Args:
        n: 1..26, or :data:`~modgen.features.flags.OTHER_LETTER`.

    Returns:
        X position.
    """
    return OTHER_X if n == OTHER_LETTER else (n - 1) * LETTER_W


def _text(
    name: str, pos: tuple[int, int], text: str, size: tuple[int, int], *, extra: str = ""
) -> str:
    """Return one ``instantTextBoxType`` block.

    Args:
        name: Element name.
        pos: Position.
        text: Localisation key.
        size: ``maxWidth`` and ``maxHeight``.
        extra: Additional attribute lines (already indented).

    Returns:
        The block, indented for a window body.
    """
    return (
        f'\t\tinstantTextboxType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\tfont = "Arial12"\n\t\t\ttext = "{text}"\n'
        f"\t\t\tmaxWidth = {size[0]}\n\t\t\tmaxHeight = {size[1]}\n"
        f"\t\t\tfixedsize = yes\n{extra}\t\t\talwaystransparent = yes\n\t\t}}\n"
    )


def _button(
    name: str, pos: tuple[int, int], sprite: str, *, attrs: str = "", quad: bool = False
) -> str:
    """Return one ``buttonType`` block.

    Args:
        name: Element name.
        pos: Position.
        sprite: Sprite name (vanilla or a hit area).
        attrs: Additional attribute lines (already indented).
        quad: Use ``quadTextureSprite`` (a framed sprite) instead of ``spriteType``.

    Returns:
        The block, indented for a window body.
    """
    kind = "quadTextureSprite" if quad else "spriteType"
    return (
        f'\t\tbuttonType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\t{kind} = "{sprite}"\n{attrs}\t\t\tclicksound = click_default\n\t\t}}\n'
    )


def _icon(name: str, pos: tuple[int, int], sprite: str, *, attrs: str = "") -> str:
    """Return one ``iconType`` block.

    Args:
        name: Element name.
        pos: Position.
        sprite: Sprite (``spriteType``, or ``quadTextureSprite`` for a framed sprite in attrs).
        attrs: Additional attribute lines (already indented).

    Returns:
        The block, indented for a window body.
    """
    return (
        f'\t\ticonType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\tspriteType = "{sprite}"\n{attrs}\t\t}}\n'
    )


def _captioned(text: str, tip: str) -> str:
    """Return the caption, font and tooltip lines of a text button.

    Args:
        text: Caption key.
        tip: Tooltip key.

    Returns:
        Attribute lines.
    """
    return (
        f'\t\t\tbuttonText = "{text}"\n\t\t\tbuttonFont = "hoi_16mbs"\n'
        f'\t\t\tpdx_tooltip = "{tip}"\n'
    )


def _tab_buttons(picker: Picker) -> str:
    """Return the tab row of one picker.

    Args:
        picker: The editor.

    Returns:
        Button blocks.
    """
    return "".join(
        _button(
            f"rn_fp_{picker.editor}_tab_{suffix}",
            (i * TAB_PITCH, 0),
            "GFX_button_94x31",
            attrs=_captioned(text, tip),
        )
        for i, (suffix, text, tip) in enumerate(picker.tabs)
    )


def _letters(letters: tuple[int, ...]) -> str:
    """Return the letter row: a hit area and a normal and an active caption per entry.

    Args:
        letters: Entries with countries (1..26) and, when it has flags, the "Other" entry.

    Returns:
        Element blocks.
    """
    out = []
    for n in letters:
        x = letter_x(n)
        w = OTHER_W if n == OTHER_LETTER else LETTER_W
        if n == OTHER_LETTER:
            sprite, key = "GFX_rn_hit_other", "RN_FP_OTHER"
            attrs = f'\t\t\tpdx_tooltip = "{key}_TT"\n'
        else:
            sprite, key, attrs = HIT_LETTER_SPRITE, f"RN_FP_L_{LETTERS[n - 1]}", ""
        out.append(_button(f"rn_fp_letter_{n}", (x, LETTER_Y), sprite, attrs=attrs))
        fmt = "\t\t\tformat = centre\n"
        out.append(_text(f"rn_fp_lt_{n}", (x, LETTER_Y + 1), key, (w, 14), extra=fmt))
        out.append(_text(f"rn_fp_lta_{n}", (x, LETTER_Y + 1), f"{key}_ON", (w, 14), extra=fmt))
    return "".join(out)


def _gridbox(name: str, slot: tuple[int, int], columns: int, rows: int) -> str:
    """Return a ``gridBoxType`` at the grid position.

    Args:
        name: Dynamic list name.
        slot: Slot size.
        columns: Slots per row.
        rows: Rows.

    Returns:
        The block.
    """
    return (
        f'\t\tgridBoxType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {GRID_X} y = {CONTENT_Y} }}\n"
        f"\t\t\tsize = {{ width = {slot[0] * columns} height = {slot[1] * rows} }}\n"
        f"\t\t\tslotsize = {{ width = {slot[0]} height = {slot[1]} }}\n"
        f'\t\t\tmax_slots_horizontal = {columns}\n\t\t\tformat = "UPPER_LEFT"\n\t\t}}\n'
    )


def window(picker: Picker, letters: tuple[int, ...]) -> str:
    """Return the window of one picker.

    Args:
        picker: The editor.
        letters: Letter entries to draw (see :func:`_letters`).

    Returns:
        The ``containerWindowType`` block.
    """
    x, y = picker.position
    arrow_y = NAV_Y + 7
    parts = [
        f'\tcontainerWindowType = {{\n\t\tname = "{picker.key}"\n',
        f"\t\tposition = {{ x = {x} y = {y} }}\n",
        f"\t\tsize = {{ width = {WIDTH} height = {HEIGHT} }}\n",
        "\t\torientation = upper_left\n\t\tclipping = no\n",
        '\t\tbackground = { name = "Background" quadTextureSprite = "GFX_generic_bg2" }\n',
        "\t\t# CAPIE epoch carrier (hidden).\n",
        _text(f"capie_v1_ep__rn__{picker.editor}", (0, 0), "[?ROOT.rn_fp_epoch|0]", (120, 14)),
        _tab_buttons(picker),
        "\t\t# Preview: the selected flag (large sprite) in the vanilla large flag frame.\n",
        _icon("rn_fp_preview", PREVIEW_FLAG, "GFX_rnf_1"),
        _icon(
            "rn_fp_frame",
            PREVIEW_FRAME,
            "GFX_large_flag_frame",
            attrs="\t\t\talwaystransparent = yes\n",
        ),
        _text("rn_fp_name", (0, NAME_Y), "RN_FP_NAME", (NAME_W, 26)),
        _text("rn_fp_note_current", (0, NAME_Y + 26), "RN_FP_NOTE_CURRENT", (NAME_W, 14)),
        _text("rn_fp_note_overlord", (0, NAME_Y + 26), "RN_FP_NOTE_OVERLORD", (NAME_W, 14)),
        "\t\t# Flags of one pool (rn_fp_grid) or countries (rn_fp_rows_grid), ten per page.\n",
        _gridbox("rn_fp_grid", CELL, GRID_COLUMNS, GRID_ROWS),
        _gridbox("rn_fp_rows_grid", ROW, ROW_COLUMNS, ROW_ROWS),
        _text("rn_fp_empty", (GRID_X, CONTENT_Y + 32), "RN_FP_EMPTY", (GRID_W, 14)),
        _button(
            f"{picker.key}_apply",
            (APPLY_X, CONTENT_Y + 3),
            "GFX_preset_button_save",
            attrs=(
                "\t\t\tscale = 0.67 # 20x20\n"
                '\t\t\tpdx_tooltip = "RN_FP_APPLY_TT"\n\t\t\tshortcut = "RETURN"\n'
            ),
            quad=True,
        ),
        _button(
            "rn_fp_cancel",
            (CANCEL_X, CONTENT_Y + 5),
            "GFX_closebutton_16",
            attrs='\t\t\tpdx_tooltip = "RN_IP_CANCEL"\n',
            quad=True,
        ),
        "\t\t# Navigation: this country's pool or every country (game rule), pages.\n",
        _button(
            "rn_fp_nav_own",
            (GRID_X, NAV_Y),
            "GFX_button_94x31",
            attrs=_captioned("RN_FP_NAV_OWN", "RN_FP_NAV_OWN_TT"),
        ),
        _button(
            "rn_fp_nav_all",
            (GRID_X + TAB_PITCH, NAV_Y),
            "GFX_button_94x31",
            attrs=_captioned("RN_FP_NAV_ALL", "RN_FP_NAV_ALL_TT"),
        ),
        _button(
            "rn_fp_prev",
            (296, arrow_y),
            "GFX_opinion_arrow_left",
            attrs='\t\t\tpdx_tooltip = "RN_FP_PREV_TT"\n',
        ),
        _text(
            "rn_fp_page",
            (313, arrow_y + 1),
            "RN_FP_PAGE",
            (34, 14),
            extra="\t\t\tformat = centre\n",
        ),
        _button(
            "rn_fp_next",
            (347, arrow_y),
            "GFX_opinion_arrow_right",
            attrs='\t\t\tpdx_tooltip = "RN_FP_NEXT_TT"\n',
        ),
        "\t\t# Letters of the country list (English names, the same for every player).\n",
        _letters(letters),
        _text("rn_fp_status", (6, STATUS_Y), "[This.RN_FP_STATUS]", (WIDTH - 12, 14)),
        "\t\t# Restore game flag: removes the flag layer (only while one is set).\n",
        _button(
            "rn_fp_reset",
            RESET_POS,
            "GFX_button_123x34",
            attrs=_captioned("RN_FP_RESET", "RN_FP_RESET_TT"),
        ),
        "\t}\n",
    ]
    return "".join(parts)


def entries() -> str:
    """Return the two list entries: a flag cell and a country row.

    Returns:
        The two ``containerWindowType`` blocks.
    """
    cell = (
        '\tcontainerWindowType = {\n\t\tname = "rn_fp_cell"\n'
        f"\t\tsize = {{ width = {CELL[0]} height = {CELL[1]} }}\n\t\tclipping = no\n"
        + _button("rn_fp_cell_flag", CELL_FLAG, "GFX_rnfm_1")
        + _icon(
            "rn_fp_cell_frame",
            (0, 0),
            "GFX_small_flag_frame_selectable",
            attrs="\t\t\tframe = 1\n\t\t\talwaystransparent = yes\n",
        )
        + _icon(
            "rn_fp_cell_sel",
            (0, 0),
            "GFX_small_flag_frame_selectable",
            attrs="\t\t\tframe = 2\n\t\t\talwaystransparent = yes\n",
        )
        + "\t}\n"
    )
    row = (
        '\tcontainerWindowType = {\n\t\tname = "rn_fp_row"\n'
        f"\t\tsize = {{ width = {ROW[0]} height = {ROW[1]} }}\n\t\tclipping = no\n"
        + _button("rn_fp_row_hit", (0, 0), HIT_ROW_SPRITE)
        + _text("rn_fp_row_name", (2, 1), "RN_FP_ROW", (ROW[0] - 4, 14))
        + _text("rn_fp_row_name_on", (2, 1), "RN_FP_ROW_ON", (ROW[0] - 4, 14))
        + "\t}\n"
    )
    return cell + row


def letter_entries(catalog: FlagCatalog) -> tuple[int, ...]:
    """Return the letter entries the catalog needs.

    Args:
        catalog: The catalog.

    Returns:
        Letters that have countries, then "Other" when its group has flags.
    """
    out = [n for n, tags in enumerate(catalog.letters, start=1) if tags]
    if catalog.groups and catalog.groups[-1].indices:
        out.append(OTHER_LETTER)
    return tuple(out)


def gui(letters: tuple[int, ...]) -> str:
    """Return the window file.

    Args:
        letters: Letter entries (:func:`letter_entries`).

    Returns:
        Contents of :data:`GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Flag picker (tools/modgen/features/flag_picker.py): own country in the politics\n"
        "# view, another country in its diplomacy view. Vanilla sprites only, apart from\n"
        "# transparent hit areas.\n"
        "guiTypes = {\n" + "".join(window(p, letters) for p in PICKERS) + entries() + "}\n"
    )


def gfx() -> str:
    """Return the hit area sprites.

    Returns:
        Contents of :data:`GFX_FILE`.
    """
    sprites = [
        (HIT_ROW_SPRITE, "rn_hit_row.tga"),
        (HIT_LETTER_SPRITE, "rn_hit_letter.tga"),
        ("GFX_rn_hit_other", "rn_hit_other.tga"),
    ]
    body = "".join(
        f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{TEXTURE_DIR}/{file}"\n'
        '\t\tnoOfFrames = 1\n\t\teffectFile = "gfx/FX/buttonstate.lua"\n\t}\n'
        for name, file in sprites
    )
    return GEN_HEADER + "spriteTypes = {\n" + body + "}\n"


def textures() -> dict[str, bytes]:
    """Return the transparent hit area textures.

    Returns:
        File name (in :data:`~modgen.features.textures.TEXTURE_DIR`) to TGA bytes.
    """
    return {
        "rn_hit_row.tga": tga(ROW[0], ROW[1], transparent_px),
        "rn_hit_letter.tga": tga(LETTER_W, LETTER_H, transparent_px),
        "rn_hit_other.tga": tga(OTHER_W, LETTER_H, transparent_px),
    }


# ----------------------------------------------------------------------------- scripted GUI

_ROOT_OK = "is_ai = no NOT = { has_country_flag = rn_open } NOT = { has_country_flag = rn_input }"
"""Player state every picker click needs (no legacy window, no keyboard)."""


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
            "is_in_array = { array = rn_fp_target_arr value = THIS }"
        )
    return (
        "NOT = { tag = ROOT } rn_sub_may_edit = yes "
        "is_in_array = { array = ROOT.rn_fp_target_arr value = THIS } "
        f"ROOT = {{ {_ROOT_OK} has_country_flag = {picker.open_flag} }}"
    )


def _switched_on(feature: str, picker: Picker | None = None) -> str:
    """Return the host-switch condition of a tab or button (ADR-0036).

    Args:
        feature: Feature id (``country``, ``leader``, ``party`` or ``flag``).
        picker: The editor; another country also needs the "other countries" switch.
            None for the subject tabs, which are always about another country.

    Returns:
        Trigger text.
    """
    out = f"NOT = {{ rn_feature_{feature}_off = yes }}"
    if picker is not OWN:
        out += " NOT = { rn_feature_subjects_off = yes }"
    return out


def _tab_effects(picker: Picker) -> list[str]:
    """Return the tab click effects (the flag tab itself is disabled).

    Args:
        picker: The editor.

    Returns:
        Effect lines.
    """
    prefix = f"rn_fp_{picker.editor}_tab_"
    if picker is OWN:
        return [
            (
                f"\t\t\t{prefix}name_click = "
                "{ ROOT = { rn_fp_to_name_editor = yes rn_ip_status_clear = yes } }\n"
            ),
        ]
    limit = f"rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }}"
    return [
        f"\t\t\t{prefix}{suffix}_click = {{\n"
        f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {limit} {_switched_on(suffix)} }}\n"
        "\t\t\t\t\tROOT = { rn_fp_close = yes }\n\t\t\t\t\trn_sub_open_common = yes\n"
        f"\t\t\t\t\tROOT = {{ set_country_flag = rn_sub_open_{suffix} }}\n"
        "\t\t\t\t}\n\t\t\t}\n"
        for suffix in ("country", "leader", "party")
    ]


def _tab_triggers(picker: Picker) -> list[str]:
    """Return the tab enabled triggers.

    Args:
        picker: The editor.

    Returns:
        Trigger lines.
    """
    prefix = f"rn_fp_{picker.editor}_tab_"
    out = [f"\t\t\t{prefix}flag_click_enabled = {{ always = no }}\n"]
    if picker is OWN:
        out.append(
            f"\t\t\t{prefix}name_click_enabled = "
            "{ NOT = { rn_ip_cooldown_active_country = yes } "
            "NOT = { rn_feature_country_off = yes } }\n"
        )
    else:
        out += [
            f"\t\t\t{prefix}{s}_click_enabled = "
            f"{{ rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }} {_switched_on(s)} }}\n"
            for s in ("country", "leader", "party")
        ]
    return out


def _letter_lines(letters: tuple[int, ...]) -> tuple[list[str], list[str]]:
    """Return the letter click effects and their triggers.

    Args:
        letters: Letter entries (:func:`letter_entries`).

    Returns:
        ``(effects, triggers)``.
    """
    effects: list[str] = []
    triggers: list[str] = []
    shown = (
        f"{ALL_RULE} ROOT = {{ OR = {{ check_variable = {{ rn_fp_view = 2 }} "
        "has_country_flag = rn_fp_view_other } }"
    )
    for n in letters:
        effects.append(
            f"\t\t\trn_fp_letter_{n}_click = {{ ROOT = {{ set_temp_variable = {{ rn_fp_lt = {n} }} "
            "rn_fp_pick_letter = yes } }\n"
        )
        on = f"check_variable = {{ rn_fp_letter = {n} }}"
        triggers += [
            f"\t\t\trn_fp_letter_{n}_visible = {{ {shown} }}\n",
            f"\t\t\trn_fp_letter_{n}_click_enabled = {{ ROOT = {{ NOT = {{ {on} }} }} }}\n",
            f"\t\t\trn_fp_lt_{n}_visible = {{ {shown} ROOT = {{ NOT = {{ {on} }} }} }}\n",
            f"\t\t\trn_fp_lta_{n}_visible = {{ {shown} ROOT = {{ {on} }} }}\n",
        ]
    return effects, triggers


def scripted_gui(picker: Picker, letters: tuple[int, ...]) -> str:
    """Return the scripted GUI of one picker.

    Args:
        picker: The editor.
        letters: Letter entries (:func:`letter_entries`).

    Returns:
        The ``<key> = { ... }`` block.
    """
    letter_effects, letter_triggers = _letter_lines(letters)
    dirty = "\t\tdirty = rn_fp_dirty\n" if picker is OWN else ""
    lines = [
        f"\t{picker.key} = {{\n",
        f"\t\tcontext_type = {picker.context}\n",
        f"\t\tparent_window_token = {picker.parent}\n",
        f'\t\twindow_name = "{picker.key}"\n',
        f"\t\tvisible = {{ {_visible(picker)} }}\n",
        "\t\tai_enabled = { always = no }\n",
        dirty,
        "\t\teffects = {\n",
        f"\t\t\t{picker.key}_apply_click = {{ ROOT = {{ rn_fp_apply = yes }} }}\n",
        _EFFECTS,
        *_tab_effects(picker),
        *letter_effects,
        "\t\t}\n",
        "\t\ttriggers = {\n",
        f"\t\t\tcapie_v1_ep__rn__{picker.editor}_visible = {{ always = no }}\n",
        (
            f"\t\t\t{picker.key}_apply_click_enabled = {{ ROOT = {{ "
            f"has_country_flag = {picker.open_flag} {_SEL_CHANGED} }} "
            f"NOT = {{ rn_fp_cooldown_active = yes }} {_switched_on('flag', picker)} }}\n"
        ),
        _TRIGGERS.replace("@ALL_RULE@", ALL_RULE),
        *_tab_triggers(picker),
        *letter_triggers,
        "\t\t}\n",
        _PROPERTIES_AND_LISTS,
        "\t}\n",
    ]
    return "".join(lines)


_SEL_CHANGED = (
    "check_variable = { rn_fp_sel > 0 } NOT = { check_variable = { rn_fp_sel = rn_fp_init } }"
)
"""Trigger: a flag other than the current one is selected."""

_EFFECTS = """\t\t\trn_fp_cancel_click = { ROOT = { rn_fp_close = yes rn_cv1_status_clear = yes } }
\t\t\trn_fp_reset_click = { ROOT = { rn_fp_reset = yes } }
\t\t\trn_fp_cell_flag_click = { set_temp_variable = { rn_fp_pick = rn_fp_v } ROOT = { rn_fp_pick_cell = yes } }
\t\t\trn_fp_row_hit_click = { rn_fp_pick_country = yes }
\t\t\trn_fp_nav_own_click = { ROOT = { rn_fp_show_target = yes } }
\t\t\trn_fp_nav_all_click = { ROOT = { rn_fp_show_list = yes } }
\t\t\trn_fp_prev_click = { ROOT = { set_temp_variable = { rn_fp_step = -1 } rn_fp_page_step = yes } }
\t\t\trn_fp_next_click = { ROOT = { set_temp_variable = { rn_fp_step = 1 } rn_fp_page_step = yes } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Click effects both pickers share (Apply and the tabs are per picker)."""

_TRIGGERS = """\t\t\trn_fp_reset_visible = { has_variable = capie_cf_ver }
\t\t\trn_fp_reset_click_enabled = { has_variable = capie_cf_ver NOT = { rn_fp_cooldown_active = yes } NOT = { rn_feature_flag_off = yes } }
\t\t\trn_fp_preview_visible = { ROOT = { check_variable = { rn_fp_sel > 0 } } }
\t\t\trn_fp_name_visible = { ROOT = { check_variable = { rn_fp_sel > 0 } } }
\t\t\trn_fp_note_current_visible = { ROOT = { check_variable = { rn_fp_sel > 0 } check_variable = { rn_fp_sel = rn_fp_init } } }
\t\t\trn_fp_note_overlord_visible = { ROOT = { check_variable = { rn_fp_ovl > 0 } check_variable = { rn_fp_sel = rn_fp_ovl } NOT = { check_variable = { rn_fp_sel = rn_fp_init } } } }
\t\t\trn_fp_grid_visible = { ROOT = { check_variable = { rn_fp_view = 1 } } }
\t\t\trn_fp_rows_grid_visible = { ROOT = { check_variable = { rn_fp_view = 2 } } }
\t\t\trn_fp_empty_visible = { ROOT = { check_variable = { rn_fp_view = 1 } check_variable = { rn_fp_cells^num = 0 } } }
\t\t\trn_fp_cell_sel_visible = { check_variable = { rn_fp_v = ROOT.rn_fp_sel } }
\t\t\trn_fp_row_name_visible = { NOT = { is_in_array = { array = ROOT.rn_fp_src_arr value = THIS } } }
\t\t\trn_fp_row_name_on_visible = { is_in_array = { array = ROOT.rn_fp_src_arr value = THIS } }
\t\t\trn_fp_nav_own_visible = { @ALL_RULE@ }
\t\t\trn_fp_nav_own_click_enabled = { ROOT = { NOT = { has_country_flag = rn_fp_view_target } } }
\t\t\trn_fp_nav_all_visible = { @ALL_RULE@ }
\t\t\trn_fp_nav_all_click_enabled = { ROOT = { NOT = { check_variable = { rn_fp_view = 2 } } } }
\t\t\trn_fp_prev_visible = { ROOT = { check_variable = { rn_fp_pages > 1 } } }
\t\t\trn_fp_next_visible = { ROOT = { check_variable = { rn_fp_pages > 1 } } }
\t\t\trn_fp_page_visible = { ROOT = { check_variable = { rn_fp_pages > 1 } } }
\t\t\trn_fp_prev_click_enabled = { ROOT = { check_variable = { rn_fp_page > 0 } } }
\t\t\trn_fp_next_click_enabled = { ROOT = { check_variable = { rn_fp_page_disp < rn_fp_pages } } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Visible and enabled triggers both pickers share; ``@ALL_RULE@`` is :data:`ALL_RULE`."""

_PROPERTIES_AND_LISTS = """\t\tproperties = {
\t\t\trn_fp_preview = { image = "GFX_rnf_[?ROOT.rn_fp_sel|0]" }
\t\t\trn_fp_cell_flag = { image = "GFX_rnfm_[?rn_fp_v|0]" }
\t\t}
\t\tdynamic_lists = {
\t\t\trn_fp_grid = {
\t\t\t\tarray = ROOT.rn_fp_cells
\t\t\t\tvalue = rn_fp_v
\t\t\t\tchange_scope = no
\t\t\t\tentry_container = "rn_fp_cell"
\t\t\t}
\t\t\trn_fp_rows_grid = {
\t\t\t\tarray = ROOT.rn_fp_rows
\t\t\t\tchange_scope = yes
\t\t\t\tentry_container = "rn_fp_row"
\t\t\t}
\t\t}
"""
"""Flag images by catalog index (review K6: medium sprites in the grid) and the two lists."""


def scripted_guis(letters: tuple[int, ...]) -> str:
    """Return the scripted GUI file.

    Args:
        letters: Letter entries (:func:`letter_entries`).

    Returns:
        Contents of :data:`SCRIPTED_GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Flag picker (tools/modgen/features/flag_picker.py). ROOT is the player in both\n"
        "# editors; THIS is the country whose flag changes (the player in the politics view,\n"
        "# the selected country in its diplomacy view). The effects (rn_flag_picker.txt)\n"
        "# re-check the pinned target, the rights, the cooldown, the CAPIE records and the\n"
        "# pool; a click never trusts the command scope.\n"
        "scripted_gui = {\n" + "".join(scripted_gui(p, letters) for p in PICKERS) + "}\n"
    )


def write_files(catalog: FlagCatalog) -> list[tuple[str, str]]:
    """Return the picker's text files.

    Args:
        catalog: The flag catalog (its letters decide the letter row).

    Returns:
        ``(path relative to mod/, text)`` per file.
    """
    letters = letter_entries(catalog)
    return [
        (GFX_FILE, gfx()),
        (GUI_FILE, gui(letters)),
        (SCRIPTED_GUI_FILE, scripted_guis(letters)),
    ]
