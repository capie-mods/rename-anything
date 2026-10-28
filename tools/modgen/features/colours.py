"""Colour presets of the country colour picker and the script that uses them.

The player picks a map colour for a country in the colour picker
(``colour_picker``). The picker offers :data:`PRESETS`, a hand palette of
distinct map colours, and three RGB steppers. A colour is three integers
``0..255``, as in the game's ``colors.txt``; CAPIE applies the game's country
colour defines to it, as the game does with ``colors.txt`` (CONTRACT section 19).

Generated files (relative to ``mod/``):

* ``interface/rn_colour_catalog.gfx``: one swatch sprite per preset
  (``GFX_rn_cp_sw_<n>``), the selection mark and the preview strip
  ``GFX_rn_cp_preview`` (512 frames, 3 bits per channel).
* ``gfx/interface/rename_anything/rn_cp_*.tga``: the textures of those sprites.
* ``common/scripted_effects/rn_colour_catalog.txt``: ``rn_cp_presets`` (the preset
  count), ``rn_cp_load_preset`` (a preset into ``rn_cp_r/g/b``),
  ``rn_cp_match_preset`` (the preset of the picked colour, 0 = none), and the
  cosmetic tag snapshot of the colour layer, ``rn_cp_cos_write`` and
  ``rn_cp_cos_match`` (``capie_cc_cos``, CONTRACT 19.2 / 17.3), built from the
  flag catalog's cosmetic tags.
* ``common/scripted_localisation/rn_colour_catalog.txt``: the colour cooldown's
  days left.
* ``localisation/<lang>/rn_colour_catalog_l_<lang>.yml``: the preset names
  (English and Polish, the other languages English).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from modgen.common import GEN_HEADER, LANGS, POLISH
from modgen.features.catalog_common import days_left_loc, pack, write_leaf
from modgen.features.textures import TEXTURE_DIR, tga
from modgen.script import check_variable

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
    Preset("Crimson", "Karmazynowy", (200, 30, 45)),
    Preset("Scarlet", "Szkarłatny", (230, 70, 30)),
    Preset("Orange", "Pomarańczowy", (240, 135, 20)),
    Preset("Amber", "Bursztynowy", (245, 185, 40)),
    Preset("Yellow", "Żółty", (240, 225, 50)),
    Preset("Olive", "Oliwkowy", (140, 150, 40)),
    Preset("Lime", "Limonkowy", (150, 210, 60)),
    Preset("Green", "Zielony", (40, 160, 60)),
    Preset("Forest green", "Ciemnozielony", (25, 100, 45)),
    Preset("Teal", "Morski", (20, 150, 140)),
    Preset("Turquoise", "Turkusowy", (60, 200, 200)),
    Preset("Sky blue", "Błękitny", (90, 170, 235)),
    Preset("Blue", "Niebieski", (30, 90, 200)),
    Preset("Navy", "Granatowy", (25, 40, 120)),
    Preset("Indigo", "Indygo", (75, 50, 160)),
    Preset("Violet", "Fioletowy", (140, 70, 200)),
    Preset("Purple", "Purpurowy", (110, 30, 110)),
    Preset("Magenta", "Amarantowy", (210, 50, 160)),
    Preset("Pink", "Różowy", (240, 140, 180)),
    Preset("Brown", "Brązowy", (120, 70, 35)),
    Preset("Sand", "Piaskowy", (200, 160, 110)),
    Preset("Grey", "Szary", (130, 130, 130)),
    Preset("White", "Biały", (235, 235, 230)),
    Preset("Black", "Czarny", (35, 35, 35)),
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

SWATCH = (24, 20)
"""Size of a swatch texture."""

MARK = (28, 24)
"""Size of the selection mark (two pixels around a swatch)."""

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

BORDER = (20, 20, 20, 255)
"""Swatch border colour."""

MARK_COLOUR = (255, 214, 0, 255)
"""Selection mark colour (vanilla highlight yellow)."""


def swatch_sprite(n: int) -> str:
    """Return the sprite of preset ``n``.

    Args:
        n: Preset number, 1-based.

    Returns:
        Sprite name.
    """
    return f"GFX_rn_cp_sw_{n}"


def preview_frame(rgb: tuple[int, int, int]) -> int:
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


def textures() -> dict[str, bytes]:
    """Return the swatch, mark and preview textures.

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
    sprites += [(MARK_SPRITE, "rn_cp_mark.tga", 1), (PREVIEW_SPRITE, "rn_cp_preview.tga", 512)]
    body = "".join(
        f'\tspriteType = {{\n\t\tname = "{name}"\n\t\ttexturefile = "{TEXTURE_DIR}/{file}"\n'
        f"\t\tnoOfFrames = {frames}\n\t}}\n"
        for name, file, frames in sprites
    )
    return (
        GEN_HEADER
        + "# Colour picker sprites (tools/modgen/features/colours.py): preset swatches, the\n"
        "# selection mark and the preview strip (frame = (r/32)*64 + (g/32)*8 + b/32 + 1).\n"
        "spriteTypes = {\n" + body + "}\n"
    )


def _rgb_lines(rgb: tuple[int, int, int]) -> str:
    """Return the three ``set_variable`` statements of a colour on ROOT.

    Args:
        rgb: Red, green, blue.

    Returns:
        Script text.
    """
    return " ".join(
        f"set_variable = {{ rn_cp_{c} = {v} }}" for c, v in zip("rgb", rgb, strict=True)
    )


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


def effects(catalog: FlagCatalog) -> str:
    """Return the generated colour effects.

    Args:
        catalog: The flag catalog (cosmetic tags of the snapshot).

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
    out += _cosmetic_effects(catalog)
    return "".join(out)


def scripted_loc() -> str:
    """Return the colour cooldown's days left.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    return (
        GEN_HEADER
        + "# Days left of the colour cooldown (scope: the country whose colour changes).\n"
        + days_left_loc("RN_IP_CD_LEFT_COLOUR", "rn_ip_cd_colour_until")
    )


def localisation(lang: str) -> str:
    """Return the preset names of one language (Polish, or English for every other one).

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
        lines.append(f' RN_CP_SW_{n}:0 "{name} (R {r}, G {g}, B {b})"\n')
    return "".join(lines)


def write_files(catalog: FlagCatalog) -> list[tuple[str, str, bool]]:
    """Return every generated colour file.

    Args:
        catalog: The flag catalog (cosmetic tags of the snapshot).

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    files = [
        (GFX_FILE, gfx(), False),
        (EFFECTS_FILE, effects(catalog), False),
        (SCRIPTED_LOC_FILE, scripted_loc(), False),
    ]
    files += [
        (f"localisation/{lang}/rn_colour_catalog_l_{lang}.yml", localisation(lang), True)
        for lang in LANGS
    ]
    return files
