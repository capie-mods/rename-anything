"""Refresh gate of the legacy editor windows (scripted GUI ``dirty``).

By default the game updates a scripted GUI on every tick. With ``dirty =
<variable>`` it updates the GUI only when that variable of the GUI's scope
changes (``common/scripted_guis/_documentation.md``). The four tab windows and
the input window use :data:`DIRTY_VARIABLE` on the player country, and every
cause of a visible change bumps it:

* every click effect of those windows ends with ``ROOT = { rn_gui_touch = yes }``,
  after the buffer, flags and lists have changed (PID45148: a bump at the start
  of the effect can refresh the window before the typed character is in the
  buffer, so the field shows one keystroke late);
* the hand-written effects that other entry points call (the decision, the
  state view panel) bump it too, as their last line: ``rn_open_main``,
  ``rn_close_all``, ``rn_set_tab``, ``rn_open_input`` and ``rn_cancel_input``;
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

_CLICK = re.compile(r"^\t+\w+_click = \{", re.MULTILINE)
"""Opening of one click effect in a scripted GUI ``effects`` block."""

TOUCH = f"ROOT = {{ {TOUCH_EFFECT} = yes }}"
"""Statement that bumps the player's refresh counter from any scope (list rows are states)."""


def dirty_line() -> str:
    """Return the ``dirty`` line of a gated scripted GUI.

    Returns:
        The line, indented for a scripted GUI body.
    """
    return f"\t\tdirty = {DIRTY_VARIABLE}\n"


def _closing_brace(text: str, opening: int) -> int:
    """Return the index of the brace that closes the one at ``opening``.

    Args:
        text: Script text.
        opening: Index of an opening brace.

    Returns:
        Index of the matching closing brace.

    Raises:
        ValueError: The braces are not balanced.
    """
    depth = 0
    for i in range(opening, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    msg = f"unbalanced click effect at {opening}"
    raise ValueError(msg)


def touch_clicks(effects: str) -> str:
    """Make every click effect end with :data:`TOUCH`.

    The bump is the last statement, so the counter changes only after the
    buffer, flags and lists have their new values. ROOT is the player country
    even in a list row whose scope is the row's state.

    Args:
        effects: Lines of a scripted GUI ``effects`` block.

    Returns:
        The same lines with ``ROOT = { rn_gui_touch = yes }`` before the closing
        brace of each ``<name>_click = {``.
    """
    out = []
    pos = 0
    for match in _CLICK.finditer(effects):
        close = _closing_brace(effects, match.end() - 1)
        if "\n" in effects[match.start() : close]:
            # Multi-line effect: the bump becomes the last line, one level deeper than the brace.
            line_start = effects.rfind("\n", 0, close) + 1
            indent = effects[line_start:close]
            out.append(f"{effects[pos:line_start]}{indent}\t{TOUCH}\n")
            pos = line_start
        else:
            out.append(f"{effects[pos:close].rstrip(' ')} {TOUCH} ")
            pos = close
    out.append(effects[pos:])
    return "".join(out)


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
