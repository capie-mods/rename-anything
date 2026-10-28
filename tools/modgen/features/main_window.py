"""The main Rename window: one window and one scripted GUI per tab.

Element-level ``_visible`` triggers on child containers do not work in 1.19.3
(verified live), so each tab is a complete window with its own scripted GUI and
its own ``visible`` block. This slice owns the frame every tab shares (title,
close button, tab buttons, the open/input flags) and asks the tab slices for
their content through :class:`TabSpec`.
"""

from __future__ import annotations

from dataclasses import dataclass

from modgen.common import TAB_COUNTRY
from modgen.features import refresh
from modgen.gui import (
    BUTTON_MEDIUM,
    CLOSE_BUTTON,
    TITLE_FONT,
    WINDOW_END,
    background,
    btn,
    txt,
    window_header,
)

WINDOW_WIDTH = 560
"""Width of every main tab window and of the input window."""

WINDOW_HEIGHT = 520
"""Height of every main tab window."""

CONTENT_Y = 86
"""Y position where a tab's own content starts, under the tab buttons."""

TAB_BUTTON_Y = 42
"""Y position of the tab buttons."""

TAB_BUTTON_PITCH = 132
"""Horizontal distance between neighbouring tab buttons."""

CLOSE_BUTTON_INSET = 42
"""Distance of the close button from the right window edge."""


@dataclass(frozen=True)
class DynamicList:
    """A scripted GUI ``dynamic_lists`` entry of one tab."""

    grid: str
    """Grid element that shows the rows."""

    array: str
    """Country array the rows come from."""

    entry: str
    """Row template window (``entry_container``)."""

    row_context: str
    """Scope lines of the entry, already indented (``change_scope`` and maybe ``value``)."""


@dataclass(frozen=True)
class TabSpec:
    """Everything one tab slice contributes to the main window.

    A frozen dataclass rather than a protocol: the tabs differ only in data
    (text fragments), not in behaviour, so one value type is enough.
    """

    number: int
    """Value of ``rn_tab`` that shows this tab."""

    name: str
    """Tab name used in window and scripted GUI names (``rn_main_<name>_window``)."""

    effects: str
    """Tab-specific scripted GUI effect lines (three tabs of indentation)."""

    triggers: str
    """Tab-specific scripted GUI trigger lines (three tabs of indentation)."""

    elements: tuple[str, ...]
    """``.gui`` element blocks of the tab content, in drawing order."""

    dynamic_list: DynamicList | None = None
    """The tab's list of rows, if it has one."""

    properties: str = ""
    """Scripted GUI ``properties`` lines (three tabs of indentation), e.g. a row image."""

    extra_lists: tuple[DynamicList, ...] = ()
    """Further dynamic lists of the tab (e.g. a grid drawn over the rows)."""


def _header_effects(tabs: list[TabSpec]) -> str:
    """Return the close and tab-switch click effects every tab GUI shares.

    Args:
        tabs: All tabs, in tab order.

    Returns:
        Effect lines for ``rn_close`` and ``rn_tab_<n>``.
    """
    return "\t\t\trn_close_click = { rn_close_all = yes }\n" + "".join(
        f"\t\t\trn_tab_{tab.number}_click = {{ set_temp_variable = {{ rn_newtab = {tab.number} }}"
        " rn_set_tab = yes }\n"
        for tab in tabs
    )


def _visible_condition(number: int) -> str:
    """Return the ``rn_tab`` condition that shows a tab.

    Args:
        number: Tab number.

    Returns:
        The trigger; the Country tab is also shown while ``rn_tab`` is unset.
    """
    if number == TAB_COUNTRY:
        return f"NOT = {{ check_variable = {{ rn_tab > {TAB_COUNTRY} }} }}"
    return f"check_variable = {{ rn_tab = {number} }}"


def scripted_guis(tabs: list[TabSpec]) -> str:
    """Return the scripted GUI blocks of every tab window.

    Args:
        tabs: All tabs, in tab order.

    Returns:
        One ``rn_main_<name>_gui`` block per tab, each followed by a blank line.
    """
    header_effects = _header_effects(tabs)
    dirty = refresh.dirty_line()
    out = []
    for tab in tabs:
        out.append(f"""	rn_main_{tab.name}_gui = {{
		context_type = player_context
		window_name = "rn_main_{tab.name}_window"
		visible = {{
			has_country_flag = rn_open
			NOT = {{ has_country_flag = rn_input }}
			{_visible_condition(tab.number)}
		}}
		ai_enabled = {{ always = no }}
{dirty}		effects = {{
{refresh.touch_clicks(header_effects + tab.effects)}		}}
		triggers = {{
			rn_tab_{tab.number}_click_enabled = {{ always = no }}
{tab.triggers}		}}
""")
        if tab.properties:
            out.append(f"""		properties = {{
{tab.properties}		}}
""")
        lists = ((tab.dynamic_list,) if tab.dynamic_list is not None else ()) + tab.extra_lists
        if lists:
            body = "".join(
                f"""			{dyn.grid} = {{
				array = {dyn.array}
{dyn.row_context}
				entry_container = "{dyn.entry}"
			}}
"""
                for dyn in lists
            )
            out.append(f"""		dynamic_lists = {{
{body}		}}
""")
        out.append("\t}\n\n")
    return "".join(out)


def windows(tabs: list[TabSpec]) -> str:
    """Return the ``.gui`` window of every tab.

    Args:
        tabs: All tabs, in tab order.

    Returns:
        One ``containerWindowType`` block per tab with the title, close button,
        tab buttons and the tab's own content, each followed by a blank line.
    """
    out = []
    for tab in tabs:
        out.append(window_header(f"rn_main_{tab.name}_window", WINDOW_WIDTH, WINDOW_HEIGHT))
        out.append(background("rn_main_bg"))
        out.append(txt("rn_main_title", 20, 12, "RN_MAIN_TITLE", font=TITLE_FONT, w=480))
        out.append(
            btn(
                "rn_close",
                WINDOW_WIDTH - CLOSE_BUTTON_INSET,
                8,
                CLOSE_BUTTON,
                tooltip="RN_CLOSE_TT",
            )
        )
        out.extend(
            btn(
                f"rn_tab_{other.number}",
                20 + (other.number - 1) * TAB_BUTTON_PITCH,
                TAB_BUTTON_Y,
                BUTTON_MEDIUM,
                text=f"RN_TAB_{other.number}",
            )
            for other in tabs
        )
        out.extend(tab.elements)
        out.append(WINDOW_END + "\n")
    return "".join(out)
