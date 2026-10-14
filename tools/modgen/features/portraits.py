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
from modgen.script import check_variable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

CARRIER_READY = True
"""The CAPIE portrait contract exists (contract-ready.txt, CONTRACT section 18)."""

TOKEN = re.compile(r'"[^"]*"|[{}=]|[^\s{}="]+')
"""Tokens of a Paradox script file (quoted string, brace, equals, word)."""

SPRITE = re.compile(
    r'spriteType\s*=\s*\{[^{}]*?name\s*=\s*"?([^"\s}]+)"?[^{}]*?texturefile\s*=\s*"?([^"\s}]+)"?',
    re.IGNORECASE | re.DOTALL,
)
"""A ``spriteType`` with its name and texture file (name before texturefile, as in vanilla)."""

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


@dataclass(frozen=True)
class PortraitCatalog:
    """Every portrait the picker offers."""

    entries: tuple[Entry, ...]
    """Catalog entries; index ``n`` is ``entries[n - 1]``."""

    textures: dict[str, str]
    """Large sprite name to its texture file."""

    tags: tuple[str, ...]
    """Group tags (group ``g`` is ``tags[g - 1]``)."""

    letters: dict[int, tuple[tuple[str, ...], ...]]
    """Kind to the tags of each letter that have portraits of that kind."""

    report: dict[str, int] = field(default_factory=dict)
    """Counts for the generator's summary line."""

    def pool(self, tag: str, kind: int) -> tuple[int, ...]:
        """Return the indices of a country's portraits of one kind.

        Args:
            tag: Country tag.
            kind: :data:`LEADER` or :data:`GENERAL`.

        Returns:
            Catalog indices in catalog order.
        """
        return tuple(
            n
            for n, e in enumerate(self.entries, start=1)
            if e.tag == tag and (e.leader if kind == LEADER else e.general)
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
            portraits: dict[tuple[str, str], str] = {}
            for k, v in block:
                if k == "portraits" and isinstance(v, list):
                    for kind, sizes in v:
                        if isinstance(sizes, list):
                            portraits.update(
                                {(kind, size): str(s) for size, s in sizes if isinstance(s, str)}
                            )
            name = next((str(v) for k, v in block if k == "name" and isinstance(v, str)), token)
            roles = frozenset(k for k, v in block if isinstance(v, list))
            out.append(Character(token, tag, name, portraits, roles))
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
) -> PortraitCatalog:
    """Build the catalog.

    Args:
        characters: Every character of the game.
        textures: Sprite name to texture file (``interface/*.gfx``).
        english: English localisation.

    Returns:
        The catalog.
    """
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
            if not STEM.fullmatch(large) or large not in textures:
                skipped += 1
                continue
            item = found.setdefault(
                large,
                {
                    "small": _small(large, char.portraits.get((kind, "small")), textures),
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
        )
        for large, v in sorted(found.items())
    )
    group_tags = tuple(sorted({e.tag for e in entries}))
    letters = {
        kind: letters_of(
            (
                t
                for t in group_tags
                if any(e.tag == t and (e.leader if kind == LEADER else e.general) for e in entries)
            ),
            english,
        )
        for kind in (LEADER, GENERAL)
    }
    report = {
        "portraits": len(entries),
        "leaders": sum(e.leader for e in entries),
        "generals": sum(e.general for e in entries),
        "countries": len(group_tags),
        "skipped": skipped,
        "unnamed": sum(e.label == UNNAMED for e in entries),
    }
    return PortraitCatalog(
        entries, {e.large: textures[e.large] for e in entries}, group_tags, letters, report
    )


def read_textures(root: Path) -> dict[str, str]:
    """Return every vanilla sprite name with its texture file.

    Args:
        root: Game installation folder.

    Returns:
        Sprite name to texture file.
    """
    out: dict[str, str] = {}
    for path in sorted((root / "interface").glob("*.gfx")):
        for name, texture in SPRITE.findall(path.read_text(encoding="utf-8", errors="replace")):
            out.setdefault(name, texture.replace("\\\\", "/").replace("//", "/"))
    return out


def read_catalog(root: str) -> PortraitCatalog:
    """Read the catalog from a HOI4 installation.

    Args:
        root: Game installation folder.

    Returns:
        The catalog.
    """
    game = Path(root)
    tags = set(read_tags(root))
    chars: list[Character] = []
    for path in sorted((game / "common" / "characters").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        chars += characters_of(text, path.stem, tags)
    return build_catalog(chars, read_textures(game), read_english(root))


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
        leaders = " ".join(
            f"add_to_array = {{ rn_pp_list = {i} }}" for i in catalog.pool(tag, LEADER)
        )
        generals = " ".join(
            f"add_to_array = {{ rn_pp_list = {i} }}" for i in catalog.pool(tag, GENERAL)
        )
        leaves[g] = (
            f"if = {{ limit = {{ check_variable = {{ rn_pp_kind = {GENERAL} }} }} {generals} }} "
            f"else = {{ {leaders} }}"
        )
    return [
        "# ROOT scope. Input temp rn_pp_g (1..groups). Adds the group's portraits of the kind\n",
        f"# ROOT.rn_pp_kind ({LEADER} leaders, {GENERAL} generals) to rn_pp_list.\n",
        "rn_pp_fill_group = {\n",
        *dispatch("temp_var:rn_pp_g", 1, len(catalog.tags), leaves, "\t"),
        "}\n\n",
    ]


def _fill_letter(catalog: PortraitCatalog) -> list[str]:
    """Return ``rn_pp_fill_letter``: the countries of a letter that have the current kind.

    Args:
        catalog: The catalog.

    Returns:
        Lines.
    """
    out = [
        "# ROOT scope. Adds the countries of letter rn_pp_letter that have portraits of the kind\n",
        "# rn_pp_kind, sorted by English name, to rn_pp_list.\n",
        "rn_pp_fill_letter = {\n",
    ]
    for kind in (LEADER, GENERAL):
        word = "if" if kind == LEADER else "else"
        guard = (
            f"limit = {{ check_variable = {{ rn_pp_kind = {LEADER} }} }} " if kind == LEADER else ""
        )
        out.append(f"\t{word} = {{\n\t\t{guard}\n")
        first = True
        for n, tags in enumerate(catalog.letters[kind], start=1):
            if not tags:
                continue
            adds = " ".join(
                f"{t} = {{ ROOT = {{ add_to_array = {{ rn_pp_list = PREV }} }} }}" for t in tags
            )
            w = "if" if first else "else_if"
            first = False
            out.append(
                f"\t\t{w} = {{ limit = {{ {check_variable(f'rn_pp_letter = {n}')} }} {adds} }}\n"
            )
        out.append("\t}\n")
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
