"""Native text field of the legacy rename window (CAPIE v1.1 editor grammar).

With CAPIE the legacy window (characters, states, cities, country name and
adjective) takes the name in an ordinary HOI4 edit box, so the physical
keyboard works, AltGr and Polish letters included. The window is a public
grammar editor (``plugin/capie/CONTRACT.md``, API level 2): scripted GUI
``capie_v1_ed__rn__legacy``, field ``capie_v1_f__rn__legacy__1``, epoch carrier
``capie_v1_ep__rn__legacy`` and Apply ``capie_v1_ed__rn__legacy_apply``. CAPIE
adds the typed codes to the Apply command; ``rn_lg_field_apply``
(``tools/inline_editor/common/scripted_effects/rn_capie_legacy.txt``) validates
them with the existing payload validator, fills the input buffer and runs the
usual ``rn_apply_input``.

No trigger can tell whether CAPIE is loaded (the contract reports it only in an
Apply command). The field is therefore the default, and the first Apply without
CAPIE ends with error 10: nothing is changed, the window switches to the
on-screen keyboard (country flag ``rn_lg_keyboard``) and says why. The flag is
saved, so this happens once per save; two buttons switch between the modes by
hand.
"""

from __future__ import annotations

from modgen.common import TARGET_CITY
from modgen.features.main_window import WINDOW_WIDTH
from modgen.gui import (
    BUTTON_MEDIUM,
    BUTTON_SMALL,
    TITLE_FONT,
    WINDOW_END,
    background,
    btn,
    gridbox,
    txt,
    window_header,
)

MODEL = "capie_v1_ed__rn__legacy"
"""Scripted GUI key and window name of the field mode (CAPIE grammar, mod id ``rn``)."""

FIELD = "capie_v1_f__rn__legacy__1"
"""The edit box CAPIE reads on Apply."""

EPOCH_CARRIER = "capie_v1_ep__rn__legacy"
"""Hidden text box that shows the opening epoch to CAPIE."""

KEYBOARD_FLAG = "rn_lg_keyboard"
"""Country flag: the legacy window uses the on-screen keyboard instead of the field."""

FIELD_HEIGHT = 190
"""Height of the field-mode window."""

FIELD_Y = 86
"""Top of the field frame (the label row sits 12 px above it)."""

BUTTON_Y = 140
"""Top of the button row."""

TARGET_ROW = (500, 30)
"""Size of the target header row (same as the keyboard window)."""


def field_window() -> list[str]:
    """Return the field-mode window: target header, labelled edit box, status, buttons.

    Returns:
        GUI blocks in drawing order, ending with the closing brace and a blank line.
    """
    return [
        window_header(MODEL, WINDOW_WIDTH, FIELD_HEIGHT),
        background("rn_lg_bg"),
        txt("rn_lg_title", 20, 12, "RN_INPUT_TITLE", font=TITLE_FONT, w=520),
        gridbox("rn_lg_target_grid", (20, 40), TARGET_ROW, TARGET_ROW[1]),
        txt("rn_lg_target_prov", 20, 42, "RN_TARGET_PROV", font=TITLE_FONT, w=500),
        txt("rn_lg_target_country", 20, 42, "RN_TARGET_COUNTRY", font=TITLE_FONT, w=500),
        (
            '\t\tinstantTextBoxType = { name = "' + EPOCH_CARRIER + '" position = { x = 0 y = 0 }'
            ' font = "Arial12" text = "[?ROOT.rn_lg_epoch|0]" maxWidth = 120 maxHeight = 14'
            " fixedsize = yes }\n"
        ),
        (
            '\t\tcontainerWindowType = { name = "rn_lg_field_frame"'
            f" position = {{ x = 20 y = {FIELD_Y} }} size = {{ width = 364 height = 26 }}"
            ' clipping = no background = { name = "Background"'
            ' spriteType = "GFX_tiles_dark_area_cut_8" alwaysTransparent = yes } }\n'
        ),
        txt("rn_lg_label", 26, FIELD_Y - 12, "RN_LG_LABEL", font="Arial12", w=356, h=14),
        (
            f'\t\teditBoxType = {{ name = "{FIELD}" position = {{ x = 24 y = {FIELD_Y + 3} }}'
            ' size = { x = 356 y = 20 } font = "hoi_18" borderSize = { x = 0 y = 0 }'
            ' text = "" ignore_enter = yes }\n'
        ),
        txt("rn_lg_status", 26, FIELD_Y + 28, "[ROOT.RN_LG_STATUS]", font="Arial12", w=408, h=14),
        btn(
            "rn_lg_use_keyboard",
            20,
            BUTTON_Y + 2,
            BUTTON_SMALL,
            text="RN_LG_BTN_KEYBOARD",
            tooltip="RN_LG_BTN_KEYBOARD_TT",
        ),
        btn("rn_lg_cancel", 150, BUTTON_Y, BUTTON_MEDIUM, text="RN_BTN_CANCEL"),
        btn(
            f"{MODEL}_apply",
            290,
            BUTTON_Y,
            BUTTON_MEDIUM,
            text="RN_BTN_APPLY",
            shortcut="RETURN",
            tooltip="RN_LG_APPLY_TT",
        ),
        WINDOW_END + "\n",
    ]


def field_gui() -> str:
    """Return the scripted GUI of the field mode.

    The Apply effect ends with the refresh bump of the legacy windows, because an
    Apply without CAPIE switches to the keyboard window, which only updates when
    ``rn_gui_dirty`` changes.

    Returns:
        The ``capie_v1_ed__rn__legacy`` block (one tab of indentation).
    """
    return f"""	{MODEL} = {{
		context_type = player_context
		window_name = "{MODEL}"
		visible = {{ has_country_flag = rn_input NOT = {{ has_country_flag = {KEYBOARD_FLAG} }} }}
		ai_enabled = {{ always = no }}
		effects = {{
			{MODEL}_apply_click = {{ rn_lg_field_apply = yes rn_gui_touch = yes }}
			rn_lg_cancel_click = {{ rn_cancel_input = yes }}
			rn_lg_use_keyboard_click = {{ set_country_flag = {KEYBOARD_FLAG} rn_cv1_status_clear = yes rn_gui_touch = yes }}
		}}
		triggers = {{
			{EPOCH_CARRIER}_visible = {{ always = no }}
			rn_lg_target_prov_visible = {{ check_variable = {{ rn_ttype = {TARGET_CITY} }} }}
			rn_lg_target_country_visible = {{ check_variable = {{ rn_ttype > {TARGET_CITY} }} }}
		}}
		dynamic_lists = {{
			rn_lg_target_grid = {{
				array = rn_display_target
				value = rn_header_target
				change_scope = no
				entry_container = "rn_target_entry"
			}}
		}}
	}}
"""  # noqa: E501 - generated script lines are emitted verbatim


def keyboard_mode_elements(button_y: int, status_y: int) -> list[str]:
    """Return the keyboard window's way back to the field and its CAPIE line.

    Args:
        button_y: Top of the keyboard window's button row.
        status_y: Top of the free line under the hint.

    Returns:
        The ``rn_lg_use_field`` button and the ``rn_lg_kb_status`` line.
    """
    return [
        btn(
            "rn_lg_use_field",
            20,
            button_y + 2,
            BUTTON_SMALL,
            text="RN_LG_BTN_FIELD",
            tooltip="RN_LG_BTN_FIELD_TT",
        ),
        txt("rn_lg_kb_status", 20, status_y, "[ROOT.RN_LG_KB_STATUS]", font="Arial12", w=520, h=14),
    ]


KEYBOARD_MODE_EFFECT = (
    "\t\t\trn_lg_use_field_click = {"
    f" clr_country_flag = {KEYBOARD_FLAG} rn_cv1_status_clear = yes }}\n"
)
"""Click effect of the keyboard window's "Text field" button (the refresh bump is added there)."""
