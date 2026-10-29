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
from dataclasses import dataclass, field
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
"""Values from here on are small portraits (``SMALL_OFFSET + k``); below are large ones."""

LARGE_OFFSET = 5000
"""Large portraits outside the catalog get ``LARGE_OFFSET + j`` (below: catalog entries).

A character defined by ``instance`` blocks (1.19 DLC characters) is not in the portrait catalog,
so its large picture gets its own value; values below :data:`SMALL_OFFSET` use the large frame.
"""

DLC_OFFSET = 20000
"""Pictures that only a DLC folder has: ``DLC_OFFSET + p * DLC_BLOCK + j`` for DLC ``p``.

The value is game state and the same for every player; the row's ``_visible`` triggers test
``has_dlc`` (local UI only, as the portrait picker does) and show the unknown portrait to a
player without that DLC. ``j`` below :data:`DLC_SMALL` is a large picture, from it a small one.
"""

DLC_BLOCK = 1000
"""Values per DLC."""

DLC_SMALL = 500
"""First small-picture offset inside a DLC block."""

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

    tags: dict[str, str] = field(default_factory=dict)
    """Token to the country tag of the character (the group its comparison runs in)."""

    packs: tuple[str, ...] = ()
    """``has_dlc`` names of the DLC blocks, in block order (:data:`DLC_OFFSET`)."""


class _Picker:
    """Numbers the pictures of the mini portraits (catalog, extra large, small) as it meets them."""

    def __init__(self, catalog: portraits.PortraitCatalog) -> None:
        """Start with only the unknown portrait in use.

        Args:
            catalog: The portrait catalog (its entries keep their numbers).
        """
        self.catalog = catalog
        self.used: dict[int, str] = {0: UNKNOWN_TEXTURE}
        self.large: dict[str, int] = {}
        self.small: dict[str, int] = {}
        self.packs: list[str] = []
        self.dlc: dict[tuple[str, str], dict[str, int]] = {}

    def _number(self, index: dict[str, int], offset: int, texture: str) -> int:
        """Return the value of a texture in one range, numbering it on first use.

        Args:
            index: Texture to number within the range.
            offset: First value of the range minus one.
            texture: Texture file.

        Returns:
            The value.
        """
        value = offset + index.setdefault(texture, len(index) + 1)
        self.used[value] = texture
        return value

    def pick(
        self,
        pictures: dict[tuple[str, str], str],
        by_sprite: dict[str, int],
        known: dict[str, str],
    ) -> int | None:
        """Return the value of the best picture: catalog entry, other large one, small one.

        Args:
            pictures: ``(type, size)`` to sprite of a character or instance.
            by_sprite: Catalog sprite to catalog number (the entries this character may use).
            known: Sprite to texture file (the folders this character's pictures may come from).

        Returns:
            The value, or None when no picture is usable.
        """
        hit = next((x for k in KINDS if (x := pictures.get((k, "large"))) in by_sprite), None)
        if hit is not None:
            self.used[by_sprite[hit]] = self.catalog.textures[hit]
            return by_sprite[hit]
        for size, index, offset in (
            ("large", self.large, LARGE_OFFSET),
            ("small", self.small, SMALL_OFFSET),
        ):
            for kind in KINDS:
                sprite = pictures.get((kind, size))
                if sprite is not None and portraits.STEM.fullmatch(sprite) and sprite in known:
                    return self._number(index, offset, known[sprite])
        return None

    def pick_dlc(
        self, pictures: dict[tuple[str, str], str], dlc_sprites: dict[str, tuple[str, str]]
    ) -> int | None:
        """Return a DLC-block value for a picture that only a DLC folder has.

        Args:
            pictures: ``(type, size)`` to sprite of a character.
            dlc_sprites: Sprite to ``(has_dlc name, texture file)`` of the DLC folders.

        Returns:
            The value, or None when no picture of a DLC is usable.
        """
        for size, start in (("large", 0), ("small", DLC_SMALL)):
            for kind in KINDS:
                sprite = pictures.get((kind, size))
                if (
                    sprite is None
                    or not portraits.STEM.fullmatch(sprite)
                    or sprite not in dlc_sprites
                ):
                    continue
                dlc, texture = dlc_sprites[sprite]
                if dlc not in self.packs:
                    self.packs.append(dlc)
                index = self.dlc.setdefault((dlc, size), {})
                j = index.setdefault(texture, len(index) + 1)
                value = DLC_OFFSET + self.packs.index(dlc) * DLC_BLOCK + start + j
                self.used[value] = texture
                return value
        return None

    def check_ranges(self) -> None:
        """Stop when a range of values runs into the next one.

        Raises:
            ValueError: More catalog entries than LARGE_OFFSET, too many extra large pictures,
                or a DLC with more pictures of one size than its block holds.
        """
        if (
            len(self.catalog.entries) >= LARGE_OFFSET
            or len(self.large) >= SMALL_OFFSET - LARGE_OFFSET
            or len(self.small) >= DLC_OFFSET - SMALL_OFFSET
            or any(len(index) >= DLC_SMALL for index in self.dlc.values())
        ):
            msg = "portrait values overflow their range (LARGE_OFFSET / SMALL_OFFSET / DLC_SMALL)"
            raise ValueError(msg)


def build(
    characters: list[portraits.Character],
    catalog: portraits.PortraitCatalog,
    textures: dict[str, str],
    dlc_sprites: dict[str, tuple[str, str]] | None = None,
) -> CharPortraits:
    """Choose the portrait value of every character.

    A character with top-level portraits uses a base-game picture first; when only a DLC folder
    has its picture, it gets a DLC-block value (:data:`DLC_OFFSET`) that the list shows only to
    owners of that DLC. A character defined by ``instance`` blocks (DLC characters) gets the
    picture of one instance, chosen at build time: a DLC picture is fine there, because such an
    instance exists only with its DLC.

    Args:
        characters: Characters of ``common/characters``.
        catalog: The portrait catalog (its entries are reused).
        textures: Sprite name to texture file of the base game.
        dlc_sprites: Sprite name to ``(has_dlc name, texture file)`` of the DLC folders.

    Returns:
        The values and the textures of the used values.
    """
    dlc = dlc_sprites or {}
    base_sprites = {e.large: n for n, e in enumerate(catalog.entries, 1) if e.pack == 0}
    all_sprites = {e.large: n for n, e in enumerate(catalog.entries, 1)}
    with_dlc = {**{s: t for s, (_, t) in dlc.items()}, **textures}
    picker = _Picker(catalog)
    values: dict[str, int] = {}
    tags: dict[str, str] = {}
    for char in sorted(characters, key=lambda c: c.token):
        if char.token in values:
            continue
        value = None
        if char.portraits:
            value = picker.pick(char.portraits, base_sprites, textures)
            if value is None:
                value = picker.pick_dlc(char.portraits, dlc)
        else:
            options = [
                (condition, v)
                for condition, pictures in char.instances
                if (v := picker.pick(pictures, all_sprites, with_dlc)) is not None
            ]
            # One fixed value, never a has_dlc test: the value is game state (a character
            # variable) and must not depend on the player's DLC (inline_checks/portrait_cases.py).
            # The instance without a DLC requirement wins (every player has that picture); a
            # character with only DLC instances exists only with that DLC.
            base = [v for c, v in options if c == "always = yes" or c.startswith("NOT = { has_dlc")]
            value = base[0] if base else (options[0][1] if options else None)
        if value is not None:
            values[char.token] = value
            tags[char.token] = char.tag
    picker.check_ranges()
    return CharPortraits(values, dict(sorted(picker.used.items())), tags, tuple(picker.packs))


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
    dlc = {**portraits.read_base_sprites_in_dlc(game), **portraits.read_dlc_textures(game)}
    return build(chars, catalog, portraits.read_textures(game), dlc)


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


def row(token: str, action: str) -> str:
    """Return one comparison of :func:`effects`: a silent ownership guard, then ``is_character``.

    Args:
        token: Character token.
        action: Effect to run when the scope is that character.

    Returns:
        One script line, without indentation.
    """
    return (
        f"if = {{ limit = {{ ROOT = {{ has_character = {token} }} }}"
        f" if = {{ limit = {{ is_character = {token} }} {action} }} }}"
    )


def effects(data: CharPortraits) -> str:
    """Return ``rn_char_portrait_index`` (character scope).

    ``is_character = <token>`` looks the token up among the characters of the scope's country and
    logs "Input <token> is not a valid character" to error.log when it is not there (hoi4.exe
    1.19.4.0). One chain over every character of the game wrote one line per foreign token for
    every row (100 000 lines on the first page). The comparisons are therefore grouped by country:
    the Characters list holds ROOT's characters, so only the group of ROOT's tag runs.

    Inside the group, ``ROOT = { has_character = <token> }`` guards every ``is_character``
    (:func:`row`): in hoi4.exe 1.19.4.0 ``has_character`` (``CHasCharacterTrigger``, evaluate
    ``3F2B10``) resolves the token through the same country lookup (``58A860`` -> ``58A900`` ->
    ``1173230``) but has no log call, and it is true only for a character the country has, which
    every row is. So ``is_character`` only runs for tokens that resolve and never logs. The guard
    is a nested ``if``, not an ``else_if`` limit, so the result does not depend on whether a limit
    stops at its first false trigger; the tokens are unique, so at most one row matches.

    Args:
        data: The values and textures.

    Returns:
        The scripted effect file.
    """
    groups: dict[str, list[tuple[str, str]]] = {}
    rows_of = {t: f"set_variable = {{ {VALUE_VAR} = {v} }}" for t, v in data.values.items()}
    for token, action in sorted(rows_of.items()):
        groups.setdefault(data.tags.get(token, token[:3]), []).append((token, action))
    body = ""
    for g, (tag, rows) in enumerate(sorted(groups.items())):
        inner = "".join(f"\t\t\t{row(token, action)}\n" for token, action in rows)
        body += (
            f"\t\t{'if' if g == 0 else 'else_if'} = {{\n"
            f"\t\t\tlimit = {{ ROOT = {{ original_tag = {tag} }} }}\n{inner}\t\t}}\n"
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
