"""Shared GUI builders of the generated pickers (flag picker, portrait picker).

Window bodies are written as indented blocks: ``instantTextboxType``,
``buttonType`` and ``iconType`` with their position and sprite, captioned text
buttons, grid boxes for dynamic lists, a letter row, and the transparent hit-area
sprites that vanilla lacks for small text buttons and list rows.
"""

from __future__ import annotations

from modgen.common import GEN_HEADER
from modgen.features.catalog_common import LETTERS
from modgen.features.textures import TEXTURE_DIR, tga, transparent_px

HIT_SPRITES = {
    "GFX_rn_hit_row": ("rn_hit_row.tga", (130, 16)),
    "GFX_rn_hit_letter": ("rn_hit_letter.tga", (14, 16)),
    "GFX_rn_hit_other": ("rn_hit_other.tga", (52, 16)),
    "GFX_rn_hit_row108": ("rn_hit_row108.tga", (108, 16)),
}
"""Transparent hit areas: sprite name to (texture file, size)."""


def text(
    name: str, pos: tuple[int, int], text: str, size: tuple[int, int], *, extra: str = ""
) -> str:
    """Return one ``instantTextBoxType`` block.

    Args:
        name: Element name.
        pos: Position.
        text: Localisation key.
        size: ``maxWidth`` and ``maxHeight``.
        extra: Additional attribute lines (already indented).

    Returns:
        The block, indented for a window body.
    """
    return (
        f'\t\tinstantTextboxType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\tfont = "Arial12"\n\t\t\ttext = "{text}"\n'
        f"\t\t\tmaxWidth = {size[0]}\n\t\t\tmaxHeight = {size[1]}\n"
        f"\t\t\tfixedsize = yes\n{extra}\t\t\talwaystransparent = yes\n\t\t}}\n"
    )


def button(
    name: str, pos: tuple[int, int], sprite: str, *, attrs: str = "", quad: bool = False
) -> str:
    """Return one ``buttonType`` block.

    Args:
        name: Element name.
        pos: Position.
        sprite: Sprite name (vanilla or a hit area).
        attrs: Additional attribute lines (already indented).
        quad: Use ``quadTextureSprite`` (a framed sprite) instead of ``spriteType``.

    Returns:
        The block, indented for a window body.
    """
    kind = "quadTextureSprite" if quad else "spriteType"
    return (
        f'\t\tbuttonType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\t{kind} = "{sprite}"\n{attrs}\t\t\tclicksound = click_default\n\t\t}}\n'
    )


def icon(name: str, pos: tuple[int, int], sprite: str, *, attrs: str = "") -> str:
    """Return one ``iconType`` block.

    Args:
        name: Element name.
        pos: Position.
        sprite: Sprite (``spriteType``, or ``quadTextureSprite`` for a framed sprite in attrs).
        attrs: Additional attribute lines (already indented).

    Returns:
        The block, indented for a window body.
    """
    return (
        f'\t\ticonType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f'\t\t\tspriteType = "{sprite}"\n{attrs}\t\t}}\n'
    )


def captioned(text: str, tip: str) -> str:
    """Return the caption, font and tooltip lines of a text button.

    Args:
        text: Caption key.
        tip: Tooltip key.

    Returns:
        Attribute lines.
    """
    return (
        f'\t\t\tbuttonText = "{text}"\n\t\t\tbuttonFont = "hoi_16mbs"\n'
        f'\t\t\tpdx_tooltip = "{tip}"\n'
    )


def gridbox(name: str, pos: tuple[int, int], slot: tuple[int, int], columns: int, rows: int) -> str:
    """Return a ``gridBoxType`` for a dynamic list.

    Args:
        name: Dynamic list name.
        pos: Position.
        slot: Slot size.
        columns: Slots per row.
        rows: Rows.

    Returns:
        The block.
    """
    return (
        f'\t\tgridBoxType = {{\n\t\t\tname = "{name}"\n'
        f"\t\t\tposition = {{ x = {pos[0]} y = {pos[1]} }}\n"
        f"\t\t\tsize = {{ width = {slot[0] * columns} height = {slot[1] * rows} }}\n"
        f"\t\t\tslotsize = {{ width = {slot[0]} height = {slot[1]} }}\n"
        f'\t\t\tmax_slots_horizontal = {columns}\n\t\t\tformat = "UPPER_LEFT"\n\t\t}}\n'
    )


def hit_gfx() -> str:
    """Return the hit area sprites.

    Returns:
        A complete ``spriteTypes`` file.
    """
    body = "".join(
        f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{TEXTURE_DIR}/{file}"\n'
        '\t\tnoOfFrames = 1\n\t\teffectFile = "gfx/FX/buttonstate.lua"\n\t}\n'
        for name, (file, _) in HIT_SPRITES.items()
    )
    return GEN_HEADER + "spriteTypes = {\n" + body + "}\n"


def hit_textures() -> dict[str, bytes]:
    """Return the transparent hit area textures.

    Returns:
        File name (in :data:`~modgen.features.textures.TEXTURE_DIR`) to TGA bytes.
    """
    return {file: tga(w, h, transparent_px) for file, (w, h) in HIT_SPRITES.values()}


def letter_row(prefix: str, letters: tuple[int, ...], y: int, width: int) -> str:
    """Return a letter row: per letter a hit area and a normal and an active caption.

    The captions are the letter keys the flag catalog writes (``RN_FP_L_<letter>``
    and ``RN_FP_L_<letter>_ON``), the same in every language.

    Args:
        prefix: Element prefix (``rn_pp``); elements are ``<prefix>_letter_<n>``,
            ``<prefix>_lt_<n>`` and ``<prefix>_lta_<n>``.
        letters: Letters with entries (1..26).
        y: Top of the row.
        width: Width of one letter (the hit sprite ``GFX_rn_hit_letter`` is 14 px).

    Returns:
        Element blocks.
    """
    out = []
    fmt = "\t\t\tformat = centre\n"
    for n in letters:
        x = (n - 1) * width
        key = f"RN_FP_L_{LETTERS[n - 1]}"
        out.append(button(f"{prefix}_letter_{n}", (x, y), "GFX_rn_hit_letter"))
        out.append(text(f"{prefix}_lt_{n}", (x, y + 1), key, (width, 14), extra=fmt))
        out.append(text(f"{prefix}_lta_{n}", (x, y + 1), f"{key}_ON", (width, 14), extra=fmt))
    return "".join(out)


def letter_lines(
    prefix: str, letters: tuple[int, ...], shown: str, when: dict[int, str] | None = None
) -> tuple[list[str], list[str]]:
    """Return the letter click effects and their triggers.

    A click sets ``temp <prefix>_lt`` and runs ``<prefix>_pick_letter`` in ROOT;
    the active letter (``ROOT.<prefix>_letter``) is disabled and drawn highlighted.

    Args:
        prefix: Element and variable prefix (``rn_pp``).
        letters: Letters with entries (1..26).
        shown: Trigger body that shows the row.
        when: Extra condition of a letter (it has entries for the current filter), if any.

    Returns:
        ``(effects, triggers)``.
    """
    effects: list[str] = []
    triggers: list[str] = []
    for n in letters:
        effects.append(
            f"\t\t\t{prefix}_letter_{n}_click = {{ ROOT = {{ "
            f"set_temp_variable = {{ {prefix}_lt = {n} }} "
            f"{prefix}_pick_letter = yes }} }}\n"
        )
        on = f"check_variable = {{ {prefix}_letter = {n} }}"
        here = f"{shown} {(when or {}).get(n, '')}".strip()
        triggers += [
            f"\t\t\t{prefix}_letter_{n}_visible = {{ {here} }}\n",
            f"\t\t\t{prefix}_letter_{n}_click_enabled = {{ ROOT = {{ NOT = {{ {on} }} }} }}\n",
            f"\t\t\t{prefix}_lt_{n}_visible = {{ {here} ROOT = {{ NOT = {{ {on} }} }} }}\n",
            f"\t\t\t{prefix}_lta_{n}_visible = {{ {here} ROOT = {{ {on} }} }}\n",
        ]
    return effects, triggers
