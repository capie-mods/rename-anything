"""Input window: the text field, the on-screen keyboard and Apply.

This is the keyboard mode of the legacy rename window. It shows while the
country flag ``rn_lg_keyboard`` is set; otherwise the CAPIE text field of
:mod:`modgen.features.legacy_field` takes its place.

Every target (character, state, city, country name or adjective) is typed here
into :data:`~modgen.features.text_buffers.INPUT_BUFFER`. Physical keys work
through button shortcuts: a letter key types the letter in the current case,
an invisible ``shift+<letter>`` button always types the upper-case letter, and
Backspace, Space and Enter have their own shortcuts. Polish letters and the
apostrophe are buttons only.

``rn_apply_input`` dispatches on ``rn_ttype``. ``meta_effect`` turns the scripted
localisation of the buffer into a literal string, so the stored name is plain
text. Persistence was observed in stage0 probes; multiplayer still needs a
two-client test.
"""

from __future__ import annotations

from modgen.charset import (
    CODE,
    LOWER,
    LOWER_FIRST,
    PL_LOWER,
    PL_LOWER_FIRST,
    PL_UPPER_FIRST,
    UPPER_FIRST,
)
from modgen.common import (
    TARGET_CHARACTER,
    TARGET_CITY,
    TARGET_COUNTRY_ADJ,
    TARGET_COUNTRY_NAME,
    TARGET_STATE,
    slots_expr,
)
from modgen.features import legacy_field, refresh
from modgen.features.cities import province_expr
from modgen.features.main_window import WINDOW_WIDTH
from modgen.features.text_buffers import INPUT_BUFFER
from modgen.gui import (
    BUTTON_MEDIUM,
    TITLE_FONT,
    WINDOW_END,
    background,
    btn,
    entry_window,
    gridbox,
    txt,
    window_header,
)
from modgen.script import check_variable, defined_text

KEY = 36
"""Width in pixels of a normal keyboard key texture."""

KEY_H = 32
"""Height in pixels of every keyboard key texture."""

PITCH = 40
"""Distance in pixels between neighbouring keys, horizontally and vertically."""

KB_Y = 124
"""Y position of the first keyboard row inside the input window."""

INPUT_HEIGHT = 468
"""Height of the input window."""

ROW1 = [*list("1234567890"), "-", ".", "'"]
"""Characters on the first keyboard row (digits and punctuation)."""

ROW2 = list("qwertyuiop")
"""Letters on the second keyboard row."""

ROW3 = list("asdfghjkl")
"""Letters on the third keyboard row."""

ROW4 = list("zxcvbnm")
"""Letters on the fourth keyboard row."""

LETTER_ROWS = ((ROW2, 40, 1), (ROW3, 60, 2), (ROW4, 80, 3))
"""Letter rows as (keys, x of the first key, row index below the first row)."""

PUNCTUATION_KEY_IDS = {"-": "minus", ".": "dot", "'": "apos"}
"""Button name part of the punctuation keys (a GUI name cannot hold the character)."""

KEY_SPRITE = "GFX_rn_key"
"""Sprite of a normal key."""

WIDE_KEY_SPRITE = "GFX_rn_key_wide"
"""Sprite of Caps, Backspace and Clear."""

SPACE_KEY_SPRITE = "GFX_rn_key_space"
"""Sprite of the space bar."""

INVISIBLE_SPRITE = "GFX_rn_invisible"
"""Sprite of the invisible ``shift+<letter>`` hit areas."""

FIELD_SPRITE = "GFX_rn_field"
"""Sprite of the text field background."""

TARGET_ROW_WIDTH = 500
"""Width of the row that shows the rename target above the text field."""

TARGET_ROW_HEIGHT = 26
"""Height of that row."""

SHIFT_VARIABLE = "rn_shift"
"""Country variable that is 1 while Caps is on."""

KeySpec = tuple[str, int, int, str, str | None, str | None, str]
"""Keyboard button as (name, x, y, sprite, text key, shortcut, click effect body)."""


def key_id(ch: str) -> str:
    """Return the identifier part used in a key's button name.

    Args:
        ch: Character on the key.

    Returns:
        ``minus``, ``dot`` or ``apos`` for punctuation, otherwise the character.
    """
    return PUNCTUATION_KEY_IDS.get(ch, ch)


def _type_char(code: int, effect: str = "rn_add_char") -> str:
    """Return the click effect body that types one character code.

    Args:
        code: Character code.
        effect: ``rn_add_char`` (exact code) or ``rn_add_letter`` (follows Caps).

    Returns:
        The effect body.
    """
    return f"set_temp_variable = {{ rn_c = {code} }} {effect} = yes"


def keyboard_keys() -> list[KeySpec]:
    """Return every keyboard button of the input window.

    The list holds the visible keys row by row, then Caps, Backspace, Space and
    Clear, and finally 26 invisible ``shift+<letter>`` buttons that always type
    the upper-case letter.

    Returns:
        ``(button_name, x, y, sprite, text_key, shortcut, effect_body)`` tuples.
    """
    keys: list[KeySpec] = []
    for i, ch in enumerate(ROW1):
        keys.append(
            (
                f"rn_key_{key_id(ch)}",
                20 + i * PITCH,
                KB_Y,
                KEY_SPRITE,
                f"RN_CH_{CODE[ch]}",
                ch if ch != "'" else None,
                _type_char(CODE[ch]),
            )
        )
    for row, x0, row_index in LETTER_ROWS:
        keys.extend(
            (
                f"rn_key_{ch}",
                x0 + i * PITCH,
                KB_Y + row_index * PITCH,
                KEY_SPRITE,
                f"RN_KL_{ch}",
                ch,
                _type_char(CODE[ch], "rn_add_letter"),
            )
            for i, ch in enumerate(row)
        )
    y5 = KB_Y + 4 * PITCH
    keys.extend(
        (
            f"rn_key_pl{i}",
            20 + i * PITCH,
            y5,
            KEY_SPRITE,
            f"RN_KL_pl{i}",
            None,
            _type_char(PL_LOWER_FIRST + i, "rn_add_letter"),
        )
        for i in range(len(PL_LOWER))
    )
    keys.append(
        ("rn_key_caps", 380, y5, WIDE_KEY_SPRITE, "RN_KEY_CAPS", None, "rn_toggle_shift = yes")
    )
    keys.append(
        (
            "rn_key_backspace",
            380,
            KB_Y + 3 * PITCH,
            WIDE_KEY_SPRITE,
            "RN_KEY_BACKSPACE",
            "BACKSPACE",
            "rn_backspace = yes",
        )
    )
    y6 = KB_Y + 5 * PITCH
    keys.append(
        (
            "rn_key_space",
            100,
            y6,
            SPACE_KEY_SPRITE,
            "RN_KEY_SPACE",
            "SPACE",
            _type_char(CODE[" "]),
        )
    )
    keys.append(
        ("rn_key_clear", 320, y6, WIDE_KEY_SPRITE, "RN_KEY_CLEAR", None, "rn_clear_buf = yes")
    )
    keys.extend(
        (
            f"rn_keyS_{ch}",
            2,
            2,
            INVISIBLE_SPRITE,
            None,
            f"shift+{ch}",
            _type_char(UPPER_FIRST + i),
        )
        for i, ch in enumerate(LOWER)
    )
    return keys


def key_label_loc() -> str:
    """Return the key captions that follow the Caps toggle, and the Caps caption.

    Returns:
        ``RN_KeyLabel_<letter>``, ``RN_KeyLabel_pl<i>`` and ``RN_CapsLabel``.
    """
    caps_on = check_variable(f"{SHIFT_VARIABLE} = 1")
    latin = (
        defined_text(
            f"RN_KeyLabel_{c}",
            [(caps_on, f"RN_CH_{UPPER_FIRST + i}")],
            f"RN_CH_{LOWER_FIRST + i}",
        )
        for i, c in enumerate(LOWER)
    )
    polish = (
        defined_text(
            f"RN_KeyLabel_pl{i}",
            [(caps_on, f"RN_CH_{PL_UPPER_FIRST + i}")],
            f"RN_CH_{PL_LOWER_FIRST + i}",
        )
        for i in range(len(PL_LOWER))
    )
    caps = defined_text("RN_CapsLabel", [(caps_on, "RN_KEY_CAPS_ON")], "RN_KEY_CAPS_OFF")
    return "".join(latin) + "".join(polish) + caps


def target_type_loc() -> str:
    """Return ``RN_TargetTypeLabel``, the target kind in the input window title.

    Returns:
        A ``defined_text`` with one branch per ``rn_ttype`` value.
    """
    targets = range(TARGET_CHARACTER, TARGET_COUNTRY_ADJ + 1)
    return defined_text(
        "RN_TargetTypeLabel",
        [(check_variable(f"rn_ttype = {t}"), f"RN_TTYPE_{t}") for t in targets],
        "RN_TTYPE_0",
    )


def key_label_entries() -> list[str]:
    """Return the language-independent ``RN_KL_*`` indirections to the key captions.

    Returns:
        One localisation line per letter key.
    """
    return [f' RN_KL_{c}: "[ROOT.RN_KeyLabel_{c}]"\n' for c in LOWER] + [
        f' RN_KL_pl{i}: "[ROOT.RN_KeyLabel_pl{i}]"\n' for i in range(len(PL_LOWER))
    ]


_CLOSING_EFFECTS = (
    "\t\t\trn_cancel_click = { rn_cancel_input = yes }\n"
    "\t\t\trn_apply_click = { rn_apply_input = yes }\n"
)
"""Cancel and Apply effects of the input window."""


def input_gui() -> str:
    """Return the scripted GUI of the input window with every keyboard key.

    Returns:
        The ``rn_input_gui`` block (one tab of indentation).
    """
    key_effects = "".join(
        f"\t\t\t{name}_click = {{ {body} }}\n" for name, *_r, body in keyboard_keys()
    )
    return f"""	rn_input_gui = {{
		context_type = player_context
		window_name = "rn_input_window"
		visible = {{ has_country_flag = rn_input has_country_flag = {legacy_field.KEYBOARD_FLAG} }}
		ai_enabled = {{ always = no }}
{refresh.dirty_line()}		effects = {{
{refresh.touch_clicks(key_effects + _CLOSING_EFFECTS + legacy_field.KEYBOARD_MODE_EFFECT)}		}}
		triggers = {{
			rn_apply_click_enabled = {{ check_variable = {{ {INPUT_BUFFER.length} > 0 }} }}
			rn_target_prov_visible = {{ check_variable = {{ rn_ttype = {TARGET_CITY} }} }}
			rn_target_country_visible = {{ check_variable = {{ rn_ttype > {TARGET_CITY} }} }}
		}}
		dynamic_lists = {{
			rn_target_grid = {{
				array = rn_display_target
				value = rn_header_target
				change_scope = no
				entry_container = "rn_target_entry"
			}}
		}}
	}}
"""


def target_entry() -> list[str]:
    """Return the row template that shows the rename target in the input window.

    Returns:
        GUI blocks of the ``rn_target_entry`` window.
    """
    return [
        entry_window("rn_target_entry", TARGET_ROW_WIDTH, TARGET_ROW_HEIGHT),
        txt("rn_target_name", 0, 2, "RN_TARGET_DISPLAY", font=TITLE_FONT, w=500),
        WINDOW_END,
    ]


def input_window() -> list[str]:
    """Return the input window with the text field and on-screen keyboard.

    Returns:
        GUI blocks in drawing order, ending with the closing brace and a blank line.
    """
    o = [
        window_header("rn_input_window", WINDOW_WIDTH, INPUT_HEIGHT),
        background("rn_input_bg"),
        txt("rn_input_title", 20, 12, "RN_INPUT_TITLE", font=TITLE_FONT, w=520),
        gridbox(
            "rn_target_grid", (20, 40), (TARGET_ROW_WIDTH, TARGET_ROW_HEIGHT), TARGET_ROW_HEIGHT
        ),
        txt("rn_target_prov", 20, 42, "RN_TARGET_PROV", font=TITLE_FONT, w=500),
        txt("rn_target_country", 20, 42, "RN_TARGET_COUNTRY", font=TITLE_FONT, w=500),
        (
            '\t\ticonType = { name = "rn_field_bg" position = { x = 20 y = 72 }'
            f' spriteType = "{FIELD_SPRITE}" }}\n'
        ),
        txt("rn_field_text", 30, 82, "RN_FIELD_TEXT", font=TITLE_FONT, w=440),
        txt("rn_field_count", 470, 84, "RN_FIELD_COUNT", w=64, fmt="right"),
    ]
    keys = keyboard_keys()
    # Invisible shift buttons first, so they are drawn underneath the visible keys.
    o.extend(
        btn(name, x, y, sprite, text=None, shortcut=sc)
        for name, x, y, sprite, _text, sc, _ in keys
        if sprite == INVISIBLE_SPRITE
    )
    o.extend(
        btn(name, x, y, sprite, text=text, shortcut=sc)
        for name, x, y, sprite, text, sc, _ in keys
        if sprite != INVISIBLE_SPRITE
    )
    by = KB_Y + 6 * PITCH + 2
    o.append(btn("rn_cancel", 150, by, BUTTON_MEDIUM, text="RN_BTN_CANCEL"))
    o.append(
        btn(
            "rn_apply",
            290,
            by,
            BUTTON_MEDIUM,
            text="RN_BTN_APPLY",
            shortcut="RETURN",
            tooltip="RN_APPLY_TT",
        )
    )
    o.append(txt("rn_input_hint", 20, by + 40, "RN_INPUT_HINT", w=520, h=44))
    o.extend(legacy_field.keyboard_mode_elements(by, by + 84))
    o.append(WINDOW_END + "\n")
    return o


def apply_input_effect() -> str:
    """Return ``rn_apply_input``, which applies the buffer to the current target.

    Characters: the player's characters are rebuilt first (a target can move or
    retire while the window is open), and the country leader shares the in-place
    editor's cooldown. States and cities start their own cooldown. The country
    name and adjective only fill their buffers; the Country tab applies them.

    Returns:
        The effect with its comment lines.
    """
    name = slots_expr(INPUT_BUFFER.prefix)
    province = province_expr()
    return f"""# Apply the input buffer to the current target. meta_effect turns the scripted loc into a literal string,
# so the stored name is plain text. Persistence was observed in stage0 probes; MP still needs a two-client test.
rn_apply_input = {{
	if = {{
		limit = {{ check_variable = {{ {INPUT_BUFFER.length} > 0 }} }}
		if = {{
			limit = {{ check_variable = {{ rn_ttype = {TARGET_CHARACTER} }} }}
			# Rebuild only the character list (not states): a target can transfer/retire while the input stays open.
			rn_refresh_chars = yes
			for_each_scope_loop = {{
				array = rn_tchar
				if = {{
					limit = {{
						is_in_array = {{ array = ROOT.rn_chars_all value = THIS }}
						# The country leader shares the in-place editor cooldown (no legacy bypass).
						OR = {{
							NOT = {{ is_country_leader = yes }}
							ROOT = {{ NOT = {{ rn_ip_cooldown_active_leader = yes }} }}
						}}
					}}
					meta_effect = {{
						text = {{ set_character_name = "[N]" }}
						N = "{name}"
					}}
					if = {{
						limit = {{ is_country_leader = yes }}
						ROOT = {{ rn_ip_cooldown_start_leader = yes }}
					}}
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = {TARGET_STATE} }} NOT = {{ rn_cd_state_active = yes }} }}
			for_each_scope_loop = {{
				array = rn_tstate
				if = {{
					limit = {{ is_owned_by = ROOT }}
					meta_effect = {{
						text = {{ set_state_name = "[N]" }}
						N = "{name}"
					}}
					ROOT = {{ rn_cd_state_start = yes }}
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = {TARGET_CITY} }} check_variable = {{ rn_tprov > 0 }} NOT = {{ rn_cd_vp_active = yes }} }}
			for_each_scope_loop = {{
				array = rn_tstate
				if = {{
					limit = {{ is_owned_by = ROOT }}
					meta_effect = {{
						text = {{ set_province_name = {{ id = [P] name = "[N]" }} }}
						P = "{province}"
						N = "{name}"
					}}
					ROOT = {{ rn_cd_vp_start = yes }}
					rn_vp_store_name = yes
					rn_vp_names_to_root = yes
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = {TARGET_COUNTRY_NAME} }} }}
			rn_store_country_name = yes
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = {TARGET_COUNTRY_ADJ} }} }}
			rn_store_country_adj = yes
		}}
	}}
	rn_cancel_input = yes
}}
"""  # noqa: E501 - generated script lines are emitted verbatim
