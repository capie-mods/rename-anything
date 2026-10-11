"""Builders for the ``.gui`` interface elements of the legacy editor.

Every builder returns the element exactly as the generator has always written
it: two tabs of indentation for elements inside a window, one for windows.
"""

from __future__ import annotations

from typing import NamedTuple

from modgen.common import LIST_ROW_HEIGHT, LIST_WIDTH, PAGE

DEFAULT_FONT = "hoi_16mbs"
"""Font of ordinary text boxes and button captions."""

TITLE_FONT = "hoi_18mbs"
"""Font of window titles, section headers and the typed name."""

WINDOW_BACKGROUND_SPRITE = "GFX_tiled_window_2b_border"
"""Vanilla tiled sprite used as the background of every editor window."""

BUTTON_SMALL = "GFX_button_94x31"
"""Vanilla 94x31 button sprite (list rows, paging, Cities rows)."""

BUTTON_MEDIUM = "GFX_button_123x34"
"""Vanilla 123x34 button sprite (tabs, Country tab, input window)."""

BUTTON_WIDE = "GFX_button_261x34"
"""Vanilla 261x34 button sprite (the long country reset caption)."""

CLOSE_BUTTON = "GFX_closebutton"
"""Vanilla window close button sprite."""

TEXT_BOX_HEIGHT = 24
"""Default ``maxHeight`` of a single-line text box."""

TEXT_BOX_WIDTH = 500
"""Default ``maxWidth`` of a text box."""


# One keyword parameter per attribute of the GUI element, hence PLR0913.
def txt(  # noqa: PLR0913
    name: str,
    x: int,
    y: int,
    text: str,
    *,
    font: str = DEFAULT_FONT,
    w: int = TEXT_BOX_WIDTH,
    h: int = TEXT_BOX_HEIGHT,
    fmt: str = "left",
    extra: str = "",
) -> str:
    """Return one single-line ``instantTextBoxType`` element.

    Args:
        name: Element name.
        x: X position.
        y: Y position.
        text: Localisation key or literal text.
        font: Font name.
        w: ``maxWidth``.
        h: ``maxHeight``.
        fmt: Text alignment (``left``, ``centre`` or ``right``).
        extra: Raw text appended before the closing brace.

    Returns:
        The element line, indented by two tabs.
    """
    return (
        f'\t\tinstantTextBoxType = {{ name = "{name}" position = {{ x = {x} y = {y} }}'
        f' font = "{font}" '
        f'text = "{text}" maxWidth = {w} maxHeight = {h} format = {fmt} fixedsize = yes{extra} }}\n'
    )


# One keyword parameter per attribute of the GUI element, hence PLR0913.
def btn(  # noqa: PLR0913
    name: str,
    x: int,
    y: int,
    sprite: str,
    *,
    text: str | None = None,
    shortcut: str | None = None,
    font: str = DEFAULT_FONT,
    tooltip: str | None = None,
    indent: str = "\t\t",
) -> str:
    """Return one ``buttonType`` element.

    Args:
        name: Element name; its click effect is ``<name>_click``.
        x: X position.
        y: Y position.
        sprite: Sprite type.
        text: Button text key; text and font lines are omitted when empty.
        shortcut: Keyboard shortcut; omitted when empty.
        font: Button font, used only together with ``text``.
        tooltip: Tooltip key; omitted when empty.
        indent: Indentation of the opening line.

    Returns:
        The multi-line element block.
    """
    s = (
        f'{indent}buttonType = {{\n{indent}\tname = "{name}"\n'
        f'{indent}\tposition = {{ x = {x} y = {y} }}\n{indent}\tspriteType = "{sprite}"\n'
    )
    if text not in {None, ""}:
        s += f'{indent}\tbuttonText = "{text}"\n{indent}\tbuttonFont = "{font}"\n'
    if tooltip not in {None, ""}:
        s += f'{indent}\tpdx_tooltip = "{tooltip}"\n'
    if shortcut not in {None, ""}:
        s += f'{indent}\tshortcut = "{shortcut}"\n'
    s += f"{indent}\tclicksound = click_default\n{indent}}}\n"
    return s


def gridbox(name: str, position: tuple[int, int], size: tuple[int, int], slot_height: int) -> str:
    """Return a one-column ``gridBoxType`` that hosts a dynamic list.

    Args:
        name: Grid name (the dynamic list name in the scripted GUI).
        position: ``(x, y)`` position.
        size: ``(width, height)`` of the grid; rows have the same width.
        slot_height: Height of one row.

    Returns:
        The multi-line element block.
    """
    (x, y), (width, height) = position, size
    return (
        f'\t\tgridBoxType = {{\n\t\t\tname = "{name}"\n\t\t\tposition = {{ x = {x} y = {y} }}\n'
        f"\t\t\tsize = {{ width = {width} height = {height} }}\n"
        f"\t\t\tslotsize = {{ width = {width} height = {slot_height} }}\n"
        '\t\t\tmax_slots_horizontal = 1\n\t\t\tformat = "UPPER_LEFT"\n\t\t}\n'
    )


def window_header(name: str, width: int, height: int) -> str:
    """Return the opening of a centred main window.

    Args:
        name: Window name.
        width: Window width in pixels.
        height: Window height in pixels.

    Returns:
        The ``containerWindowType`` header lines up to the background.
    """
    return (
        f'\tcontainerWindowType = {{\n\t\tname = "{name}"\n\t\torientation = center\n'
        f"\t\tposition = {{ x = {-width // 2} y = {-height // 2} }}\n"
        f"\t\tsize = {{ width = {width} height = {height} }}\n\t\tclipping = no\n"
    )


def background(name: str) -> str:
    """Return the tiled border background line of an editor window.

    Args:
        name: Background element name.

    Returns:
        The ``background`` line.
    """
    return (
        f'\t\tbackground = {{ name = "{name}" quadTextureSprite = "{WINDOW_BACKGROUND_SPRITE}" }}\n'
    )


def entry_window(name: str, width: int, height: int) -> str:
    r"""Return the opening of a dynamic list row template.

    Args:
        name: Row container name (the ``entry_container`` of the list).
        width: Row width.
        height: Row height.

    Returns:
        The ``containerWindowType`` header; the caller adds elements and ``\\t}``.
    """
    return (
        f'\tcontainerWindowType = {{\n\t\tname = "{name}"\n'
        f"\t\tsize = {{ width = {width} height = {height} }}\n\t\tclipping = no\n"
    )


WINDOW_END = "\t}\n"
"""Closing brace of a window or row template."""

PAGE_BUTTON_GAP = 8
"""Vertical gap between the last list row and the paging buttons."""

PAGE_LABEL_OFFSET = 6
"""Vertical offset of the page counter text relative to the paging buttons."""


class PagedList(NamedTuple):
    """Element names of a paged list (Characters or States tab)."""

    tab: str
    """Tab name used in the counter element name (``rn_<tab>_page``)."""

    grid: str
    """Grid name (the dynamic list in the scripted GUI)."""

    prev: str
    """Name of the Prev button."""

    next: str
    """Name of the Next button."""

    page_key: str
    """Localisation key of the page counter."""


def paged_list(names: PagedList, y0: int) -> list[str]:
    """Return a list grid of :data:`~modgen.common.PAGE` rows with Prev, Next and a counter.

    Args:
        names: Element names of the list.
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    py = y0 + PAGE * LIST_ROW_HEIGHT + PAGE_BUTTON_GAP
    counter = f"rn_{names.tab}_page"
    return [
        gridbox(names.grid, (20, y0), (LIST_WIDTH, PAGE * LIST_ROW_HEIGHT), LIST_ROW_HEIGHT),
        btn(names.prev, 20, py, BUTTON_SMALL, text="RN_BTN_PREV"),
        txt(counter, 130, py + PAGE_LABEL_OFFSET, names.page_key, w=300, fmt="centre"),
        btn(names.next, 446, py, BUTTON_SMALL, text="RN_BTN_NEXT"),
    ]
