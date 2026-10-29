"""Colour presets of the country colour picker and the script that uses them.

The player picks a map colour for a country in the colour picker
(``colour_picker``). The picker offers :data:`PRESETS`, a palette of 90 distinct
map colours grouped by hue (the last row holds the game's own colours of the
great powers), red, green and blue steppers, and a colour code typed on a small
keypad. A colour is three integers ``0..255``, as in the game's ``colors.txt``;
CAPIE applies the game's country colour defines to it, as the game does with
``colors.txt`` (CONTRACT section 19).

Script cannot read a country's colour, so the generator reads the game's own
colours (:func:`read_natives`: ``common/countries/colors.txt`` per tag and
``common/countries/cosmetic.txt`` per cosmetic tag, HSV converted to RGB) and
writes them as a lookup. The picker starts at that colour, and a subject's
"My colour" copies the overlord's colour from it when the overlord has no
colour layer.

Generated files (relative to ``mod/``):

* ``interface/rn_colour_catalog.gfx``: one swatch sprite per preset
  (``GFX_rn_cp_sw_<n>``), the selection mark, the two keypad keys and the
  preview strip ``GFX_rn_cp_preview`` (512 frames, 3 bits per channel).
* ``gfx/interface/rename_anything/rn_cp_*.tga``: the textures of those sprites.
* ``common/scripted_effects/rn_colour_catalog.txt``: ``rn_cp_presets`` (the preset
  count), ``rn_cp_load_preset`` (a preset into ``rn_cp_r/g/b``),
  ``rn_cp_match_preset`` (the preset of the picked colour, 0 = none),
  ``rn_cp_native`` (the game's colour of the scope country), and the cosmetic tag
  snapshot of the colour layer, ``rn_cp_cos_write`` and ``rn_cp_cos_match``
  (``capie_cc_cos``, CONTRACT 19.2 / 17.3), built from the flag catalog's
  cosmetic tags.
* ``common/scripted_localisation/rn_colour_catalog.txt``: the colour cooldown's
  days left, the six hex digits of the picked colour, the typed code and its
  message.
* ``localisation/<lang>/rn_colour_catalog_l_<lang>.yml``: the preset names
  (English and Polish, the other languages English) and the hex digits.
"""

from __future__ import annotations

import colorsys
import re
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from modgen.common import GEN_HEADER, LANGS, POLISH
from modgen.features.catalog_common import STEM, days_left_loc, pack, read_tags, write_leaf
from modgen.features.textures import TEXTURE_DIR, tga
from modgen.script import check_variable, defined_text

if TYPE_CHECKING:
    from modgen.features.flags import FlagCatalog


class Preset(NamedTuple):
    """One preset colour."""

    english: str
    """English name (swatch tooltip)."""

    polish: str
    """Polish name."""

    rgb: tuple[int, int, int]
    """Red, green and blue, ``0..255`` each."""


PRESETS = (
    # Reds and pinks.
    Preset("Crimson", "Karmazynowy", (200, 30, 45)),
    Preset("Scarlet", "Szkarłatny", (230, 50, 40)),
    Preset("Red", "Czerwony", (220, 20, 20)),
    Preset("Dark red", "Ciemnoczerwony", (140, 15, 20)),
    Preset("Maroon", "Bordowy", (110, 25, 40)),
    Preset("Rose", "Różany", (230, 80, 110)),
    Preset("Pink", "Różowy", (240, 140, 180)),
    Preset("Light pink", "Jasnoróżowy", (250, 190, 210)),
    Preset("Salmon", "Łososiowy", (250, 128, 114)),
    Preset("Coral", "Koralowy", (240, 100, 80)),
    # Oranges and browns.
    Preset("Orange", "Pomarańczowy", (240, 135, 20)),
    Preset("Dark orange", "Ciemnopomarańczowy", (220, 100, 10)),
    Preset("Tangerine", "Mandarynkowy", (250, 160, 60)),
    Preset("Peach", "Brzoskwiniowy", (250, 190, 140)),
    Preset("Rust", "Rdzawy", (180, 70, 30)),
    Preset("Copper", "Miedziany", (185, 110, 60)),
    Preset("Brown", "Brązowy", (120, 70, 35)),
    Preset("Chocolate", "Czekoladowy", (90, 50, 25)),
    Preset("Sand", "Piaskowy", (200, 160, 110)),
    Preset("Khaki", "Khaki", (190, 170, 110)),
    # Yellows and olives.
    Preset("Amber", "Bursztynowy", (245, 185, 40)),
    Preset("Gold", "Złoty", (230, 190, 30)),
    Preset("Yellow", "Żółty", (240, 225, 50)),
    Preset("Lemon", "Cytrynowy", (250, 240, 120)),
    Preset("Cream", "Kremowy", (245, 235, 190)),
    Preset("Straw", "Słomkowy", (225, 200, 120)),
    Preset("Mustard", "Musztardowy", (200, 170, 40)),
    Preset("Ochre", "Ochrowy", (190, 140, 40)),
    Preset("Olive", "Oliwkowy", (140, 150, 40)),
    Preset("Dark olive", "Ciemnooliwkowy", (90, 100, 40)),
    # Greens.
    Preset("Lime", "Limonkowy", (150, 210, 60)),
    Preset("Light green", "Jasnozielony", (140, 220, 120)),
    Preset("Bright green", "Soczystozielony", (30, 200, 80)),
    Preset("Green", "Zielony", (40, 160, 60)),
    Preset("Emerald", "Szmaragdowy", (20, 150, 90)),
    Preset("Forest green", "Leśna zieleń", (25, 100, 45)),
    Preset("Dark green", "Ciemnozielony", (15, 70, 30)),
    Preset("Sage", "Szałwiowy", (140, 170, 120)),
    Preset("Moss", "Mszysty", (100, 120, 60)),
    Preset("Mint", "Miętowy", (150, 230, 180)),
    # Teals and cyans.
    Preset("Teal", "Morski", (20, 150, 140)),
    Preset("Dark teal", "Ciemnomorski", (15, 95, 95)),
    Preset("Sea green", "Zieleń morska", (46, 139, 110)),
    Preset("Turquoise", "Turkusowy", (60, 200, 200)),
    Preset("Aquamarine", "Akwamaryna", (100, 220, 190)),
    Preset("Cyan", "Cyjan", (30, 210, 230)),
    Preset("Light cyan", "Jasnocyjanowy", (160, 230, 240)),
    Preset("Petrol", "Naftowy", (20, 110, 130)),
    Preset("Steel blue", "Stalowoniebieski", (70, 130, 170)),
    Preset("Slate", "Łupkowy", (90, 110, 130)),
    # Blues.
    Preset("Sky blue", "Błękitny", (90, 170, 235)),
    Preset("Light blue", "Jasnoniebieski", (150, 200, 245)),
    Preset("Azure", "Lazurowy", (40, 130, 230)),
    Preset("Cornflower", "Chabrowy", (100, 140, 230)),
    Preset("Blue", "Niebieski", (30, 90, 200)),
    Preset("Royal blue", "Królewski niebieski", (50, 70, 190)),
    Preset("Cobalt", "Kobaltowy", (0, 70, 170)),
    Preset("Navy", "Granatowy", (25, 40, 120)),
    Preset("Midnight blue", "Nocny granat", (20, 25, 80)),
    Preset("Periwinkle", "Barwinkowy", (150, 150, 230)),
    # Purples and magentas.
    Preset("Indigo", "Indygo", (75, 50, 160)),
    Preset("Violet", "Fioletowy", (140, 70, 200)),
    Preset("Lavender", "Lawendowy", (190, 160, 230)),
    Preset("Lilac", "Liliowy", (200, 140, 200)),
    Preset("Purple", "Purpurowy", (110, 30, 110)),
    Preset("Plum", "Śliwkowy", (140, 60, 120)),
    Preset("Mauve", "Wrzosowy", (170, 110, 150)),
    Preset("Magenta", "Amarantowy", (210, 50, 160)),
    Preset("Fuchsia", "Fuksja", (240, 60, 200)),
    Preset("Wine", "Winny", (100, 20, 60)),
    # Neutrals.
    Preset("White", "Biały", (235, 235, 230)),
    Preset("Ivory", "Kość słoniowa", (240, 230, 210)),
    Preset("Beige", "Beżowy", (210, 195, 165)),
    Preset("Light grey", "Jasnoszary", (190, 190, 190)),
    Preset("Silver", "Srebrny", (160, 165, 170)),
    Preset("Grey", "Szary", (130, 130, 130)),
    Preset("Taupe", "Szarobrązowy", (120, 105, 90)),
    Preset("Dark grey", "Ciemnoszary", (80, 80, 80)),
    Preset("Charcoal", "Grafitowy", (55, 55, 60)),
    Preset("Black", "Czarny", (35, 35, 35)),
    # Map colours of the game (common/countries/colors.txt, HSV converted to RGB).
    Preset("German grey", "Niemiecki szary", (102, 96, 87)),
    Preset("British red", "Brytyjski czerwony", (201, 56, 93)),
    Preset("French blue", "Francuski niebieski", (57, 113, 228)),
    Preset("Soviet red", "Radziecki czerwony", (125, 13, 24)),
    Preset("Italian green", "Włoski zielony", (67, 127, 63)),
    Preset("American blue", "Amerykański niebieski", (20, 133, 237)),
    Preset("Japanese peach", "Japoński brzoskwiniowy", (255, 201, 178)),
    Preset("Chinese blue", "Chiński niebieski", (40, 40, 140)),
    Preset("Polish pink", "Polski różowy", (214, 102, 139)),
    Preset("Spanish yellow", "Hiszpański żółty", (242, 205, 94)),
)
"""The preset grid, in grid order (rows of :data:`~modgen.features.colour_picker.GRID_COLUMNS`)."""

CHANNEL_MAX = 255
"""Largest channel value."""

LEVELS = 8
"""Preview levels per channel (3 bits)."""

LEVEL_STEP = (CHANNEL_MAX + 1) // LEVELS
"""Channel values per preview level (32)."""

PREVIEW_FRAMES = LEVELS**3
"""Frames of the preview strip (512)."""

PREVIEW_FRAME = 8
"""Side of one preview frame in pixels."""

SWATCH = (22, 14)
"""Size of a swatch texture."""

MARK = (26, 18)
"""Size of the selection mark (two pixels around a swatch)."""

KEY = (22, 18)
"""Size of a keypad key (a digit or A..F)."""

KEY_WIDE = (56, 18)
"""Size of the keypad's Space, Delete and Clear keys."""

GFX_FILE = "interface/rn_colour_catalog.gfx"
"""Sprite file, relative to ``mod/``."""

EFFECTS_FILE = "common/scripted_effects/rn_colour_catalog.txt"
"""Generated effects, relative to ``mod/``."""

SCRIPTED_LOC_FILE = "common/scripted_localisation/rn_colour_catalog.txt"
"""Generated scripted localisation, relative to ``mod/``."""

PREVIEW_SPRITE = "GFX_rn_cp_preview"
"""Preview strip sprite."""

MARK_SPRITE = "GFX_rn_cp_mark"
"""Selection mark sprite."""

KEY_SPRITE = "GFX_rn_cp_key"
"""Keypad key sprite."""

KEY_WIDE_SPRITE = "GFX_rn_cp_key_wide"
"""Wide keypad key sprite."""

BORDER = (20, 20, 20, 255)
"""Swatch border colour."""

MARK_COLOUR = (255, 214, 0, 255)
"""Selection mark colour (vanilla highlight yellow)."""

KEY_EDGE = (120, 120, 110, 255)
"""Keypad key border."""

KEY_FILL = (38, 40, 42, 255)
"""Keypad key face."""

HEX_DIGITS = "0123456789ABCDEF"
"""Hex digits; a typed digit is stored as its value 0..15."""

SEPARATOR = 16
"""Code of the separator between red, green and blue in a typed code."""

CODE_MAX = 11
"""Longest typed code ("255 255 255")."""

CODE_STATES = {
    0: "RN_CP_IN_HINT",
    1: "RN_CP_IN_OK",
    2: "RN_CP_IN_SHORT",
    3: "RN_CP_IN_LONG",
    4: "RN_CP_IN_LETTER",
    5: "RN_CP_IN_RANGE",
    6: "RN_CP_IN_COUNT",
}
"""``rn_cp_in_st`` (what the typed code is) to its message key: 0 nothing typed, 1 a valid
colour, 2 a hex code with fewer than 6 digits, 3 more than 6, 4 a letter among the R G B
numbers, 5 a number above 255, 6 not three numbers (or an empty one)."""

COLOR = re.compile(r"\bcolor\s*=\s*(rgb|hsv)?\s*\{([^{}]*)\}", re.IGNORECASE)
"""The ``color = rgb { R G B }`` (or ``hsv { H S V }``) of one ``colors.txt`` entry."""

ENTRY = re.compile(r"([A-Za-z0-9_]+)\s*=\s*\{")
"""The start of a top-level ``KEY = {`` entry."""

COMMENT = re.compile(r"#[^\n]*")
"""A comment to the end of the line."""

DYNAMIC_TAG = re.compile(r"D[0-9]{2}")
"""A dynamic tag (civil war or released country): the game picks its colour when it is made,
so its ``colors.txt`` entry is not what the map shows; it is left out (unknown)."""

RGB = tuple[int, int, int]
"""Red, green and blue, ``0..255`` each."""


class NativeColours(NamedTuple):
    """The game's own map colours (``color``, not ``color_ui``), as whole RGB numbers."""

    tags: dict[str, RGB]
    """Country tag to colour (``common/countries/colors.txt``): tags of ``country_tags``
    without the dynamic ones."""

    cosmetics: dict[str, RGB]
    """Cosmetic tag to colour (``common/countries/cosmetic.txt``)."""


NO_NATIVES = NativeColours({}, {})
"""No game colours (unit tests without a game folder)."""


def _rgb(kind: str, numbers: list[float]) -> RGB | None:
    """Return a ``colors.txt`` colour as whole RGB numbers.

    Args:
        kind: ``rgb``, ``hsv`` or empty (rgb).
        numbers: The three numbers.

    Returns:
        ``(r, g, b)``, or None when the entry is not a usable colour.
    """
    if len(numbers) != 3:  # noqa: PLR2004 - three channels
        return None
    if kind.lower() == "hsv":
        h, s, v = numbers
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
        rgb = (round(r * CHANNEL_MAX), round(g * CHANNEL_MAX), round(b * CHANNEL_MAX))
    else:
        rgb = (round(numbers[0]), round(numbers[1]), round(numbers[2]))
    return rgb if all(0 <= c <= CHANNEL_MAX for c in rgb) else None


def parse_colours(text: str) -> dict[str, RGB]:
    """Return the ``color`` of every top-level entry of a ``colors.txt``-like file.

    Args:
        text: File text.

    Returns:
        Entry key to colour; the last entry of a key wins, as in the game.
    """
    text = COMMENT.sub("", text)
    out: dict[str, RGB] = {}
    pos = 0
    while (match := ENTRY.search(text, pos)) is not None:
        depth, end = 1, match.end()
        while depth and end < len(text):
            depth += {"{": 1, "}": -1}.get(text[end], 0)
            end += 1
        colour = COLOR.search(text[match.end() : end])
        if colour is not None:
            try:
                rgb = _rgb(colour[1] or "", [float(x) for x in colour[2].split()])
            except ValueError:
                rgb = None
            if rgb is not None:
                out[match[1]] = rgb
        pos = end
    return out


def read_natives(root: str) -> NativeColours:
    """Read the game's map colours.

    Args:
        root: Game installation folder.

    Returns:
        The colours of the tags of ``common/country_tags`` and of the cosmetic tags.
    """
    countries = Path(root) / "common" / "countries"

    def read(name: str) -> dict[str, RGB]:
        path = countries / name
        if not path.is_file():
            return {}
        return parse_colours(path.read_text(encoding="utf-8-sig", errors="replace"))

    known = set(read_tags(root))
    tags = {
        k: v
        for k, v in sorted(read("colors.txt").items())
        if k in known and not DYNAMIC_TAG.fullmatch(k)
    }
    cosmetics = {
        k: v
        for k, v in sorted(read("cosmetic.txt").items())
        if STEM.fullmatch(k) and k not in known
    }
    return NativeColours(tags, cosmetics)


def hex_code(rgb: RGB) -> str:
    """Return a colour as ``#RRGGBB``.

    Args:
        rgb: Red, green, blue.

    Returns:
        The hex code.
    """
    return "#" + "".join(f"{c:02X}" for c in rgb)


def swatch_sprite(n: int) -> str:
    """Return the sprite of preset ``n``.

    Args:
        n: Preset number, 1-based.

    Returns:
        Sprite name.
    """
    return f"GFX_rn_cp_sw_{n}"


def preview_frame(rgb: RGB) -> int:
    """Return the preview frame (1-based) the script computes for a colour.

    Args:
        rgb: Red, green, blue.

    Returns:
        ``(r // 32) * 64 + (g // 32) * 8 + b // 32 + 1``.
    """
    r, g, b = (c // LEVEL_STEP for c in rgb)
    return r * LEVELS * LEVELS + g * LEVELS + b + 1


def _level_value(level: int) -> int:
    """Return the colour drawn for a preview level (the middle of its range).

    Args:
        level: 0..7.

    Returns:
        Channel value.
    """
    return level * LEVEL_STEP + LEVEL_STEP // 2


def _key_texture(w: int, h: int) -> bytes:
    """Return a keypad key: a one-pixel border around a dark face.

    Args:
        w: Width.
        h: Height.

    Returns:
        TGA bytes.
    """

    def px(x: int, y: int) -> tuple[int, ...]:
        return KEY_EDGE if x in (0, w - 1) or y in (0, h - 1) else KEY_FILL

    return tga(w, h, px)


def textures() -> dict[str, bytes]:
    """Return the swatch, mark, key and preview textures.

    Returns:
        File name (in :data:`~modgen.features.textures.TEXTURE_DIR`) to TGA bytes.
    """
    out: dict[str, bytes] = {}
    w, h = SWATCH
    for n, preset in enumerate(PRESETS, start=1):
        fill = (*preset.rgb, 255)

        def px(x: int, y: int, fill: tuple[int, int, int, int] = fill) -> tuple[int, ...]:
            edge = x in (0, w - 1) or y in (0, h - 1)
            return BORDER if edge else fill

        out[f"rn_cp_sw_{n}.tga"] = tga(w, h, px)
    mw, mh = MARK

    def mark(x: int, y: int) -> tuple[int, ...]:
        ring = x < 2 or x >= mw - 2 or y < 2 or y >= mh - 2  # noqa: PLR2004 - two-pixel ring
        return MARK_COLOUR if ring else (0, 0, 0, 0)

    out["rn_cp_mark.tga"] = tga(mw, mh, mark)
    out["rn_cp_key.tga"] = _key_texture(*KEY)
    out["rn_cp_key_wide.tga"] = _key_texture(*KEY_WIDE)

    def strip(x: int, _y: int) -> tuple[int, ...]:
        frame = x // PREVIEW_FRAME
        r, g, b = frame // (LEVELS * LEVELS), frame // LEVELS % LEVELS, frame % LEVELS
        return (_level_value(r), _level_value(g), _level_value(b), 255)

    out["rn_cp_preview.tga"] = tga(PREVIEW_FRAMES * PREVIEW_FRAME, PREVIEW_FRAME, strip)
    return out


def gfx() -> str:
    """Return the sprite file.

    Returns:
        Contents of :data:`GFX_FILE`.
    """
    sprites = [(swatch_sprite(n), f"rn_cp_sw_{n}.tga", 1) for n in range(1, len(PRESETS) + 1)]
    sprites += [
        (MARK_SPRITE, "rn_cp_mark.tga", 1),
        (KEY_SPRITE, "rn_cp_key.tga", 1),
        (KEY_WIDE_SPRITE, "rn_cp_key_wide.tga", 1),
        (PREVIEW_SPRITE, "rn_cp_preview.tga", 512),
    ]
    body = "".join(
        f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{TEXTURE_DIR}/{file}"\n'
        f"\t\tnoOfFrames = {frames}\n\t}}\n"
        for name, file, frames in sprites
    )
    return (
        GEN_HEADER
        + "# Colour picker sprites (tools/modgen/features/colours.py): preset swatches, the\n"
        "# selection mark, the keypad keys and the preview strip\n"
        "# (frame = (r/32)*64 + (g/32)*8 + b/32 + 1).\n"
        "spriteTypes = {\n" + body + "}\n"
    )


def _rgb_lines(rgb: RGB, prefix: str = "rn_cp_", *, temp: bool = False) -> str:
    """Return the three statements that store a colour.

    Args:
        rgb: Red, green, blue.
        prefix: Variable prefix (``rn_cp_`` gives ``rn_cp_r``, ``rn_cp_g``, ``rn_cp_b``).
        temp: Temp variables instead of variables of the scope.

    Returns:
        Script text.
    """
    effect = "set_temp_variable" if temp else "set_variable"
    return " ".join(f"{effect} = {{ {prefix}{c} = {v} }}" for c, v in zip("rgb", rgb, strict=True))


def _cosmetic_effects(catalog: FlagCatalog) -> list[str]:
    """Return the cosmetic tag snapshot effects of the colour layer.

    Args:
        catalog: The flag catalog (its known cosmetic tags).

    Returns:
        Script lines.
    """
    out = [
        (
            "# Country scope. Writes the snapshot of the country's cosmetic tag (capie_cc_cos\n"
            "# and capie_cc_cos_len, CONTRACT 19.2 and 17.3) when it is a known one; otherwise\n"
            '# removes the snapshot: script cannot tell "no cosmetic tag" from an unknown one.\n'
            "rn_cp_cos_write = {\n"
        )
    ]
    for i, cosmetic in enumerate(catalog.cosmetics):
        word = "if" if i == 0 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ has_cosmetic_tag = {cosmetic} }} "
            f"{write_leaf(cosmetic, 'capie_cc_cos', 'capie_cc_cos_len')} }}\n"
        )
    out.append("\telse = { clear_array = capie_cc_cos clear_variable = capie_cc_cos_len }\n}\n\n")
    out.append(
        "# Country scope. Output temps rn_cp_cos_known (1 = the country has a known cosmetic tag)\n"
        "# and rn_cp_cos_same (1 = it is the one in the snapshot capie_cc_cos).\n"
        "rn_cp_cos_match = {\n"
        "\tset_temp_variable = { rn_cp_cos_known = 0 }\n"
        "\tset_temp_variable = { rn_cp_cos_same = 0 }\n"
    )
    for i, cosmetic in enumerate(catalog.cosmetics):
        word = "if" if i == 0 else "else_if"
        same = " ".join(
            [check_variable(f"capie_cc_cos_len = {len(cosmetic)}")]
            + [check_variable(f"capie_cc_cos^{j} = {v}") for j, v in enumerate(pack(cosmetic))]
        )
        out.append(
            f"\t{word} = {{ limit = {{ has_cosmetic_tag = {cosmetic} }} "
            f"set_temp_variable = {{ rn_cp_cos_known = 1 }} "
            f"if = {{ limit = {{ {same} }} set_temp_variable = {{ rn_cp_cos_same = 1 }} }} }}\n"
        )
    out.append("}\n")
    return out


def _native_effect(natives: NativeColours) -> list[str]:
    """Return ``rn_cp_native``, the game's colour of the scope country.

    Args:
        natives: The game's colours.

    Returns:
        Script lines.
    """
    out = [
        (
            "# Country scope. The game's map colour of this country, read from the game's files\n"
            f"# ({len(natives.cosmetics)} cosmetic tags of common/countries/cosmetic.txt first,\n"
            f"# then {len(natives.tags)} tags of common/countries/colors.txt). Output temps\n"
            "# rn_cp_nr, rn_cp_ng, rn_cp_nb and rn_cp_nk (1 = known; 0 for a dynamic tag or\n"
            "# another mod's tag). The colours are the base game's: a mod that recolours a\n"
            "# country is not seen.\n"
            "rn_cp_native = {\n\tset_temp_variable = { rn_cp_nk = 0 }\n"
        )
    ]
    branches = [(f"has_cosmetic_tag = {k}", v) for k, v in natives.cosmetics.items()]
    branches += [(f"tag = {k}", v) for k, v in natives.tags.items()]
    for i, (limit, rgb) in enumerate(branches):
        word = "if" if i == 0 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ {limit} }} {_rgb_lines(rgb, 'rn_cp_n', temp=True)} "
            "set_temp_variable = { rn_cp_nk = 1 } }\n"
        )
    out.append("}\n\n")
    return out


def effects(catalog: FlagCatalog, natives: NativeColours = NO_NATIVES) -> str:
    """Return the generated colour effects.

    Args:
        catalog: The flag catalog (cosmetic tags of the snapshot).
        natives: The game's colours.

    Returns:
        Contents of :data:`EFFECTS_FILE`.
    """
    out = [
        GEN_HEADER,
        "# Colour picker presets (tools/modgen/features/colours.py).\n\n",
        "# Constant: the number of presets.\n",
        f"rn_cp_presets = {{\n\tset_temp_variable = {{ rn_cp_n = {len(PRESETS)} }}\n}}\n\n",
        "# ROOT scope. Input temp rn_cp_pick (1..presets): puts that preset into rn_cp_r/g/b.\n",
        "rn_cp_load_preset = {\n",
    ]
    for n, preset in enumerate(PRESETS, start=1):
        word = "if" if n == 1 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ check_variable = {{ temp_var:rn_cp_pick = {n} }} }} "
            f"{_rgb_lines(preset.rgb)} }}\n"
        )
    out.append("}\n\n")
    out.append(
        "# ROOT scope. rn_cp_sel = the preset whose colour is rn_cp_r/g/b, 0 when none is.\n"
        "rn_cp_match_preset = {\n\tset_variable = { rn_cp_sel = 0 }\n"
    )
    for n, preset in enumerate(PRESETS, start=1):
        word = "if" if n == 1 else "else_if"
        same = " ".join(
            check_variable(f"rn_cp_{c} = {v}") for c, v in zip("rgb", preset.rgb, strict=True)
        )
        out.append(f"\t{word} = {{ limit = {{ {same} }} set_variable = {{ rn_cp_sel = {n} }} }}\n")
    out.append("}\n\n")
    out += _native_effect(natives)
    out += _cosmetic_effects(catalog)
    return "".join(out)


def _code_loc() -> str:
    """Return the hex digits of the picked colour, the typed code and its message.

    Returns:
        ``defined_text`` blocks, called as ``[ROOT.<name>]``.
    """
    out = [
        defined_text(
            f"RN_CP_HX{i}",
            [(check_variable(f"rn_cp_x{i} = {v}"), f"RN_CP_HD_{v}") for v in range(1, 16)],
            "RN_CP_HD_0",
        )
        for i in range(1, 7)
    ]
    out.append(
        defined_text(
            "RN_CP_IN_PRE",
            [
                (check_variable("rn_cp_in^num = 0"), "RN_CP_IN_EMPTY"),
                (f"is_in_array = {{ array = rn_cp_in value = {SEPARATOR} }}", "RN_IPP_EMPTY"),
            ],
            "RN_CP_IN_HASH",
        )
    )
    for i in range(CODE_MAX):
        typed = check_variable(f"rn_cp_in^num > {i}")
        branches = [
            (f"{typed} {check_variable(f'rn_cp_in^{i} = {v}')}", f"RN_CP_HD_{v}")
            for v in range(len(HEX_DIGITS))
        ]
        branches.append(
            (f"{typed} {check_variable(f'rn_cp_in^{i} = {SEPARATOR}')}", "RN_CP_IN_SEP")
        )
        out.append(defined_text(f"RN_CP_IN_{i}", branches, "RN_IPP_EMPTY"))
    out.append(
        defined_text(
            "RN_CP_IN_MSG",
            [(check_variable(f"rn_cp_in_st = {s}"), key) for s, key in CODE_STATES.items() if s],
            CODE_STATES[0],
        )
    )
    return "".join(out)


def scripted_loc() -> str:
    """Return the colour cooldown's days left and the colour code texts.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    return (
        GEN_HEADER
        + "# Days left of the colour cooldown (scope: the country whose colour changes).\n"
        + days_left_loc("RN_IP_CD_LEFT_COLOUR", "rn_ip_cd_colour_until")
        + "\n# The picked colour as #RRGGBB (rn_cp_x1..6 on ROOT), the typed colour code\n"
        "# (array rn_cp_in on ROOT: 0..15 a hex digit, 16 the separator) and its message\n"
        "# (rn_cp_in_st). Called as [ROOT.<name>].\n" + _code_loc()
    )


def localisation(lang: str) -> str:
    """Return the preset names and the code characters of one language.

    Polish has its own preset names; every other language gets the English ones. The
    digits are the same in every language.

    Args:
        lang: Game language.

    Returns:
        The ``.yml`` text without the BOM.
    """
    pl = lang == POLISH
    lines = [f"l_{lang}:\n"]
    for n, preset in enumerate(PRESETS, start=1):
        name = preset.polish if pl else preset.english
        r, g, b = preset.rgb
        lines.append(f' RN_CP_SW_{n}:0 "{name} ({hex_code(preset.rgb)}; R {r}, G {g}, B {b})"\n')
    lines += [f' RN_CP_HD_{v}:0 "{d}"\n' for v, d in enumerate(HEX_DIGITS)]
    lines += [' RN_CP_IN_SEP:0 " "\n', ' RN_CP_IN_HASH:0 "#"\n']
    return "".join(lines)


def write_files(
    catalog: FlagCatalog, natives: NativeColours = NO_NATIVES
) -> list[tuple[str, str, bool]]:
    """Return every generated colour file.

    Args:
        catalog: The flag catalog (cosmetic tags of the snapshot).
        natives: The game's colours.

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    files = [
        (GFX_FILE, gfx(), False),
        (EFFECTS_FILE, effects(catalog, natives), False),
        (SCRIPTED_LOC_FILE, scripted_loc(), False),
    ]
    files += [
        (f"localisation/{lang}/rn_colour_catalog_l_{lang}.yml", localisation(lang), True)
        for lang in LANGS
    ]
    return files
