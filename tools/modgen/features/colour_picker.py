"""Colour picker: the "Colour" tab of the politics name editor and the subject's map colour.

Two CAPIE grammar editors without text fields (CONTRACT section 3) share one
layout: ``capie_v1_ed__rncc__colour`` for the player's own country (politics view,
``player_context``) and ``capie_v1_ed__rncc__subcolour`` for a country the player
may rename (diplomacy view, ``selected_country_context``). They are grammar
editors so that their Apply carries ``capie_cap`` and ``capie_colour`` (API level
8, CONTRACT section 19); the choice lives in script variables on the player
(``rn_cp_*``) and the hand-written effects in
``tools/inline_editor/common/scripted_effects/rn_colour_picker.txt`` check
everything again. The editors use their own mod id ``rncc`` (at most eight
editors per mod id).

Layout (420 px wide, local coordinates, the same frame as the flag picker)::

    y   0  tabs                  Name | Flag | Colour   or  Country | Leader | Party | Flag
    y  36  preview (40 x 40)     grid of 8 x 3 preset swatches      Apply, Cancel
    y  86  label, note
    y 116                        Red    -16 -1  value  +1 +16
    y 136                        Green  ...
    y 156                        Blue   ...
    y 180  status line
    y 192                        Original colour (only while a colour is set)

The preview is the 512-frame strip of :mod:`modgen.features.colours` (3 bits per
channel); the exact colour shows on the map after Apply.
"""

from __future__ import annotations

from typing import NamedTuple

from modgen.common import GEN_HEADER
from modgen.features.colours import MARK_SPRITE, PRESETS, PREVIEW_SPRITE, swatch_sprite
from modgen.features.picker_common import button, captioned, icon, text

WIDTH = 420
"""Window width, the same as the name editors."""

HEIGHT = 228
"""Window height: tabs, grid, channels, status and the Restore button."""

TAB_PITCH = 96
"""Distance between two tabs, as in the subject editor."""

CONTENT_Y = 36
"""Top of the preview and the grid."""

PREVIEW_POS = (6, 40)
"""Position of the preview."""

PREVIEW_SCALE = 5
"""Scale of the 8 x 8 preview frame (40 x 40 on screen)."""

RGB_Y = 86
"""Top of the R G B numbers under the preview."""

NOTE_Y = 102
"""Top of the note under the numbers."""

LEFT_W = 100
"""Width of the preview column."""

GRID_X = 104
"""Left edge of the swatch grid and of the channel rows."""

CELL = (28, 24)
"""Grid slot: the selection mark; the swatch sits 2 px inside."""

GRID_COLUMNS = 8
"""Swatches per row."""

CHANNEL_Y = 116
"""Top of the first channel row."""

CHANNEL_PITCH = 20
"""Distance between two channel rows."""

LABEL_W = 70
"""Width of a channel label."""

STEP_W = 26
"""Width of one stepper hit area."""

STEPS = (("m16", -16, 176), ("m1", -1, 204), ("p1", 1, 268), ("p16", 16, 296))
"""Steppers: element suffix, step and x position."""

VALUE_POS = 232
"""X of the channel value."""

VALUE_W = 34
"""Width of the channel value."""

CHANNELS = (("r", "RN_CP_RED"), ("g", "RN_CP_GREEN"), ("b", "RN_CP_BLUE"))
"""Channel ids and label keys, in row order."""

STATUS_Y = 180
"""Top of the status line."""

APPLY_X = 370
"""X of Apply, the same as in the name editors."""

CANCEL_X = 396
"""X of Cancel, the same as in the name editors."""

RESET_POS = (297, 192)
"""Position of "Restore colour" (``GFX_button_123x34``)."""

STEP_SPRITE = "GFX_rn_hit_step"
"""Transparent hit area of a stepper (``picker_common.HIT_SPRITES``)."""

GUI_FILE = "interface/rn_colour_picker.gui"
"""Window file, relative to ``mod/``."""

SCRIPTED_GUI_FILE = "common/scripted_guis/rn_colour_picker.txt"
"""Scripted GUI file, relative to ``mod/``."""

ON_ACTIONS_FILE = "common/on_actions/rn_colour_on_actions.txt"
"""Daily checks, relative to ``mod/``."""


class Picker(NamedTuple):
    """One of the two colour editors."""

    editor: str
    """CAPIE editor id (``colour`` or ``subcolour``)."""

    context: str
    """Scripted GUI ``context_type``."""

    parent: str
    """``parent_window_token``."""

    position: tuple[int, int]
    """Window position in the parent view (the name editor's)."""

    open_flag: str
    """Country flag on the player while this picker is open."""

    tabs: tuple[tuple[str, str, str], ...]
    """Tabs as ``(element suffix, text key, tooltip key)``; the ``colour`` tab is the open one."""

    @property
    def key(self) -> str:
        """Return the scripted GUI key and window name.

        Returns:
            ``capie_v1_ed__rncc__<editor>``.
        """
        return f"capie_v1_ed__rncc__{self.editor}"


OWN = Picker(
    "colour",
    "player_context",
    "politics_tab",
    (18, 28),
    "rn_cp_open_own",
    (
        ("name", "RN_FP_TAB_NAME", "RN_FP_TAB_NAME_TT"),
        ("flag", "RN_FP_TAB_FLAG", "RN_FP_TAB_FLAG_TT"),
        ("colour", "RN_CP_TAB", "RN_CP_TAB_TT"),
    ),
)
"""Own country: in the politics view, where the country name editor opens."""

SUBJECT = Picker(
    "subcolour",
    "selected_country_context",
    "selected_country_view_diplomacy",
    (65, 37),
    "rn_cp_open_sub",
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


def cell_pos(n: int) -> tuple[int, int]:
    """Return the top-left corner of preset ``n``'s grid slot.

    Args:
        n: Preset number, 1-based.

    Returns:
        Position.
    """
    col, row = (n - 1) % GRID_COLUMNS, (n - 1) // GRID_COLUMNS
    return GRID_X + col * CELL[0], CONTENT_Y + row * CELL[1]


def _tab_buttons(picker: Picker) -> str:
    """Return the tab row of one picker.

    Args:
        picker: The editor.

    Returns:
        Button blocks.
    """
    return "".join(
        button(
            f"rn_cp_{picker.editor}_tab_{suffix}",
            (i * TAB_PITCH, 0),
            "GFX_button_94x31",
            attrs=captioned(label, tip),
        )
        for i, (suffix, label, tip) in enumerate(picker.tabs)
    )


def _swatches() -> str:
    """Return the preset grid: a swatch button and a selection mark per preset.

    Returns:
        Element blocks.
    """
    out = []
    for n in range(1, len(PRESETS) + 1):
        x, y = cell_pos(n)
        out.append(
            button(
                f"rn_cp_sw_{n}",
                (x + 2, y + 2),
                swatch_sprite(n),
                attrs=f'\t\t\tpdx_tooltip = "RN_CP_SW_{n}"\n',
            )
        )
        out.append(
            icon(
                f"rn_cp_mark_{n}",
                (x, y),
                MARK_SPRITE,
                attrs="\t\t\talwaystransparent = yes\n",
            )
        )
    return "".join(out)


def _channels() -> str:
    """Return the three channel rows: label, four steppers and the value.

    Returns:
        Element blocks.
    """
    out = []
    fmt = "\t\t\tformat = centre\n"
    for row, (c, label) in enumerate(CHANNELS):
        y = CHANNEL_Y + row * CHANNEL_PITCH
        out.append(text(f"rn_cp_{c}_label", (GRID_X, y + 1), label, (LABEL_W, 14)))
        for suffix, _step, x in STEPS:
            name = f"rn_cp_{c}_{suffix}"
            out.append(
                button(name, (x, y), STEP_SPRITE, attrs='\t\t\tpdx_tooltip = "RN_CP_STEP_TT"\n')
            )
            key = f"RN_CP_STEP_{suffix.upper()}"
            out.append(text(f"{name}_t", (x, y + 1), key, (STEP_W, 14), extra=fmt))
        value = f"[?ROOT.rn_cp_{c}|0]"
        out.append(text(f"rn_cp_{c}_value", (VALUE_POS, y + 1), value, (VALUE_W, 14), extra=fmt))
    return "".join(out)


def window(picker: Picker) -> str:
    """Return the window of one picker.

    Args:
        picker: The editor.

    Returns:
        The ``containerWindowType`` block.
    """
    x, y = picker.position
    parts = [
        f'\tcontainerWindowType = {{\n\t\tname = "{picker.key}"\n',
        f"\t\tposition = {{ x = {x} y = {y} }}\n",
        f"\t\tsize = {{ width = {WIDTH} height = {HEIGHT} }}\n",
        "\t\torientation = upper_left\n\t\tclipping = no\n",
        '\t\tbackground = { name = "Background" quadTextureSprite = "GFX_generic_bg2" }\n',
        "\t\t# CAPIE epoch carrier (hidden).\n",
        text(f"capie_v1_ep__rncc__{picker.editor}", (0, 0), "[?ROOT.rn_cp_epoch|0]", (120, 14)),
        _tab_buttons(picker),
        "\t\t# Preview of the picked colour (3 bits per channel; the map shows it exactly).\n",
        icon(
            "rn_cp_preview",
            PREVIEW_POS,
            PREVIEW_SPRITE,
            attrs=f"\t\t\tscale = {PREVIEW_SCALE}\n\t\t\talwaystransparent = yes\n",
        ),
        text("rn_cp_rgb", (0, RGB_Y), "RN_CP_RGB", (LEFT_W, 14)),
        text("rn_cp_note_game", (0, NOTE_Y), "RN_CP_NOTE_GAME", (LEFT_W, 28)),
        text("rn_cp_note_current", (0, NOTE_Y), "RN_CP_NOTE_CURRENT", (LEFT_W, 28)),
        text("rn_cp_note_new", (0, NOTE_Y), "RN_CP_NOTE_NEW", (LEFT_W, 28)),
        "\t\t# Preset swatches.\n",
        _swatches(),
        button(
            f"{picker.key}_apply",
            (APPLY_X, CONTENT_Y + 3),
            "GFX_preset_button_save",
            attrs=(
                "\t\t\tscale = 0.67 # 20x20\n"
                '\t\t\tpdx_tooltip = "RN_CP_APPLY_TT"\n\t\t\tshortcut = "RETURN"\n'
            ),
            quad=True,
        ),
        button(
            "rn_cp_cancel",
            (CANCEL_X, CONTENT_Y + 5),
            "GFX_closebutton_16",
            attrs='\t\t\tpdx_tooltip = "RN_IP_CANCEL"\n',
            quad=True,
        ),
        "\t\t# Red, green and blue, 0..255, in steps of 1 and 16.\n",
        _channels(),
        text("rn_cp_status", (6, STATUS_Y), "[This.RN_CP_STATUS]", (WIDTH - 12, 14)),
        "\t\t# Restore colour: removes the colour layer (only while one is set).\n",
        button(
            "rn_cp_reset",
            RESET_POS,
            "GFX_button_123x34",
            attrs=captioned("RN_CP_RESET", "RN_CP_RESET_TT"),
        ),
        "\t}\n",
    ]
    return "".join(parts)


def gui() -> str:
    """Return the window file.

    Returns:
        Contents of :data:`GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Colour picker (tools/modgen/features/colour_picker.py): own country in the politics\n"
        "# view, another country in its diplomacy view.\n"
        "guiTypes = {\n" + "".join(window(p) for p in PICKERS) + "}\n"
    )


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
            "is_in_array = { array = rn_cp_target_arr value = THIS }"
        )
    return (
        "NOT = { tag = ROOT } rn_sub_may_edit = yes "
        "is_in_array = { array = ROOT.rn_cp_target_arr value = THIS } "
        f"ROOT = {{ {_ROOT_OK} has_country_flag = {picker.open_flag} }}"
    )


def _switched_on(feature: str, picker: Picker | None = None) -> str:
    """Return the host-switch condition of a tab or button (ADR-0036).

    Args:
        feature: Feature id.
        picker: The editor; another country also needs the "other countries" switch.
            None for the subject tabs, which are always about another country.

    Returns:
        Trigger text.
    """
    out = f"NOT = {{ rn_feature_{feature}_off = yes }}"
    if picker is not OWN:
        out += " NOT = { rn_feature_subjects_off = yes }"
    return out


def _tab_lines(picker: Picker) -> tuple[list[str], list[str]]:
    """Return the tab click effects and their enabled triggers.

    Args:
        picker: The editor.

    Returns:
        ``(effects, triggers)``.
    """
    prefix = f"rn_cp_{picker.editor}_tab_"
    if picker is OWN:
        effects = [
            (
                f"\t\t\t{prefix}name_click = "
                "{ ROOT = { rn_cp_to_name_editor = yes rn_ip_status_clear = yes } }\n"
            ),
            f"\t\t\t{prefix}flag_click = {{ ROOT = {{ rn_fp_open_own = yes }} }}\n",
        ]
        triggers = [
            f"\t\t\t{prefix}colour_click_enabled = {{ always = no }}\n",
            (
                f"\t\t\t{prefix}name_click_enabled = "
                "{ NOT = { rn_ip_cooldown_active_country = yes } "
                "NOT = { rn_feature_country_off = yes } }\n"
            ),
            f"\t\t\t{prefix}flag_click_enabled = {{ NOT = {{ rn_feature_flag_off = yes }} }}\n",
        ]
        return effects, triggers
    limit = f"rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }}"
    effects = [
        f"\t\t\t{prefix}{suffix}_click = {{\n"
        f"\t\t\t\tif = {{\n\t\t\t\t\tlimit = {{ {limit} {_switched_on(suffix)} }}\n"
        "\t\t\t\t\tROOT = { rn_cp_close = yes }\n\t\t\t\t\trn_sub_open_common = yes\n"
        f"\t\t\t\t\tROOT = {{ set_country_flag = rn_sub_open_{suffix} }}\n"
        "\t\t\t\t}\n\t\t\t}\n"
        for suffix in ("country", "leader", "party")
    ]
    effects.append(f"\t\t\t{prefix}flag_click = {{ rn_fp_open_sub = yes }}\n")
    triggers = [
        f"\t\t\t{prefix}{s}_click_enabled = "
        f"{{ rn_sub_may_edit = yes ROOT = {{ {_ROOT_OK} }} {_switched_on(s)} }}\n"
        for s in ("country", "leader", "party", "flag")
    ]
    return effects, triggers


def _grid_lines() -> tuple[list[str], list[str]]:
    """Return the swatch click effects and the mark triggers.

    Returns:
        ``(effects, triggers)``.
    """
    effects = [
        f"\t\t\trn_cp_sw_{n}_click = {{ ROOT = {{ set_temp_variable = {{ rn_cp_pick = {n} }} "
        "rn_cp_pick_preset = yes } }\n"
        for n in range(1, len(PRESETS) + 1)
    ]
    triggers = [
        f"\t\t\trn_cp_mark_{n}_visible = "
        f"{{ ROOT = {{ check_variable = {{ rn_cp_sel = {n} }} }} }}\n"
        for n in range(1, len(PRESETS) + 1)
    ]
    return effects, triggers


def _channel_lines() -> tuple[list[str], list[str]]:
    """Return the stepper click effects and their enabled triggers.

    Returns:
        ``(effects, triggers)``.
    """
    effects: list[str] = []
    triggers: list[str] = []
    for i, (c, _) in enumerate(CHANNELS, start=1):
        for suffix, step, _x in STEPS:
            name = f"rn_cp_{c}_{suffix}"
            effects.append(
                f"\t\t\t{name}_click = {{ ROOT = {{ set_temp_variable = {{ rn_cp_ch = {i} }} "
                f"set_temp_variable = {{ rn_cp_d = {step} }} rn_cp_step = yes }} }}\n"
            )
            bound = f"rn_cp_{c} > 0" if step < 0 else f"rn_cp_{c} < 255"
            triggers.append(
                f"\t\t\t{name}_click_enabled = {{ ROOT = {{ check_variable = {{ {bound} }} }} }}\n"
            )
    return effects, triggers


_EFFECTS = """\t\t\trn_cp_cancel_click = { ROOT = { rn_cp_close = yes rn_cv1_status_clear = yes } }
\t\t\trn_cp_reset_click = { ROOT = { rn_cp_reset = yes } }
"""
"""Click effects both pickers share (Apply and the tabs are per picker)."""

_TRIGGERS = """\t\t\trn_cp_reset_visible = { has_variable = capie_cc_ver }
\t\t\trn_cp_reset_click_enabled = { has_variable = capie_cc_ver NOT = { rn_cp_cooldown_active = yes } NOT = { rn_feature_colour_off = yes } }
\t\t\trn_cp_note_game_visible = { NOT = { has_variable = capie_cc_ver } ROOT = { NOT = { has_country_flag = rn_cp_changed } } }
\t\t\trn_cp_note_current_visible = { has_variable = capie_cc_ver ROOT = { NOT = { has_country_flag = rn_cp_changed } } }
\t\t\trn_cp_note_new_visible = { ROOT = { has_country_flag = rn_cp_changed } }
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Visible and enabled triggers both pickers share (THIS is the country whose colour changes)."""


def scripted_gui(picker: Picker) -> str:
    """Return the scripted GUI of one picker.

    Args:
        picker: The editor.

    Returns:
        The ``<key> = { ... }`` block.
    """
    tab_effects, tab_triggers = _tab_lines(picker)
    grid_effects, grid_triggers = _grid_lines()
    step_effects, step_triggers = _channel_lines()
    dirty = "\t\tdirty = rn_cp_dirty\n" if picker is OWN else ""
    # The preview frame is on ROOT (the player); THIS is the target in the diplomacy view.
    frame = "rn_cp_frame" if picker is OWN else "ROOT.rn_cp_frame"
    lines = [
        f"\t{picker.key} = {{\n",
        f"\t\tcontext_type = {picker.context}\n",
        f"\t\tparent_window_token = {picker.parent}\n",
        f'\t\twindow_name = "{picker.key}"\n',
        f"\t\tvisible = {{ {_visible(picker)} }}\n",
        "\t\tai_enabled = { always = no }\n",
        dirty,
        "\t\teffects = {\n",
        f"\t\t\t{picker.key}_apply_click = {{ ROOT = {{ rn_cp_apply = yes }} }}\n",
        _EFFECTS,
        *tab_effects,
        *grid_effects,
        *step_effects,
        "\t\t}\n",
        "\t\ttriggers = {\n",
        f"\t\t\tcapie_v1_ep__rncc__{picker.editor}_visible = {{ always = no }}\n",
        (
            f"\t\t\t{picker.key}_apply_click_enabled = {{ ROOT = {{ "
            f"has_country_flag = {picker.open_flag} has_country_flag = rn_cp_changed }} "
            f"NOT = {{ rn_cp_cooldown_active = yes }} {_switched_on('colour', picker)} }}\n"
        ),
        _TRIGGERS,
        *tab_triggers,
        *grid_triggers,
        *step_triggers,
        "\t\t}\n",
        f"\t\tproperties = {{\n\t\t\trn_cp_preview = {{ frame = {frame} }}\n\t\t}}\n",
        "\t}\n",
    ]
    return "".join(lines)


def scripted_guis() -> str:
    """Return the scripted GUI file.

    Returns:
        Contents of :data:`SCRIPTED_GUI_FILE`.
    """
    return (
        GEN_HEADER
        + "# Colour picker (tools/modgen/features/colour_picker.py). ROOT is the player in both\n"
        "# editors; THIS is the country whose colour changes (the player in the politics view,\n"
        "# the selected country in its diplomacy view). The effects (rn_colour_picker.txt)\n"
        "# re-check the pinned target, the rights, the cooldown and the CAPIE records; a click\n"
        "# never trusts the command scope.\n"
        "scripted_gui = {\n" + "".join(scripted_gui(p) for p in PICKERS) + "}\n"
    )


def on_actions() -> str:
    """Return the daily colour checks.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE`.
    """
    return (
        GEN_HEADER
        + "# Daily: a country with a colour layer whose cosmetic tag changed loses the layer\n"
        "# (CONTRACT 19.4, as for the flag; no cooldown, it is not a player's action), and an\n"
        "# open colour picker refreshes (dirty = rn_cp_dirty) so the cooldown days stay current.\n"
        "on_actions = {\n\ton_daily = {\n\t\teffect = {\n"
        "\t\t\tif = { limit = { has_variable = capie_cc_ver } rn_cp_daily_check = yes }\n"
        "\t\t\tif = { limit = { is_ai = no has_country_flag = rn_cp_open_own } "
        "add_to_variable = { rn_cp_dirty = 1 } }\n"
        "\t\t}\n\t}\n}\n"
    )


def write_files() -> list[tuple[str, str]]:
    """Return the picker's text files.

    Returns:
        ``(path relative to mod/, text)`` per file.
    """
    return [
        (GUI_FILE, gui()),
        (SCRIPTED_GUI_FILE, scripted_guis()),
        (ON_ACTIONS_FILE, on_actions()),
    ]
