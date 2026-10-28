"""Mini portraits in the Characters list (maintainer request 2026-10-27).

The game gives scripted GUI no portrait of a character (the Character localisation object has no
portrait getter). A scripted GUI ``image`` property may build a sprite name from the NUMBER a
dynamic list row holds, as the flag picker does (``GFX_rnfm_[?rn_fp_v|0]``). It does not resolve
a variable read through a typed character variable (first in-game test, 2026-10-27: every row
showed the default sprite). So:

* the generator numbers a portrait value for every character of ``common/characters``:
  ``n`` (1..9999) = portrait catalog entry ``n`` (its large base-game portrait, 156 x 210),
  ``10000 + k`` = the character's small portrait ``k`` (an idea-style picture, most advisers),
  ``0`` = the game's unknown portrait;
* sprites ``GFX_rnchp_<value>`` alias those textures;
* ``rn_char_portrait_index`` (character scope) stores the value on the character
  (``rn_cp_v``, cached with the table fingerprint in ``rn_cp_c``) and hands it back in the temp
  variable ``rn_cp_t``;
* ``rn_build_char_page`` collects the values of the page's characters into ``rn_chars_pp``, and a
  second grid over the list shows one icon per row from that numeric array.

DLC portraits are left out (their texture is missing without the DLC). Characters that another mod
adds are not in the base game's ``common/characters`` and show the unknown portrait; a runtime list
needs CAPIE (backlog).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from modgen.common import GEN_HEADER
from modgen.features import portraits
from modgen.features.catalog_common import read_tags

GFX_FILE = "interface/rn_char_portraits.gfx"
"""Sprites of the mini portraits (``GFX_rnchp_<value>``)."""

EFFECTS_FILE = "common/scripted_effects/rn_char_portraits.txt"
"""The ``rn_char_portrait_index`` effect."""

KINDS = ("civilian", "army", "navy")
"""Portrait types in the order a character's portrait is taken from."""

SMALL_OFFSET = 10000
"""Values from here on are small portraits (``SMALL_OFFSET + k``); below are catalog entries."""

UNKNOWN_TEXTURE = "gfx/leaders/leader_unknown.dds"
"""Texture of value 0, the game's unknown portrait (``GFX_portrait_unknown``, 156 x 210)."""

VALUE_VAR = "rn_cp_v"
"""Character variable: the portrait value."""

CACHE_VAR = "rn_cp_c"
"""Character variable: fingerprint of the table the value comes from."""

TEMP_VAR = "rn_cp_t"
"""Temp variable the effect hands the value back in (read by ``rn_build_char_page``)."""


@dataclass(frozen=True)
class CharPortraits:
    """The portrait value of every base-game character, by token, with the sprite textures."""

    values: dict[str, int]
    """Token to portrait value (characters without a portrait are absent: value 0)."""

    textures: dict[int, str]
    """Portrait value to texture file, value 0 included."""


def build(
    characters: list[portraits.Character],
    catalog: portraits.PortraitCatalog,
    textures: dict[str, str],
) -> CharPortraits:
    """Choose the portrait value of every character.

    Args:
        characters: Characters of ``common/characters``.
        catalog: The portrait catalog (its base-game entries are reused).
        textures: Sprite name to texture file of the base game.

    Returns:
        The values and the textures of the used values.
    """
    by_sprite = {e.large: n for n, e in enumerate(catalog.entries, 1) if e.pack == 0}
    values: dict[str, int] = {}
    used: dict[int, str] = {0: UNKNOWN_TEXTURE}
    small_index: dict[str, int] = {}
    for char in sorted(characters, key=lambda c: c.token):
        if char.token in values:
            continue
        hit = next((s for k in KINDS if (s := char.portraits.get((k, "large"))) in by_sprite), None)
        if hit is not None:
            n = by_sprite[hit]
            values[char.token] = n
            used[n] = catalog.textures[hit]
            continue
        for kind in KINDS:
            sprite = char.portraits.get((kind, "small"))
            if sprite is not None and portraits.STEM.fullmatch(sprite) and sprite in textures:
                k = small_index.setdefault(textures[sprite], len(small_index) + 1)
                values[char.token] = SMALL_OFFSET + k
                used[SMALL_OFFSET + k] = textures[sprite]
                break
    return CharPortraits(values, dict(sorted(used.items())))


def read(root: str, catalog: portraits.PortraitCatalog) -> CharPortraits:
    """Read the characters of a HOI4 installation and choose their portraits.

    Args:
        root: Game installation folder.
        catalog: The portrait catalog of the same installation.

    Returns:
        The values and textures.
    """
    game = Path(root)
    tags = set(read_tags(root))
    chars: list[portraits.Character] = []
    for path in sorted((game / "common" / "characters").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        chars += portraits.characters_of(text, path.stem, tags)
    return build(chars, catalog, portraits.read_textures(game))


def gfx(data: CharPortraits) -> str:
    """Return the sprites ``GFX_rnchp_<value>``.

    Args:
        data: The values and textures.

    Returns:
        The ``.gfx`` file.
    """
    lines = "".join(
        f'\tspriteType = {{ name = "GFX_rnchp_{value}" texturefile = "{texture}" }}\n'
        for value, texture in data.textures.items()
    )
    return (
        f"{GEN_HEADER}# Mini portraits of the Characters list: GFX_rnchp_<value>"
        " (char_portraits.py).\n"
        f"spriteTypes = {{\n{lines}}}\n"
    )


def fingerprint(data: CharPortraits) -> int:
    """Return a stable fingerprint of the table (a new table recomputes every cached value).

    Args:
        data: The values and textures.

    Returns:
        An integer from 1 to 99991 (a plain script number).
    """
    text = "|".join(f"{t}={v}" for t, v in sorted(data.values.items()))
    text += "#" + "|".join(f"{v}={t}" for v, t in data.textures.items())
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) % 99991 + 1


def effects(data: CharPortraits) -> str:
    """Return ``rn_char_portrait_index`` (character scope).

    Args:
        data: The values and textures.

    Returns:
        The scripted effect file.
    """
    body = "".join(
        f"\t\t{'if' if i == 0 else 'else_if'} = {{ limit = {{ is_character = {token} }}"
        f" set_variable = {{ {VALUE_VAR} = {value} }} }}\n"
        for i, (token, value) in enumerate(sorted(data.values.items()))
    )
    fp = fingerprint(data)
    return (
        f"{GEN_HEADER}# Characters list mini portraits (char_portraits.py)."
        " CHARACTER scope: stores the\n"
        f"# portrait value in {VALUE_VAR} (cached per table in {CACHE_VAR})"
        f" and returns it in temp {TEMP_VAR}.\n"
        "rn_char_portrait_index = {\n"
        f"\tif = {{\n\t\tlimit = {{ NOT = {{ check_variable = {{ {CACHE_VAR} = {fp} }} }} }}\n"
        f"\t\tset_variable = {{ {VALUE_VAR} = 0 }}\n"
        f"\t\tset_variable = {{ {CACHE_VAR} = {fp} }}\n"
        f"{body}\t}}\n"
        f"\tset_temp_variable = {{ {TEMP_VAR} = {VALUE_VAR} }}\n"
        "}\n"
    )


def write_files(data: CharPortraits) -> list[tuple[str, str, bool]]:
    """Return the generated files.

    Args:
        data: The values and textures.

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    return [(GFX_FILE, gfx(data), False), (EFFECTS_FILE, effects(data), False)]
