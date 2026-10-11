"""Builders for the Paradox script constructs the generator writes many times.

The builders produce exactly the text the generator has always written (tab
indentation, single spaces inside braces), so moving a hand-written f-string to
a builder never changes the output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

Branch = tuple[str, str]
"""One conditional ``defined_text`` branch as (trigger body, localisation key)."""


def text_branch(trigger: str, key: str) -> str:
    """Return one conditional ``text`` line of a ``defined_text`` block.

    Args:
        trigger: Trigger body written inside ``trigger = { ... }``.
        key: Localisation key shown when the trigger holds.

    Returns:
        The tab-indented line with its newline.
    """
    return f"\ttext = {{ trigger = {{ {trigger} }} localization_key = {key} }}\n"


def defined_text_open(name: str) -> str:
    """Return the opening lines of a ``defined_text`` block.

    Args:
        name: Scripted localisation name.

    Returns:
        ``defined_text = {`` and the ``name`` line.
    """
    return f"defined_text = {{\n\tname = {name}\n"


def defined_text_close(default_key: str) -> str:
    """Return the unconditional last branch and the closing brace of a ``defined_text``.

    Args:
        default_key: Localisation key shown when no trigger holds.

    Returns:
        The fallback ``text`` line and ``}``.
    """
    return f"\ttext = {{ localization_key = {default_key} }}\n}}\n"


def defined_text(name: str, branches: Iterable[Branch], default_key: str) -> str:
    """Return a complete ``defined_text`` block.

    Args:
        name: Scripted localisation name.
        branches: Conditional branches in priority order.
        default_key: Localisation key shown when no branch matches.

    Returns:
        The block text.
    """
    body = "".join(text_branch(trigger, key) for trigger, key in branches)
    return defined_text_open(name) + body + defined_text_close(default_key)


def check_variable(condition: str) -> str:
    """Return a ``check_variable`` trigger.

    Args:
        condition: Comparison such as ``rn_len > 0``.

    Returns:
        ``check_variable = { <condition> }``.
    """
    return f"check_variable = {{ {condition} }}"


def set_temp(name: str, value: object) -> str:
    """Return a ``set_temp_variable`` effect.

    Args:
        name: Temporary variable name.
        value: Value or variable reference.

    Returns:
        ``set_temp_variable = { <name> = <value> }``.
    """
    return f"set_temp_variable = {{ {name} = {value} }}"
