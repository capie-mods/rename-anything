"""Unit tests of the Characters list mini portraits (``modgen.features.char_portraits``)."""

from __future__ import annotations

from modgen.features import char_portraits
from modgen.features.portraits import Character, Entry, PortraitCatalog


def _char(token: str, **portraits: str) -> Character:
    """Return a character with ``kind_size=sprite`` portraits.

    Args:
        token: Character token.
        **portraits: ``civilian_large="GFX_x"`` and the like.

    Returns:
        The character.
    """
    pics = {tuple(k.split("_")): v for k, v in portraits.items()}
    return Character(token, "ENG", token, pics, frozenset({"country_leader"}))


def _catalog() -> PortraitCatalog:
    """Return a catalog with one base-game and one DLC portrait.

    Returns:
        The catalog (entry 1 base game, entry 2 DLC pack 1).
    """
    entries = (
        Entry("GFX_base_large", "", "ENG", "x", True, False, 0),
        Entry("GFX_dlc_large", "", "ENG", "y", True, False, 1),
    )
    textures = {"GFX_base_large": "gfx/leaders/base.dds", "GFX_dlc_large": "gfx/leaders/dlc.dds"}
    return PortraitCatalog(entries, textures, ("ENG",), {}, packs=("", "dlc"))


TEXTURES = {"GFX_idea_a": "gfx/interface/ideas/a.dds", "GFX_idea_b": "gfx/interface/ideas/b.dds"}
"""Small sprites the base game defines."""

SMALL = char_portraits.SMALL_OFFSET
"""First small-portrait value."""


def test_large_catalog_portrait_wins() -> None:
    """A base-game large portrait from the catalog is used before any small one."""
    data = char_portraits.build(
        [_char("ENG_a", civilian_large="GFX_base_large", civilian_small="GFX_idea_a")], _catalog(), TEXTURES
    )
    assert data.values == {"ENG_a": 1}
    assert data.textures == {0: char_portraits.UNKNOWN_TEXTURE, 1: "gfx/leaders/base.dds"}


def test_dlc_portrait_falls_back_to_small_or_unknown() -> None:
    """A DLC-only large portrait is skipped; the small one is used, else the character is unknown."""
    data = char_portraits.build(
        [
            _char("ENG_d", civilian_large="GFX_dlc_large", civilian_small="GFX_idea_a"),
            _char("ENG_e", civilian_large="GFX_dlc_large"),
        ],
        _catalog(),
        TEXTURES,
    )
    assert data.values == {"ENG_d": SMALL + 1}
    assert data.textures[SMALL + 1] == "gfx/interface/ideas/a.dds"
    assert "gfx/leaders/dlc.dds" not in data.textures.values()


def test_small_textures_are_shared() -> None:
    """Two characters with the same small picture share one sprite value."""
    data = char_portraits.build(
        [_char("ENG_b", civilian_small="GFX_idea_b"), _char("ENG_c", army_small="GFX_idea_b")], _catalog(), TEXTURES
    )
    assert data.values == {"ENG_b": SMALL + 1, "ENG_c": SMALL + 1}
    assert len(data.textures) == 2  # unknown + one small


def test_effect_caches_and_returns_the_value() -> None:
    """The chain runs only for a new table; the value always comes back in the temp variable."""
    data = char_portraits.build([_char("ENG_a", civilian_large="GFX_base_large")], _catalog(), TEXTURES)
    text = char_portraits.effects(data)
    fp = char_portraits.fingerprint(data)
    assert f"NOT = {{ check_variable = {{ rn_cp_c = {fp} }} }}" in text
    assert "set_variable = { rn_cp_v = 0 }" in text
    assert "if = { limit = { is_character = ENG_a } set_variable = { rn_cp_v = 1 } }" in text
    assert text.rstrip().endswith("set_temp_variable = { rn_cp_t = rn_cp_v }\n}")
    assert 1 <= fp <= 99991


def test_gfx_defines_every_value_including_unknown() -> None:
    """Every value the effect can return has a sprite, value 0 included."""
    data = char_portraits.build(
        [_char("ENG_a", civilian_large="GFX_base_large"), _char("ENG_b", civilian_small="GFX_idea_b")],
        _catalog(),
        TEXTURES,
    )
    gfx = char_portraits.gfx(data)
    for value in (0, 1, SMALL + 1):
        assert f'name = "GFX_rnchp_{value}"' in gfx


def test_sprite_regex_keeps_paths_with_spaces() -> None:
    """A quoted texture path with spaces is read whole (``gfx/leaders/South America/...`` was cut)."""
    from modgen.features.portraits import SPRITE

    text = 'spriteType = { name = "GFX_a" texturefile = "gfx/leaders/South America/a b.dds" }\n'
    text += "spriteType = { name = GFX_b texturefile = gfx/leaders/x.dds }\n"
    found = [(name, quoted or bare) for name, quoted, bare in SPRITE.findall(text)]
    assert found == [("GFX_a", "gfx/leaders/South America/a b.dds"), ("GFX_b", "gfx/leaders/x.dds")]
