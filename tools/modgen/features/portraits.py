"""Portrait catalog: the game's character portraits a player can give a country leader.

ADR-0036 with its amendment (U1, U2) and portrait-layer design.txt / review.txt.
The generator reads ``common/characters`` and the sprite definitions of
``interface/*.gfx`` at build time and numbers every usable large portrait
(catalog index ``1..N``, sorted by sprite name):

* leaders: the civilian large portrait of a character with ``country_leader``;
* generals: the army large portrait of a ``field_marshal`` or ``corps_commander``,
  the navy large portrait of a ``navy_leader`` (review 3.8: admirals as generals).

Only sprites (``GFX_...``) that exist in the game's sprite definitions and fit the
CAPIE file-name alphabet are used; the two portraits given as ``.dds`` paths and
the names with other characters are left out (review 3.7). Each entry also keeps
the small portrait the layer writes with it (review 3.4): the small sprite of the
same block, or the large name plus ``_small`` when the game defines that sprite.

A portrait belongs to the country of its character (the tag that starts the
character token, otherwise the file name). Countries are listed by the first
letter of their English name, as in the flag picker.

Generated files (relative to ``mod/``):

* ``interface/rn_portrait_catalog.gfx``: ``GFX_rnp_<n>`` pointing at the game's
  texture of the large portrait (lazy loading, nothing copied);
* ``common/scripted_effects/rn_portrait_catalog.txt``: catalog constants, the pool
  group of a country, the pools of a group (leaders or generals), the countries of
  a letter (for the current kind), and the facts of one entry (its group and kinds)
  that Apply checks against the game rule;
* ``common/scripted_localisation/rn_portrait_catalog.txt``: the selected
  portrait's name and the portrait cooldown's days left;
* ``localisation/<lang>/rn_portrait_catalog_l_<lang>.yml``: labels (the
  character's name through the game's key, or the name as the game writes it).

The CAPIE carrier (section 18 of the contract, character variables ``capie_pt_*``)
is written only after the contract is ready (``contract-ready.txt``):
:data:`CARRIER_READY` switches the writer on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from modgen.common import GEN_HEADER, LANGS
from modgen.features.catalog_common import (
    STEM,
    TAG_LEN,
    days_left_loc,
    dispatch,
    fingerprint,
    letters_of,
    read_english,
    read_tags,
    selected_name_loc,
    write_leaf,
)
from modgen.script import check_variable, defined_text
from rncommon.game_data import HAS_DLC_NAMES

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

CARRIER_READY = True
"""The CAPIE portrait contract exists (contract-ready.txt, CONTRACT section 18)."""

TOKEN = re.compile(r'"[^"]*"|[{}=]|[^\s{}="]+')
"""Tokens of a Paradox script file (quoted string, brace, equals, word)."""

SPRITE = re.compile(
    r'spriteType\s*=\s*\{[^{}]*?name\s*=\s*"?([^"\s}]+)"?[^{}]*?texturefile\s*=\s*(?:"([^"]+)"|([^\s}"]+))',
    re.IGNORECASE | re.DOTALL,
)
"""A ``spriteType`` with its name and texture file (name before texturefile, as in vanilla).

A quoted texture path may contain spaces (``gfx/leaders/South America/...``): group 2 is the
quoted path, group 3 an unquoted one.
"""

DLC_NAME = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.MULTILINE)
"""The ``name`` of a ``.dlc`` descriptor, the value ``has_dlc`` takes."""

NO_CHECKSUM = re.compile(r"^\s*affects_checksum\s*=\s*no\s*$", re.MULTILINE)
"""A cosmetic DLC: the game rejects its name in ``has_dlc`` (e.g. "Anniversary Pack")."""


def checkable_dlc(descriptor: Path | None) -> str | None:
    """Return the ``has_dlc`` name of a DLC descriptor, or None when script cannot test it.

    ``has_dlc`` knows only the fixed names of :data:`~rncommon.game_data.HAS_DLC_NAMES`; any other
    DLC (a cosmetic pack, ``affects_checksum = no``) cannot gate a portrait, so its pictures are
    left out of every catalog: without the DLC their textures are missing.

    Args:
        descriptor: The folder's ``.dlc`` file, if any.

    Returns:
        The DLC name, or None.
    """
    if descriptor is None:
        return None
    text = descriptor.read_text(encoding="utf-8", errors="replace")
    match = DLC_NAME.search(text)
    if not match or NO_CHECKSUM.search(text) or match[1] not in HAS_DLC_NAMES:
        return None
    return match[1]


LEADER = 1
"""``rn_pp_kind`` of the leaders' portraits."""

GENERAL = 2
"""``rn_pp_kind`` of the generals' and admirals' portraits."""

GENERAL_ROLES = {"field_marshal": "army", "corps_commander": "army", "navy_leader": "navy"}
"""Unit leader roles and the portrait type the game shows for them."""

CATALOG_GFX = "interface/rn_portrait_catalog.gfx"
"""Sprite file of the catalog, relative to ``mod/``."""

CATALOG_EFFECTS = "common/scripted_effects/rn_portrait_catalog.txt"
"""Generated effects of the catalog, relative to ``mod/``."""

CATALOG_SCRIPTED_LOC = "common/scripted_localisation/rn_portrait_catalog.txt"
"""Generated scripted localisation, relative to ``mod/``."""

ON_ACTIONS_FILE = "common/on_actions/rn_portrait_on_actions.txt"
"""Daily portrait commit, relative to ``mod/``."""

UNNAMED = "$RN_PP_UNNAMED$"
"""Label of a character whose name the game does not define (never a sprite name)."""


@dataclass(frozen=True)
class Character:
    """One character of ``common/characters`` with what the catalog needs."""

    token: str
    """Character token."""

    tag: str
    """Country tag of the character."""

    name: str
    """``name`` value: a localisation key or a literal name."""

    portraits: dict[tuple[str, str], str]
    """``(type, size)`` to sprite name or path, e.g. ``("civilian", "large")``."""

    roles: frozenset[str]
    """Role blocks of the character (``country_leader``, ``field_marshal``, ...)."""

    instances: tuple[tuple[str, dict[tuple[str, str], str]], ...] = ()
    """``instance`` blocks with portraits: ``(allowed trigger as script, portraits)``.

    Since 1.19 a DLC character has no top-level ``portraits``; each ``instance`` has its own,
    chosen by its ``allowed`` (``has_dlc``, ``NOT = { has_dlc }``, ``has_aat``). Instances whose
    ``allowed`` uses anything else are left out (:func:`instance_condition`).
    """


@dataclass(frozen=True)
class Entry:
    """One catalog portrait."""

    large: str
    """Large sprite name (what the layer shows)."""

    small: str
    """Small sprite name written with it, or an empty string."""

    tag: str
    """Country of the character."""

    label: str
    """Localisation text (a game key reference or the literal name)."""

    leader: bool
    """A country leader's portrait."""

    general: bool
    """A general's or admiral's portrait."""

    pack: int = 0
    """Portrait pack: 0 the base game, ``k`` the DLC ``PortraitCatalog.packs[k]``."""


@dataclass(frozen=True)
class PortraitCatalog:
    """Every portrait the picker offers."""

    entries: tuple[Entry, ...]
    """Catalog entries; index ``n`` is ``entries[n - 1]``."""

    textures: dict[str, str]
    """Large sprite name to its texture file."""

    tags: tuple[str, ...]
    """Group tags (group ``g`` is ``tags[g - 1]``)."""

    letters: dict[tuple[int, int], tuple[tuple[str, ...], ...]]
    """``(kind, pack)`` to the tags of each letter that have portraits of that kind and pack."""

    packs: tuple[str, ...] = ("",)
    """Portrait packs: ``""`` (the base game) first, then the DLC names (``has_dlc``) sorted."""

    report: dict[str, int] = field(default_factory=dict)
    """Counts for the generator's summary line."""

    def pool(self, tag: str, kind: int, pack: int | None = None) -> tuple[int, ...]:
        """Return the indices of a country's portraits of one kind (and pack).

        Args:
            tag: Country tag.
            kind: :data:`LEADER` or :data:`GENERAL`.
            pack: Pack index, or None for every pack.

        Returns:
            Catalog indices in catalog order.
        """
        return tuple(
            n
            for n, e in enumerate(self.entries, start=1)
            if e.tag == tag
            and (e.leader if kind == LEADER else e.general)
            and (pack is None or e.pack == pack)
        )


def tokens(text: str) -> Iterator[str]:
    """Yield the tokens of a script file without comments.

    Args:
        text: File text.

    Yields:
        Tokens, quoted strings with their quotes.
    """
    for line in text.splitlines():
        for token in TOKEN.findall(line.split("#", 1)[0]):
            yield str(token)


def parse_block(items: list[str], i: int) -> tuple[list[tuple[str, object]], int]:
    """Parse the body of a block that starts after ``{`` at ``items[i]``.

    Args:
        items: Tokens.
        i: Index after the opening brace.

    Returns:
        ``(key, value)`` pairs (value: string or nested pairs) and the index after ``}``.
    """
    out: list[tuple[str, object]] = []
    while i < len(items) and items[i] != "}":
        key = items[i].strip('"')
        if i + 1 < len(items) and items[i + 1] == "=":
            if items[i + 2] == "{":
                value, i = parse_block(items, i + 3)
                out.append((key, value))
            else:
                out.append((key, items[i + 2].strip('"')))
                i += 3
        else:
            out.append((key, ""))
            i += 1
    return out, i + 1


INSTANCE_TRIGGERS = frozenset({"has_dlc", "has_aat", "NOT", "AND", "OR"})
"""Triggers an instance's ``allowed`` may use for the generator to copy it into script."""

SCRIPT_WORD = re.compile(r"[A-Za-z0-9_.]+")
"""A script value that needs no quotes."""


def instance_condition(allowed: object) -> str | None:
    """Return an instance's ``allowed`` block as a script trigger, or None when it is not copied.

    Args:
        allowed: The parsed ``allowed`` body (pairs), or None when the instance has none.

    Returns:
        ``"always = yes"`` without ``allowed``; the trigger text when every key is in
        :data:`INSTANCE_TRIGGERS`; None otherwise.
    """
    if allowed is None:
        return "always = yes"

    def render(pairs: object) -> str | None:
        if not isinstance(pairs, list) or not pairs:
            return None
        parts = []
        for key, value in pairs:
            if key not in INSTANCE_TRIGGERS:
                return None
            if isinstance(value, list):
                inner = render(value)
                if inner is None:
                    return None
                parts.append(f"{key} = {{ {inner} }}")
            else:
                text = str(value)
                parts.append(
                    f"{key} = {text}" if SCRIPT_WORD.fullmatch(text) else f'{key} = "{text}"'
                )
        return " ".join(parts)

    return render(allowed)


def _portraits_of(block: list[tuple[str, object]]) -> dict[tuple[str, str], str]:
    """Return the ``portraits`` of a character or instance block.

    Args:
        block: Parsed pairs of the block.

    Returns:
        ``(type, size)`` to sprite name or path.
    """
    out: dict[tuple[str, str], str] = {}
    for k, v in block:
        if k == "portraits" and isinstance(v, list):
            for kind, sizes in v:
                if isinstance(sizes, list):
                    out.update({(kind, size): str(x) for size, x in sizes if isinstance(x, str)})
    return out


def characters_of(text: str, file_tag: str, tags: set[str]) -> list[Character]:
    """Return the characters of one ``common/characters`` file.

    Args:
        text: File text.
        file_tag: File name stem.
        tags: Country tags.

    Returns:
        Characters with their portraits and roles.
    """
    items = list(tokens(text))
    top, _ = parse_block(items, 0)
    out = []
    for key, body in top:
        if key != "characters" or not isinstance(body, list):
            continue
        for token, block in body:
            if not isinstance(block, list):
                continue
            prefix = token[:TAG_LEN]
            tag = prefix if prefix in tags and token[TAG_LEN : TAG_LEN + 1] == "_" else file_tag
            if tag not in tags:
                continue  # no country to list it under (e.g. a shared file like Warlords_China)
            portraits = _portraits_of(block)
            instances = []
            for k, v in block:
                if k != "instance" or not isinstance(v, list):
                    continue
                pictures = _portraits_of(v)
                allowed = next((x for kk, x in v if kk == "allowed"), None)
                condition = instance_condition(allowed)
                if pictures and condition is not None:
                    instances.append((condition, pictures))
            name = next((str(v) for k, v in block if k == "name" and isinstance(v, str)), token)
            roles = frozenset(k for k, v in block if isinstance(v, list))
            out.append(Character(token, tag, name, portraits, roles, tuple(instances)))
    return out


def _small(large: str, small: str | None, textures: dict[str, str]) -> str:
    """Return the small sprite to write with a large one (CONTRACT 18.3, review 3.4).

    The small sprite of the same block; otherwise the large name with ``_small`` when
    the game defines it; otherwise the large one again (the game scales it).

    Args:
        large: Large sprite name.
        small: Small sprite of the same block, if any.
        textures: Known sprites.

    Returns:
        The small sprite name.
    """
    for candidate in (small, f"{large}_small"):
        if candidate is not None and STEM.fullmatch(candidate) and candidate in textures:
            return candidate
    return large


def _label(char: Character, english: dict[str, str]) -> str:
    """Return the label of a character: its game key, or the literal name the game shows.

    Args:
        char: Character.
        english: English localisation.

    Returns:
        Localisation text.
    """
    if char.name in english:
        return f"${char.name}$"
    if re.fullmatch(r"[A-Za-z0-9_]+", char.name) and char.name == char.token:
        return UNNAMED
    return char.name.replace('"', "").replace("$", "").replace("§", "").replace("[", "")


def build_catalog(
    characters: Iterable[Character],
    textures: dict[str, str],
    english: dict[str, str],
    dlc_textures: dict[str, tuple[str, str]] | None = None,
) -> PortraitCatalog:
    """Build the catalog.

    A portrait whose sprite only a DLC defines belongs to that DLC's pack. The
    catalog, the pools and every effect are the same for every player; only the UI
    asks ``has_dlc`` (MP: a state that depends on the local DLC set would go out of
    sync).

    Args:
        characters: Every character of the game.
        textures: Sprite name to texture file (``interface/*.gfx`` of the base game).
        english: English localisation.
        dlc_textures: Sprite name to ``(DLC name, texture file)`` from the DLC folders.

    Returns:
        The catalog.
    """
    dlc = dlc_textures or {}
    known = {**{k: t for k, (_, t) in dlc.items()}, **textures}
    packs = ("", *sorted({name for name, _ in dlc.values()}))
    found: dict[str, dict[str, object]] = {}
    skipped = 0
    for char in sorted(characters, key=lambda c: c.token):
        uses = []
        if "country_leader" in char.roles:
            uses.append(("civilian", True))
        uses += [(kind, False) for role, kind in GENERAL_ROLES.items() if role in char.roles]
        for kind, is_leader in uses:
            large = char.portraits.get((kind, "large"))
            if large is None:
                continue
            if not STEM.fullmatch(large) or large not in known:
                skipped += 1
                continue
            item = found.setdefault(
                large,
                {
                    "pack": 0 if large in textures else packs.index(dlc[large][0]),
                    "small": _small(large, char.portraits.get((kind, "small")), known),
                    "tag": char.tag,
                    "label": _label(char, english),
                    "leader": False,
                    "general": False,
                },
            )
            item["leader" if is_leader else "general"] = True
    entries = tuple(
        Entry(
            large,
            str(v["small"]),
            str(v["tag"]),
            str(v["label"]),
            bool(v["leader"]),
            bool(v["general"]),
            int(str(v["pack"])),
        )
        for large, v in sorted(found.items())
    )
    used = sorted({e.pack for e in entries} | {0})
    renumber = {old: new for new, old in enumerate(used)}
    packs = tuple(packs[i] for i in used)
    entries = tuple(
        Entry(e.large, e.small, e.tag, e.label, e.leader, e.general, renumber[e.pack])
        for e in entries
    )
    group_tags = tuple(sorted({e.tag for e in entries}))
    letters = {
        (kind, pack): letters_of(
            (
                t
                for t in group_tags
                if any(
                    e.tag == t and e.pack == pack and (e.leader if kind == LEADER else e.general)
                    for e in entries
                )
            ),
            english,
        )
        for kind in (LEADER, GENERAL)
        for pack in range(len(packs))
    }
    report = {
        "portraits": len(entries),
        "leaders": sum(e.leader for e in entries),
        "generals": sum(e.general for e in entries),
        "countries": len(group_tags),
        "skipped": skipped,
        "unnamed": sum(e.label == UNNAMED for e in entries),
        "dlc_portraits": sum(e.pack > 0 for e in entries),
        "dlc_packs": len(packs) - 1,
    }
    return PortraitCatalog(
        entries,
        {e.large: known[e.large] for e in entries},
        group_tags,
        letters,
        packs=packs,
        report=report,
    )


def base_roots(root: Path) -> list[Path]:
    """Return the folders whose files every player has: the game and its integrated DLC.

    Since 1.19 the game ships four former DLC (Together for Victory, Death or Dishonor,
    Waking the Tiger, Man the Guns) in ``integrated_dlc/*`` for every player; their sprites
    and textures count as base game (pack 0, no ``has_dlc``).

    Args:
        root: Game installation folder.

    Returns:
        The game folder followed by each ``integrated_dlc`` folder, sorted.
    """
    return [root, *sorted(p for p in (root / "integrated_dlc").glob("*") if p.is_dir())]


def has_base_file(root: Path, relative: str) -> bool:
    """Return True when a file exists in the game or in one of its integrated DLC.

    Args:
        root: Game installation folder.
        relative: Path relative to a content root (``gfx/leaders/...``).

    Returns:
        Whether every player has the file.
    """
    return any((base / relative).is_file() for base in base_roots(root))


def read_textures(root: Path) -> dict[str, str]:
    """Return every base-game sprite name with its texture file.

    Reads ``interface/*.gfx`` of the game and of its integrated DLC (:func:`base_roots`).

    Args:
        root: Game installation folder.

    Returns:
        Sprite name to texture file.
    """
    out: dict[str, str] = {}
    for base in base_roots(root):
        for path in sorted((base / "interface").glob("*.gfx")):
            for name, quoted, bare in SPRITE.findall(
                path.read_text(encoding="utf-8", errors="replace")
            ):
                texture = (quoted or bare).replace("\\\\", "/").replace("//", "/")
                # A game sprite whose file is missing (e.g. a wrong path in the game's own .gfx) is
                # skipped: copying it would only add a "texture not found" error and a blank cell.
                if has_base_file(root, texture):
                    out.setdefault(name, texture)
    return out


def read_dlc_textures(root: Path) -> dict[str, tuple[str, str]]:
    """Return the sprites the DLC folders define, with the DLC's ``has_dlc`` name.

    Args:
        root: Game installation folder.

    Returns:
        Sprite name to ``(DLC name, texture file)``; the first DLC wins.
    """
    out: dict[str, tuple[str, str]] = {}
    for folder in sorted((root / "dlc").glob("*")):
        dlc_name = checkable_dlc(next(iter(sorted(folder.glob("*.dlc"))), None))
        if dlc_name is None:
            continue
        for path in sorted((folder / "interface").glob("*.gfx")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for name, quoted, bare in SPRITE.findall(text):
                texture = (quoted or bare).replace("\\", "/").replace("//", "/")
                if (folder / texture).is_file() or has_base_file(root, texture):
                    out.setdefault(name, (dlc_name, texture))
    return out


EXPECTED_DLC = Path(__file__).with_name("portrait_dlc.txt")
"""The DLC folders (``dlc/*``, ``integrated_dlc/*``) the committed catalogs were generated from."""


def check_dlc_folders(root: Path) -> None:
    """Stop when the installed DLC folders differ from :data:`EXPECTED_DLC`.

    Steam creates a ``dlc/`` folder only for owned DLC, so a maintainer without one DLC would
    generate a different catalog: other pack numbers, another fingerprint, and every player's
    saved picker index would read as stale after the release.

    Args:
        root: Game installation folder.

    Raises:
        ValueError: A folder of the list is missing, or the game has one the list does not name.
    """
    lines = EXPECTED_DLC.read_text(encoding="utf-8").splitlines()
    expected = {x.strip() for x in lines if x.strip() and not x.startswith("#")}
    found = {
        f"{kind}/{p.name}"
        for kind in ("dlc", "integrated_dlc")
        for p in (root / kind).glob("*")
        if p.is_dir()
    }
    missing, extra = sorted(expected - found), sorted(found - expected)
    if missing or extra:
        msg = (
            f"DLC folders differ from {EXPECTED_DLC.name}: missing {missing or 'none'}, "
            f"not listed {extra or 'none'}. Install the missing DLC, or update the list "
            "together with a release."
        )
        raise ValueError(msg)


def read_catalog(root: str) -> PortraitCatalog:
    """Read the catalog from a HOI4 installation.

    Args:
        root: Game installation folder.

    Returns:
        The catalog. :func:`check_dlc_folders` stops first when the installed DLC folders
        differ from :data:`EXPECTED_DLC`.
    """
    game = Path(root)
    check_dlc_folders(game)
    tags = set(read_tags(root))
    chars: list[Character] = []
    for path in sorted((game / "common" / "characters").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        chars += characters_of(text, path.stem, tags)
    dlc = {**read_base_sprites_in_dlc(game), **read_dlc_textures(game)}
    return build_catalog(chars, read_textures(game), read_english(root), dlc)


def read_base_sprites_in_dlc(root: Path) -> dict[str, tuple[str, str]]:
    """Return base-game sprites whose texture file exists only in a DLC folder.

    The base ``interface/*.gfx`` defines some portraits
    (``gfx/leaders/Asia/portrait_asia_generic_4``) whose file ships with a DLC. Without that DLC
    the sprite has no texture, so it belongs to the DLC's pack (shown only with ``has_dlc``), not
    to the base game. A texture in the game or an integrated DLC (:func:`has_base_file`) is base.

    Args:
        root: Game installation folder.

    Returns:
        Sprite name to ``(DLC name, texture file)``.
    """
    folders: list[tuple[Path, str]] = []
    for folder in sorted((root / "dlc").glob("*")):
        name = checkable_dlc(next(iter(sorted(folder.glob("*.dlc"))), None))
        if name is not None:
            folders.append((folder, name))
    out: dict[str, tuple[str, str]] = {}
    for path in [
        p for base in base_roots(root) for p in sorted((base / "interface").glob("*.gfx"))
    ]:
        for name, quoted, bare in SPRITE.findall(
            path.read_text(encoding="utf-8", errors="replace")
        ):
            texture = (quoted or bare).replace("\\\\", "/").replace("//", "/")
            if has_base_file(root, texture):
                continue
            owner = next((dlc for folder, dlc in folders if (folder / texture).is_file()), None)
            if owner is not None:
                out.setdefault(name, (owner, texture))
    return out


# ----------------------------------------------------------------------------- output


def gfx(catalog: PortraitCatalog) -> str:
    """Return the sprite file: one alias per index, pointing at the game's texture.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_GFX`.
    """
    lines = [
        GEN_HEADER,
        "# Portrait catalog sprites: GFX_rnp_<n> uses the texture of the game's large portrait.\n",
        "spriteTypes = {\n",
    ]
    lines += [
        f'\tspriteType = {{ name = "GFX_rnp_{n}" texturefile = "{catalog.textures[e.large]}" }}\n'
        for n, e in enumerate(catalog.entries, start=1)
    ]
    lines.append("}\n")
    return "".join(lines)


def _fill_group(catalog: PortraitCatalog) -> list[str]:
    """Return ``rn_pp_fill_group``: a group's portraits of the current kind into ``rn_pp_list``.

    Args:
        catalog: The catalog.

    Returns:
        Lines.
    """
    leaves = {}
    for g, tag in enumerate(catalog.tags, start=1):
        parts = []
        for kind in (LEADER, GENERAL):
            for pack in range(len(catalog.packs)):
                pool = catalog.pool(tag, kind, pack)
                if not pool:
                    continue
                adds = " ".join(f"add_to_array = {{ rn_pp_list = {i} }}" for i in pool)
                word = "if" if not parts else "else_if"
                parts.append(
                    f"{word} = {{ limit = {{ check_variable = {{ rn_pp_kind = {kind} }} "
                    f"check_variable = {{ rn_pp_pack = {pack} }} }} {adds} }}"
                )
        if parts:
            leaves[g] = " ".join(parts)
    return [
        "# ROOT scope. Input temp rn_pp_g (1..groups). Adds the group's portraits of the kind\n",
        f"# ROOT.rn_pp_kind ({LEADER} leaders, {GENERAL} generals) and the pack ROOT.rn_pp_pack\n",
        "# (0 base game, k a DLC) to rn_pp_list. No DLC check here: the list is game state.\n",
        "rn_pp_fill_group = {\n",
        *dispatch("temp_var:rn_pp_g", 1, len(catalog.tags), leaves, "\t"),
        "}\n\n",
    ]


def _fill_letter(catalog: PortraitCatalog) -> list[str]:
    """Return ``rn_pp_fill_letter``: the countries of a letter with the current kind and pack.

    Args:
        catalog: The catalog.

    Returns:
        Lines.
    """
    out = [
        "# ROOT scope. Adds the countries of letter rn_pp_letter that have portraits of the kind\n",
        "# rn_pp_kind in the pack rn_pp_pack, sorted by English name, to rn_pp_list.\n",
        "rn_pp_fill_letter = {\n",
    ]
    first = True
    for (kind, pack), letters in catalog.letters.items():
        for n, tags in enumerate(letters, start=1):
            if not tags:
                continue
            adds = " ".join(
                f"{t} = {{ ROOT = {{ add_to_array = {{ rn_pp_list = PREV }} }} }}" for t in tags
            )
            word = "if" if first else "else_if"
            first = False
            cond = (
                f"check_variable = {{ rn_pp_kind = {kind} }} "
                f"check_variable = {{ rn_pp_pack = {pack} }} "
                f"{check_variable(f'rn_pp_letter = {n}')}"
            )
            out.append(f"\t{word} = {{ limit = {{ {cond} }} {adds} }}\n")
    out.append("}\n\n")
    return out


def _entry_info(catalog: PortraitCatalog) -> list[str]:
    """Return ``rn_pp_entry_info``: group and kinds of one index, for the pool rule at Apply.

    Args:
        catalog: The catalog.

    Returns:
        Lines.
    """
    group = {t: g for g, t in enumerate(catalog.tags, start=1)}
    leaves = {
        n: (
            f"set_temp_variable = {{ rn_pp_e_g = {group[e.tag]} }} "
            f"set_temp_variable = {{ rn_pp_e_leader = {int(e.leader)} }} "
            f"set_temp_variable = {{ rn_pp_e_general = {int(e.general)} }}"
        )
        for n, e in enumerate(catalog.entries, start=1)
    }
    return [
        "# Any scope. Input temp rn_pp_w (catalog index). Output temps rn_pp_e_g (its group),\n",
        "# rn_pp_e_leader and rn_pp_e_general (1/0); all 0 for a value outside the catalog.\n",
        "rn_pp_entry_info = {\n",
        "\tset_temp_variable = { rn_pp_e_g = 0 }\n",
        "\tset_temp_variable = { rn_pp_e_leader = 0 }\n",
        "\tset_temp_variable = { rn_pp_e_general = 0 }\n",
        *dispatch("temp_var:rn_pp_w", 1, len(catalog.entries), leaves, "\t"),
        "}\n\n",
    ]


def _write_portrait(catalog: PortraitCatalog) -> list[str]:
    """Return ``rn_pp_write_portrait``: the carrier arrays of one index (contract section 18).

    Args:
        catalog: The catalog.

    Returns:
        Lines (empty until :data:`CARRIER_READY`).
    """
    if not carrier_ready():
        return []
    leaves = {}
    for n, e in enumerate(catalog.entries, start=1):
        leaves[n] = (
            write_leaf(e.large, "capie_pt_s", "capie_pt_len")
            + " "
            + write_leaf(e.small, "capie_pt_ss", "capie_pt_slen")
        )
    return [
        "# Character scope. Input temp rn_pp_w. Writes capie_pt_s/_len and capie_pt_ss/_slen.\n",
        "rn_pp_write_portrait = {\n",
        *dispatch("temp_var:rn_pp_w", 1, len(catalog.entries), leaves, "\t"),
        "}\n\n",
    ]


def carrier_ready() -> bool:
    """Return whether the portrait carrier is written (the native contract exists).

    Returns:
        :data:`CARRIER_READY`.
    """
    return CARRIER_READY


def _fingerprint(catalog: PortraitCatalog) -> int:
    """Return the catalog fingerprint (``rn_pt_cat`` on a character names its catalog).

    Args:
        catalog: The catalog.

    Returns:
        Fingerprint of the large sprite names in index order.
    """
    return fingerprint(e.large for e in catalog.entries)


def effects(catalog: PortraitCatalog) -> str:
    """Return the generated catalog effects.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_EFFECTS`.
    """
    n = len(catalog.entries)
    out = [
        GEN_HEADER,
        "# Portrait catalog lookups for the portrait picker\n",
        "# (tools/modgen/features/portraits.py).\n",
        f"# Catalog: {n} portraits of {len(catalog.tags)} countries.\n\n",
        "rn_pp_catalog = {\n",
        f"\tset_temp_variable = {{ rn_pp_n = {n} }}\n",
        f"\tset_temp_variable = {{ rn_pp_cat = {_fingerprint(catalog)} }}\n",
        f"\tset_temp_variable = {{ rn_pp_packs = {len(catalog.packs)} }}\n",
        "}\n\n",
        "# Country scope. Output temp rn_pp_g: portrait group of the original tag, 0 = none.\n",
        "rn_pp_group_of = {\n\tset_temp_variable = { rn_pp_g = 0 }\n",
    ]
    for g, tag in enumerate(catalog.tags, start=1):
        word = "if" if g == 1 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ original_tag = {tag} }} "
            f"set_temp_variable = {{ rn_pp_g = {g} }} }}\n"
        )
    out.append("}\n\n")
    out += _fill_group(catalog)
    out += _fill_letter(catalog)
    out += _entry_info(catalog)
    out += _write_portrait(catalog)
    return "".join(out)


def scripted_loc(catalog: PortraitCatalog) -> str:
    """Return the selected portrait's name and the portrait cooldown's days left.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_SCRIPTED_LOC`.
    """
    return "".join(
        [
            GEN_HEADER,
            "# Name of the selected portrait (ROOT.rn_pp_sel): bucket, then index.\n",
            selected_name_loc(
                "RN_PP_SEL_NAME", "rn_pp_sel", len(catalog.entries), "RN_PPB_", "RN_PPL_"
            ),
            "# Days left of the portrait cooldown (scope: the country whose leader changes).\n",
            days_left_loc("RN_IP_CD_LEFT_PORTRAIT", "rn_ip_cd_portrait_until"),
            "# Name of the shown portrait pack (ROOT.rn_pp_pack).\n",
            defined_text(
                "RN_PP_PACK_NAME",
                [
                    (check_variable(f"rn_pp_pack = {k}"), f"RN_PP_PACK_{k}")
                    for k in range(1, len(catalog.packs))
                ],
                "RN_PP_PACK_0",
            ),
        ]
    )


def localisation(catalog: PortraitCatalog, lang: str) -> str:
    """Return the label file of one language (the same text in every language).

    Args:
        catalog: The catalog.
        lang: Game language.

    Returns:
        The ``.yml`` text (the caller adds the BOM).
    """
    from modgen.features.catalog_common import bucket_lines  # noqa: PLC0415 - one caller

    lines = [f"l_{lang}:\n"]
    lines += bucket_lines("RN_PP_SEL_NAME", len(catalog.entries), "RN_PPB_")
    lines += [f' RN_PPL_{n}:0 "{e.label}"\n' for n, e in enumerate(catalog.entries, start=1)]
    lines.append(' RN_PP_PACK_0:0 "$RN_PP_BASE_GAME$"\n')
    lines += [f' RN_PP_PACK_{k}:0 "{name}"\n' for k, name in enumerate(catalog.packs) if k]
    return "".join(lines)


def on_actions() -> str:
    """Return the daily portrait commit (CONTRACT 18: required, no cooldown).

    A country whose ruling leader has a portrait layer sets ``capie_pt_rev`` every day,
    so CAPIE shows the layer after a change of leader that recomputes no names; an
    open own picker refreshes.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE`.
    """
    return (
        GEN_HEADER
        + "# Daily: commit the portrait layer of the ruling leader (CONTRACT 18), and refresh\n"
        "# an open portrait picker (dirty = rn_pp_dirty).\n"
        "on_actions = {\n\ton_daily = {\n\t\teffect = {\n"
        "\t\t\tif = {\n"
        "\t\t\t\tlimit = {\n"
        "\t\t\t\t\tany_character = { is_country_leader = yes has_variable = capie_pt_ver }\n"
        "\t\t\t\t}\n"
        "\t\t\t\tset_variable = { capie_pt_rev = 1 }\n"
        "\t\t\t}\n"
        "\t\t\tif = { limit = { is_ai = no has_country_flag = rn_pp_open_own } "
        "add_to_variable = { rn_pp_dirty = 1 } }\n"
        "\t\t}\n\t}\n}\n"
    )


def write_files(catalog: PortraitCatalog) -> list[tuple[str, str, bool]]:
    """Return every generated catalog file.

    Args:
        catalog: The catalog.

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    files = [
        (CATALOG_GFX, gfx(catalog), False),
        (CATALOG_EFFECTS, effects(catalog), False),
        (CATALOG_SCRIPTED_LOC, scripted_loc(catalog), False),
        (ON_ACTIONS_FILE, on_actions(), False),
    ]
    files += [
        (f"localisation/{lang}/rn_portrait_catalog_l_{lang}.yml", localisation(catalog, lang), True)
        for lang in LANGS
    ]
    return files
