"""Unit tests of the Characters list mini portraits (``modgen.features.char_portraits``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from modgen.features import char_portraits, portraits
from modgen.features.portraits import Character, Entry, PortraitCatalog

if TYPE_CHECKING:
    from pathlib import Path


def _char(token: str, **portraits: str) -> Character:
    """Return a character with ``kind_size=sprite`` portraits.

    Args:
        token: Character token.
        **portraits: ``civilian_large="GFX_x"`` and the like.

    Returns:
        The character.
    """
    pics = {tuple(k.split("_")): v for k, v in portraits.items()}
    return Character(token, token[:3], token, pics, frozenset({"country_leader"}))


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
        [_char("ENG_a", civilian_large="GFX_base_large", civilian_small="GFX_idea_a")],
        _catalog(),
        TEXTURES,
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
        [_char("ENG_b", civilian_small="GFX_idea_b"), _char("ENG_c", army_small="GFX_idea_b")],
        _catalog(),
        TEXTURES,
    )
    assert data.values == {"ENG_b": SMALL + 1, "ENG_c": SMALL + 1}
    assert len(data.textures) == 2  # unknown + one small


def test_effect_caches_and_returns_the_value() -> None:
    """The chain runs only for a new table; the value always comes back in the temp variable."""
    data = char_portraits.build(
        [_char("ENG_a", civilian_large="GFX_base_large")], _catalog(), TEXTURES
    )
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
        [
            _char("ENG_a", civilian_large="GFX_base_large"),
            _char("ENG_b", civilian_small="GFX_idea_b"),
        ],
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


def test_dlc_folder_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The generator stops on a missing or an unlisted DLC folder and accepts the listed set."""
    lock = tmp_path / "portrait_dlc.txt"
    lock.write_text("# comment\ndlc/dlc001_a\nintegrated_dlc/dlc018_b\n", encoding="utf-8")
    monkeypatch.setattr(portraits, "EXPECTED_DLC", lock)
    game = tmp_path / "game"
    (game / "dlc" / "dlc001_a").mkdir(parents=True)
    (game / "integrated_dlc" / "dlc018_b").mkdir(parents=True)
    portraits.check_dlc_folders(game)
    (game / "dlc" / "dlc099_new").mkdir()
    with pytest.raises(ValueError, match="dlc099_new"):
        portraits.check_dlc_folders(game)
    (game / "dlc" / "dlc099_new").rmdir()
    (game / "dlc" / "dlc001_a").rmdir()
    with pytest.raises(ValueError, match="dlc001_a"):
        portraits.check_dlc_folders(game)


def test_instance_condition_copies_only_dlc_triggers() -> None:
    """An instance's ``allowed`` becomes script only when it uses DLC triggers."""
    assert portraits.instance_condition(None) == "always = yes"
    assert portraits.instance_condition([("has_dlc", "Thunder at Our Gates")]) == (
        'has_dlc = "Thunder at Our Gates"'
    )
    assert portraits.instance_condition([("NOT", [("has_dlc", "Gotterdammerung")])]) == (
        "NOT = { has_dlc = Gotterdammerung }"
    )
    assert portraits.instance_condition([("has_completed_focus", "X")]) is None


def test_instance_character_gets_one_fixed_value() -> None:
    """A DLC character uses its no-DLC instance picture; a DLC-only one its DLC picture."""
    both = Character(
        "ENG_i",
        "ENG",
        "ENG_i",
        {},
        frozenset(),
        (
            ('has_dlc = "X"', {("army", "large"): "GFX_dlc_large"}),
            ('NOT = { has_dlc = "X" }', {("army", "large"): "GFX_base_large"}),
        ),
    )
    only = Character(
        "ENG_j",
        "ENG",
        "ENG_j",
        {},
        frozenset(),
        (('has_dlc = "X"', {("army", "large"): "GFX_dlc_large"}),),
    )
    data = char_portraits.build([both, only], _catalog(), TEXTURES)
    assert data.values == {"ENG_i": 1, "ENG_j": 2}
    assert "has_dlc" not in char_portraits.effects(data)


def test_effect_compares_only_roots_country() -> None:
    """Each country's tokens sit in a ROOT original_tag group (no foreign-token lookups)."""
    data = char_portraits.build(
        [
            _char("ENG_a", civilian_large="GFX_base_large"),
            _char("GER_b", civilian_small="GFX_idea_b"),
        ],
        _catalog(),
        TEXTURES,
    )
    text = char_portraits.effects(data)
    eng, ger = text.index("original_tag = ENG"), text.index("original_tag = GER")
    assert eng < text.index("is_character = ENG_a") < ger < text.index("is_character = GER_b")
