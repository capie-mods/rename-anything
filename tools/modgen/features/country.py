"""Country tab: country name, adjective and leader, and the native RN1 carrier.

The country name and adjective are typed into their own buffers
(:data:`~modgen.features.text_buffers.COUNTRY_NAME_BUFFER` and
:data:`~modgen.features.text_buffers.COUNTRY_ADJ_BUFFER`). Apply stores both in
one cosmetic tag ``RN1|<name>|<adjective>|``; the native plugin decodes it when
the game looks up country localisation keys. The legacy Apply shares the
in-place editor's country cooldown and is gated by the editor bridge.
"""

from __future__ import annotations

from modgen.common import TAB_COUNTRY, TARGET_COUNTRY_ADJ, TARGET_COUNTRY_NAME, slots_expr
from modgen.features.main_window import TabSpec
from modgen.features.text_buffers import COUNTRY_ADJ_BUFFER, COUNTRY_NAME_BUFFER
from modgen.gui import BUTTON_MEDIUM, BUTTON_WIDE, TITLE_FONT, btn, txt
from modgen.script import defined_text

COUNTRY_FLAG = "rn_custom_name"
"""Country flag set after the cosmetic tag was written (not proof that the plugin runs)."""

RN1_PREFIX = "RN1"
"""Protocol tag of the cosmetic tag the native plugin decodes; a native contract."""

_EFFECTS = f"""			rn_leader_rename_click = {{ rn_target_leader = yes }}
			rn_cname_edit_click = {{ set_variable = {{ rn_ttype = {TARGET_COUNTRY_NAME} }} rn_open_input = yes }}
			rn_cadj_edit_click = {{ set_variable = {{ rn_ttype = {TARGET_COUNTRY_ADJ} }} rn_open_input = yes }}
			rn_country_apply_click = {{
				# The cooldown starts only in the same branch as the setter (its limit repeats the
				# rn_apply_country_name limit). Without the editor bridge the button does nothing.
				if = {{
					limit = {{
						rn_editor_bridge_available = yes
						NOT = {{ rn_ip_cooldown_active_country = yes }}
						rn_country_rename_enabled = yes
						check_variable = {{ rn_cname_len > 0 }}
						check_variable = {{ rn_cadj_len > 0 }}
					}}
					rn_apply_country_name = yes
					rn_ip_cooldown_start_country = yes
				}}
			}}
			rn_country_reset_click = {{ rn_reset_country_name = yes }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI effects of the Country tab."""

_TRIGGERS = f"""			rn_leader_rename_click_enabled = {{ NOT = {{ rn_ip_cooldown_active_leader = yes }} }}
			rn_country_apply_click_enabled = {{
				rn_editor_bridge_available = yes
				NOT = {{ rn_ip_cooldown_active_country = yes }}
				rn_country_rename_enabled = yes
				check_variable = {{ rn_cname_len > 0 }}
				check_variable = {{ rn_cadj_len > 0 }}
			}}
			rn_country_reset_click_enabled = {{ has_country_flag = {COUNTRY_FLAG} }}
"""  # noqa: E501 - generated script lines are emitted verbatim
"""Scripted GUI triggers of the Country tab."""


def _elements(y0: int) -> tuple[str, ...]:
    """Return the elements of the Country tab.

    Args:
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    return (
        txt("rn_cur_name", 20, y0 + 8, "RN_CUR_NAME", w=520),
        txt("rn_cur_adj", 20, y0 + 32, "RN_CUR_ADJ", w=520),
        txt("rn_cur_leader", 20, y0 + 66, "RN_CUR_LEADER", w=380),
        btn("rn_leader_rename", 410, y0 + 58, BUTTON_MEDIUM, text="RN_BTN_RENAME"),
        txt("rn_country_hdr", 20, y0 + 112, "RN_COUNTRY_HDR", font=TITLE_FONT, w=520),
        txt("rn_cname_line", 20, y0 + 148, "RN_CNAME_LINE", w=380),
        btn("rn_cname_edit", 410, y0 + 140, BUTTON_MEDIUM, text="RN_BTN_TYPE"),
        txt("rn_cadj_line", 20, y0 + 188, "RN_CADJ_LINE", w=380),
        btn("rn_cadj_edit", 410, y0 + 180, BUTTON_MEDIUM, text="RN_BTN_TYPE"),
        btn(
            "rn_country_apply",
            20,
            y0 + 226,
            BUTTON_MEDIUM,
            text="RN_BTN_COUNTRY_APPLY",
            tooltip="RN_COUNTRY_APPLY_TT",
        ),
        btn(
            "rn_country_reset",
            152,
            y0 + 226,
            BUTTON_WIDE,
            text="RN_BTN_COUNTRY_RESET",
            tooltip="RN_COUNTRY_RESET_TT",
        ),
        txt("rn_country_status", 20, y0 + 272, "RN_COUNTRY_STATUS", w=520, h=24),
        txt("rn_country_plugin", 20, y0 + 296, "RN_COUNTRY_PLUGIN", w=520, h=24),
        txt("rn_country_note", 20, y0 + 328, "RN_COUNTRY_NOTE", w=520, h=72),
    )


def tab(content_y: int) -> TabSpec:
    """Return the Country tab.

    Args:
        content_y: Y position where tab content starts.

    Returns:
        The tab specification.
    """
    return TabSpec(TAB_COUNTRY, "country", _EFFECTS, _TRIGGERS, _elements(content_y))


def status_loc() -> str:
    """Return the ``RN_CountryStatus`` line under the two country fields.

    Returns:
        A ``defined_text`` that says the text is stored once :data:`COUNTRY_FLAG`
        is set, and what to do otherwise.
    """
    return defined_text(
        "RN_CountryStatus",
        [(f"has_country_flag = {COUNTRY_FLAG}", "RN_COUNTRY_STATUS_STORED")],
        "RN_COUNTRY_STATUS_READY",
    )


def apply_country_name_effect() -> str:
    """Return the ``rn_apply_country_name`` effect (native RN1 protocol).

    Returns:
        The effect with its explanatory comment banner.
    """
    name, adjective = COUNTRY_NAME_BUFFER, COUNTRY_ADJ_BUFFER
    return f"""# ============================================================== COUNTRY NAME - NATIVE RN1 PROTOCOL
# The cosmetic tag is the game's saved/synchronised carrier. The native plugin decodes both fields
# when looking up country localisation keys. Without it, the tag remains saved but display falls back
# to the original country name. Never treat {COUNTRY_FLAG} as proof that the plugin is active.
rn_apply_country_name = {{
	if = {{
		limit = {{
			rn_country_rename_enabled = yes
			check_variable = {{ {name.length} > 0 }}
			check_variable = {{ {adjective.length} > 0 }}
		}}
		meta_effect = {{
			text = {{ set_cosmetic_tag = "{RN1_PREFIX}|[N]|[J]|" }}
			N = "{slots_expr(name.prefix)}"
			J = "{slots_expr(adjective.prefix)}"
		}}
		set_country_flag = {COUNTRY_FLAG}
	}}
}}
# ============================================================== END COUNTRY NAME - NATIVE RN1 PROTOCOL
"""  # noqa: E501 - generated script lines are emitted verbatim
