"""Textures and sprite definitions of the input window.

Six small 32-bit TGA textures are drawn pixel by pixel: key, wide key, space
bar, invisible hit area, text field and a Backspace shortcut icon that vanilla
lacks. Colours follow the design system (``steel-bevel`` border, ``field-ink``
text field).
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

from modgen.common import GEN_HEADER
from modgen.features.input_window import (
    FIELD_SPRITE,
    INVISIBLE_SPRITE,
    KEY,
    KEY_H,
    KEY_SPRITE,
    SPACE_KEY_SPRITE,
    WIDE_KEY_SPRITE,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Rgba = tuple[int, int, int, int]
"""One pixel as (red, green, blue, alpha), each 0 to 255."""

TEXTURE_DIR = "gfx/interface/rename_anything"
"""Folder of the textures, relative to ``mod/``."""

TGA_TRUECOLOR = 2
"""TGA image type for uncompressed true-colour data."""

TGA_BITS_PER_PIXEL = 32
"""Pixel depth of every texture (BGRA)."""

TGA_DESCRIPTOR_TOP_LEFT_8BIT_ALPHA = 0x28
"""TGA image descriptor: 8 alpha bits and a top-left origin."""

TGA_HEADER_FORMAT = "<BBBHHBHHHHBB"
"""``struct`` layout of the 18-byte TGA header."""

TRANSPARENT: Rgba = (0, 0, 0, 0)
"""Fully transparent pixel."""

KEY_FILL: Rgba = (52, 50, 44, 240)
"""Interior colour of a key."""

STEEL_BEVEL: Rgba = (118, 119, 107, 255)
"""Border colour of keys and the text field (design system ``steel-bevel``)."""

KEY_HIGHLIGHT: Rgba = (96, 92, 80, 255)
"""Highlight line under the top border of a key."""

KEY_SHADOW: Rgba = (30, 29, 26, 240)
"""Darker band along the bottom of a key."""

KEY_SHADOW_ROWS = 3
"""Height in pixels of the darker band (including the bottom border)."""

FIELD_INK: Rgba = (22, 20, 18, 235)
"""Interior and highlight colour of the text field (design system ``field-ink``)."""

WIDE_KEY_WIDTH = 116
"""Width of the wide key texture (Caps, Backspace, Clear)."""

SPACE_KEY_WIDTH = 196
"""Width of the space bar texture."""

INVISIBLE_SIDE = 4
"""Side of the invisible hit area texture."""

FIELD_WIDTH = 520
"""Width of the text field texture."""

FIELD_HEIGHT = 40
"""Height of the text field texture."""

ICON_WIDTH = 34
"""Width of the Backspace icon (texticon)."""

ICON_HEIGHT = 16
"""Height of the Backspace icon, matching the vanilla shortcut icons."""

ICON_TOP_ROW = 1
"""First row of the Backspace icon outline."""

ICON_BOTTOM_ROW = 14
"""Last row of the Backspace icon outline."""

ICON_RIGHT_COLUMN = 32
"""Right edge column of the Backspace icon outline."""

ICON_ARROW_TIP = 8
"""Column of the outline's left edge in the middle rows (the arrow tip is at 1)."""

ICON_CROSS_X = 21
"""Column of the centre of the X drawn inside the Backspace icon."""

ICON_CROSS_Y = 7
"""Row of the centre of the X drawn inside the Backspace icon."""

ICON_CROSS_RADIUS = 3
"""Half-size in pixels of the X drawn inside the Backspace icon."""

ICON_LINE: Rgba = (208, 200, 176, 255)
"""Colour of the Backspace icon outline and X."""

ICON_FILL: Rgba = (36, 36, 36, 255)
"""Interior colour of the Backspace icon."""


def tga(w: int, h: int, px: Callable[[int, int], Rgba]) -> bytes:
    """Encode an uncompressed 32-bit TGA image.

    Args:
        w: Width in pixels.
        h: Height in pixels.
        px: Function returning the RGBA colour of pixel ``(x, y)``; ``(0, 0)``
            is the top-left corner.

    Returns:
        The complete TGA file contents (18-byte header and BGRA pixel rows).
    """
    head = struct.pack(
        TGA_HEADER_FORMAT,
        0,
        0,
        TGA_TRUECOLOR,
        0,
        0,
        0,
        0,
        0,
        w,
        h,
        TGA_BITS_PER_PIXEL,
        TGA_DESCRIPTOR_TOP_LEFT_8BIT_ALPHA,
    )
    body = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px(x, y)
            body += bytes((b, g, r, a))
    return head + bytes(body)


def key_px(
    w: int,
    h: int,
    fill: Rgba = KEY_FILL,
    border: Rgba = STEEL_BEVEL,
    hi: Rgba = KEY_HIGHLIGHT,
) -> Callable[[int, int], Rgba]:
    """Return a pixel function for a key-like rectangle.

    The rectangle has a one-pixel border with transparent corners, a highlight
    line under the top border and a darker band along the bottom.

    Args:
        w: Width in pixels.
        h: Height in pixels.
        fill: Interior colour.
        border: Border colour.
        hi: Highlight colour of row 1.

    Returns:
        A function mapping ``(x, y)`` to an RGBA colour.
    """

    def f(x: int, y: int) -> Rgba:
        """Return the colour of one pixel of the key rectangle.

        Args:
            x: Pixel column.
            y: Pixel row.

        Returns:
            The RGBA colour.
        """
        if x == 0 or y == 0 or x == w - 1 or y == h - 1:
            if (x in {0, w - 1}) and (y in {0, h - 1}):
                return TRANSPARENT  # rounded-ish corners
            return border
        if y == 1:
            return hi
        if y >= h - KEY_SHADOW_ROWS:
            return KEY_SHADOW
        return fill

    return f


def backspace_icon_px(x: int, y: int) -> Rgba:
    """Return one pixel of the 34x16 Backspace texticon.

    It draws an outlined arrow-shaped key with an X inside, matching the height
    of the vanilla shortcut icons.

    Args:
        x: Pixel column.
        y: Pixel row.

    Returns:
        The RGBA colour of that pixel.
    """
    top, bottom, right = ICON_TOP_ROW, ICON_BOTTOM_ROW, ICON_RIGHT_COLUMN
    if not top <= y <= bottom:
        return TRANSPARENT
    left = ICON_ARROW_TIP - min(y - top, bottom - y)
    if not left <= x <= right:
        return TRANSPARENT
    if x in {left, right} or y in {top, bottom}:
        return ICON_LINE
    dx, dy = abs(x - ICON_CROSS_X), abs(y - ICON_CROSS_Y)
    if dx <= ICON_CROSS_RADIUS and dy <= ICON_CROSS_RADIUS and dx == dy:
        return ICON_LINE
    return ICON_FILL


def transparent_px(_x: int, _y: int) -> Rgba:
    """Return a transparent pixel for every position (the invisible hit area texture).

    Args:
        _x: Pixel column (unused).
        _y: Pixel row (unused).

    Returns:
        :data:`TRANSPARENT`.
    """
    return TRANSPARENT


def gen_textures() -> dict[str, bytes]:
    """Generate every TGA texture.

    Returns:
        File name mapped to TGA contents.
    """
    return {
        "rn_key.tga": tga(KEY, KEY_H, key_px(KEY, KEY_H)),
        "rn_key_wide.tga": tga(WIDE_KEY_WIDTH, KEY_H, key_px(WIDE_KEY_WIDTH, KEY_H)),
        "rn_key_space.tga": tga(SPACE_KEY_WIDTH, KEY_H, key_px(SPACE_KEY_WIDTH, KEY_H)),
        "rn_invisible.tga": tga(INVISIBLE_SIDE, INVISIBLE_SIDE, transparent_px),
        "rn_backspace_icon.tga": tga(ICON_WIDTH, ICON_HEIGHT, backspace_icon_px),
        "rn_field.tga": tga(
            FIELD_WIDTH,
            FIELD_HEIGHT,
            key_px(FIELD_WIDTH, FIELD_HEIGHT, fill=FIELD_INK, border=STEEL_BEVEL, hi=FIELD_INK),
        ),
    }


def gen_gfx() -> str:
    """Generate the sprite definitions file.

    Returns:
        Contents of ``rename_anything.gfx`` for the key, field, invisible and
        ``GFX_BACKSPACE`` sprites.
    """
    sprites = [
        (KEY_SPRITE, "rn_key.tga"),
        (WIDE_KEY_SPRITE, "rn_key_wide.tga"),
        (SPACE_KEY_SPRITE, "rn_key_space.tga"),
        (INVISIBLE_SPRITE, "rn_invisible.tga"),
    ]
    o = [GEN_HEADER, "spriteTypes = {\n"]
    o.extend(
        f'\tspriteType = {{\n\t\tname = "{name}"\n'
        f'\t\ttexturefile = "{TEXTURE_DIR}/{f}"\n'
        '\t\tnoOfFrames = 1\n\t\teffectFile = "gfx/FX/buttonstate.lua"\n\t}\n'
        for name, f in sprites
    )
    o.append(
        f'\tspriteType = {{\n\t\tname = "{FIELD_SPRITE}"\n'
        f'\t\ttexturefile = "{TEXTURE_DIR}/rn_field.tga"\n\t}}\n'
    )
    # Shortcut tooltips request GFX_<key name>. Vanilla has no BACKSPACE icon.
    o.append(
        '\tspriteType = {\n\t\tname = "GFX_BACKSPACE"\n'
        f'\t\ttexturefile = "{TEXTURE_DIR}/rn_backspace_icon.tga"\n'
        "\t\tlegacy_lazy_load = no\n\t}\n"
    )
    o.append("}\n")
    return "".join(o)
