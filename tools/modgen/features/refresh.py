"""Refresh gate of the legacy editor windows (scripted GUI ``dirty``).

By default the game updates a scripted GUI on every tick. With ``dirty =
<variable>`` it updates the GUI only when that variable of the GUI's scope
changes (``common/scripted_guis/_documentation.md``). The four tab windows and
the input window use :data:`DIRTY_VARIABLE` on the player country, and every
cause of a visible change bumps it:

* every click effect of those windows starts with ``ROOT = { rn_gui_touch = yes }``;
* the hand-written effects that other entry points call (the decision, the
  state view panel) bump it too: ``rn_open_main``, ``rn_close_all``,
  ``rn_set_tab``, ``rn_open_input`` and ``rn_cancel_input``;
* a daily on-action bumps it for a human player whose editor is open, so the
  cooldown tooltips and buttons follow the date and game events that rename,
  promote or remove a character or state show up within one game day.

The state view panel keeps the default update: its scope is the selected
state, which changes without any effect running.
"""

from __future__ import annotations

import re

DIRTY_VARIABLE = "rn_gui_dirty"
"""Country variable whose change makes the legacy editor windows update."""

DIRTY_WRAP = 999999
"""Value above which the counter restarts at 0 (still a change, far below the variable range)."""

TOUCH_EFFECT = "rn_gui_touch"
"""Scripted effect that bumps :data:`DIRTY_VARIABLE`."""

ON_ACTIONS_FILE = "common/on_actions/rename_anything_on_actions.txt"
"""Daily refresh on-action, relative to ``mod/``."""

_CLICK = re.compile(r"^(\t+\w+_click = \{)", re.MULTILINE)
"""Opening of one click effect in a scripted GUI ``effects`` block."""


def dirty_line() -> str:
    """Return the ``dirty`` line of a gated scripted GUI.

    Returns:
        The line, indented for a scripted GUI body.
    """
    return f"\t\tdirty = {DIRTY_VARIABLE}\n"


def touch_clicks(effects: str) -> str:
    """Make every click effect start with :data:`TOUCH_EFFECT`.

    Args:
        effects: Lines of a scripted GUI ``effects`` block.

    Returns:
        The same lines with ``ROOT = { rn_gui_touch = yes }`` after each
        ``<name>_click = {``. ROOT is the player country even in a list row whose
        scope is the row's state.
    """
    return _CLICK.sub(rf"\1 ROOT = {{ {TOUCH_EFFECT} = yes }}", effects)


def touch_effect() -> str:
    """Return the scripted effect that bumps the refresh counter.

    Returns:
        ``rn_gui_touch`` (COUNTRY scope) with its comment line.
    """
    return f"""# Legacy editor refresh gate: any change of {DIRTY_VARIABLE} updates its windows (COUNTRY scope).
{TOUCH_EFFECT} = {{
	add_to_variable = {{ {DIRTY_VARIABLE} = 1 }}
	if = {{ limit = {{ check_variable = {{ {DIRTY_VARIABLE} > {DIRTY_WRAP} }} }} set_variable = {{ {DIRTY_VARIABLE} = 0 }} }}
}}
"""  # noqa: E501 - generated script lines are emitted verbatim


def on_actions() -> str:
    """Return the daily on-action that keeps an open legacy editor current.

    ``on_daily`` runs once a day for every country; the limit keeps the work to
    a flag check for AI countries and closed editors.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE` (without the generated header).
    """
    return f"""# Daily refresh of the legacy editor windows (dirty = {DIRTY_VARIABLE}): cooldown
# days and game events that change a character or state show up within one game day.
on_actions = {{
	on_daily = {{
		effect = {{
			if = {{
				limit = {{ is_ai = no has_country_flag = rn_open }}
				{TOUCH_EFFECT} = yes
			}}
		}}
	}}
}}
"""
