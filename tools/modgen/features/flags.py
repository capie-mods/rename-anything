"""Flag catalog: the flag files of the game, their pools and the script that uses them.

The player picks a flag for a country in the flag picker (``flag_picker``). The
picker shows only files that exist in the game: the generator reads
``gfx/flags`` and ``gfx/flags/medium`` at build time and numbers every stem that
has both sizes (catalog index ``1..N``, sorted by stem). Nothing is copied; the
sprites point at the game's own files, so a mod that replaces a flag file is
shown as it is.

Generated files (all relative to ``mod/``):

* ``interface/rn_flag_catalog.gfx``: ``GFX_rnf_<n>`` (large, 82x52, the preview)
  and ``GFX_rnfm_<n>`` (medium, 41x26, the grid) for every catalog index. The
  sprites keep the game's default lazy loading (no ``legacy_lazy_load = no``),
  review K6.
* ``common/scripted_effects/rn_flag_catalog.txt``: the lookups the hand-written
  picker effects call. ``rn_fp_group_of`` (country scope: its pool group by
  ``original_tag``), ``rn_fp_fill_group`` and ``rn_fp_fill_letter`` (fill
  ``rn_fp_list``), ``rn_fp_resolve_game`` (the flag file the game shows for a
  country: cosmetic tag with ideology, cosmetic tag, tag with ideology, tag),
  ``rn_fp_write_stem`` (the CAPIE carrier ``capie_cf_s``/``capie_cf_len`` of one
  index, CONTRACT section 17.3), ``rn_fp_cos_write`` and ``rn_fp_cos_match`` (the
  cosmetic tag snapshot ``capie_cf_cos``) and two constants.
* ``common/scripted_localisation/rn_flag_catalog.txt``: the name of the selected
  flag (two-level lookup by index) and the flag cooldown's days left.
* ``localisation/<lang>/rn_flag_catalog_l_<lang>.yml``: one label per index, the
  same in every language because it is made of references to the game's own
  keys (``$POL_KINGDOM_neutrality$ ($neutrality$)``); never a file name.
* ``common/on_actions/rn_flag_on_actions.txt``: the daily cosmetic tag check of
  countries with a flag layer and the daily refresh of an open picker.

Pools (decision 2026-10-14, design.txt 2.2 and review K5). A tag's pool is every
flag key equal to the tag or starting with ``<TAG>_``: the tag's own flags first
(bare, then the four ideologies in the game's order), then its cosmetic variants
sorted by key. Keys that start with no tag (formable nations such as
``SCA_UNIFIED``) form the "Other" group, offered only when the game rule allows
every flag. The "all flags" view lists countries by the first letter of their
English name, so the list is the same for every player of a multiplayer game.

Limits: flags that other mods add as new files are not in the catalog (a mod or
the console can still set them through the CAPIE contract); a cosmetic tag the
game files never set is unknown to the snapshot (the snapshot is then left
absent, so CAPIE's display gate does not hide the flag, and only a known
cosmetic tag resets it).
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from modgen.common import GEN_HEADER, LANGS
from modgen.script import check_variable, defined_text

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

IDEOLOGIES = ("democratic", "communism", "fascism", "neutrality")
"""Vanilla ideology groups in the order of ``common/ideologies/00_ideologies.txt``."""

STEM = re.compile(r"[A-Za-z0-9_]{1,63}")
"""A flag stem or cosmetic tag CAPIE can carry (CONTRACT 17.3: 1..63 file-name characters)."""

TAG = re.compile(r"\s*([A-Z][A-Z0-9]{2})\s*=")
"""One ``TAG = "countries/..."`` line of ``common/country_tags``."""

LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')
"""One ``key:0 "text"`` localisation line."""

COSMETIC = re.compile(r"set_cosmetic_tag\s*=\s*\"?([A-Za-z0-9_]+)")
"""One ``set_cosmetic_tag = X`` in the game's script."""

UNNAMED = re.compile(r"\$ \d")
"""A label made of a pool position because the game has no name for the flag."""

SCRIPT_DIRS = ("common", "events", "history")
"""Game folders scanned for ``set_cosmetic_tag`` values."""

TAG_LEN = 3
"""Length of a country tag; a key belongs to tag ``T`` when it is ``T`` or starts with ``T_``."""

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
"""Letters of the country list; letter ``n`` (1-based) is ``LETTERS[n - 1]``."""

OTHER_LETTER = len(LETTERS) + 1
"""Value of ``rn_fp_letter`` for the "Other" group (keys that start with no tag)."""

NAME_BUCKET = 64
"""Width of an index bucket in the two-level name lookup."""

WRITE_LEAF = 1
"""Range size at which the binary dispatch of ``rn_fp_write_stem`` stops splitting."""

CATALOG_GFX = "interface/rn_flag_catalog.gfx"
"""Sprite file of the catalog, relative to ``mod/``."""

CATALOG_EFFECTS = "common/scripted_effects/rn_flag_catalog.txt"
"""Generated effects of the catalog, relative to ``mod/``."""

CATALOG_SCRIPTED_LOC = "common/scripted_localisation/rn_flag_catalog.txt"
"""Generated scripted localisation of the catalog, relative to ``mod/``."""

ON_ACTIONS_FILE = "common/on_actions/rn_flag_on_actions.txt"
"""Daily flag checks, relative to ``mod/``."""

EMPTY_KEY = "RN_IPP_EMPTY"
"""Existing empty localisation key (in-place editor) used as a fallback."""

CODE_LOWER = 1
"""File-name alphabet code of ``a`` (CONTRACT 17.3)."""

CODE_UPPER = 27
"""File-name alphabet code of ``A``."""

CODE_DIGIT = 53
"""File-name alphabet code of ``0``."""

CODE_UNDERSCORE = 63
"""File-name alphabet code of ``_``."""

PACK = 64
"""Base of the three-character packing (``c0 * 4096 + c1 * 64 + c2``)."""

PACK_WIDTH = 3
"""Characters per packed element."""

CATALOG_HASH_MOD = 1_000_000
"""Range of the catalog fingerprint (kept well inside HOI4's variable range)."""

FNV_OFFSET = 0x811C9DC5
"""FNV-1a 32-bit offset basis."""

FNV_PRIME = 0x01000193
"""FNV-1a 32-bit prime."""

FNV_MASK = 0xFFFFFFFF
"""32-bit mask of the FNV-1a hash."""


def code(char: str) -> int:
    """Return the file-name alphabet code of one character (CONTRACT 17.3).

    Args:
        char: ``a-z``, ``A-Z``, ``0-9`` or ``_``.

    Returns:
        The code, 1..63.

    Raises:
        ValueError: The character is not in the file-name alphabet.
    """
    if "a" <= char <= "z":
        return CODE_LOWER + ord(char) - ord("a")
    if "A" <= char <= "Z":
        return CODE_UPPER + ord(char) - ord("A")
    if "0" <= char <= "9":
        return CODE_DIGIT + ord(char) - ord("0")
    if char == "_":
        return CODE_UNDERSCORE
    msg = f"not a file-name character: {char!r}"
    raise ValueError(msg)


def pack(text: str) -> list[int]:
    """Pack a stem three characters per element, the last element padded with 0.

    Args:
        text: A stem that matches :data:`STEM`.

    Returns:
        ``ceil(len / 3)`` elements ``c0 * 4096 + c1 * 64 + c2``.

    Raises:
        ValueError: The text is not a valid stem.
    """
    if not STEM.fullmatch(text):
        msg = f"not a flag stem: {text!r}"
        raise ValueError(msg)
    codes = [code(c) for c in text]
    codes += [0] * (-len(codes) % PACK_WIDTH)
    return [
        codes[i] * PACK * PACK + codes[i + 1] * PACK + codes[i + 2]
        for i in range(0, len(codes), PACK_WIDTH)
    ]


def split_stem(stem: str) -> tuple[str, str | None]:
    """Split a stem into its flag key and ideology suffix.

    Args:
        stem: File name without ``.tga``.

    Returns:
        ``(key, ideology)``; the ideology is None for a bare key.
    """
    for ideology in IDEOLOGIES:
        if stem.endswith("_" + ideology) and len(stem) > len(ideology) + 1:
            return stem[: -len(ideology) - 1], ideology
    return stem, None


def fingerprint(stems: Iterable[str]) -> int:
    """Return a stable fingerprint of the catalog order (FNV-1a, 1..1 000 000).

    A country stores it next to the catalog index of its flag (``rn_cf_cat``); after
    a game or mod update that renumbers the catalog the stored index is ignored.

    Args:
        stems: Catalog stems in index order.

    Returns:
        The fingerprint.
    """
    value = FNV_OFFSET
    for byte in "\n".join(stems).encode("ascii"):
        value = ((value ^ byte) * FNV_PRIME) & FNV_MASK
    return value % CATALOG_HASH_MOD + 1


@dataclass(frozen=True)
class FlagGroup:
    """One pool of the catalog: a tag's flags or the "Other" flags."""

    tag: str
    """Country tag, or an empty string for the "Other" group."""

    indices: tuple[int, ...]
    """Catalog indices in pool order."""


@dataclass(frozen=True)
class FlagCatalog:
    """Every flag the picker offers, with its pools, labels and the known cosmetic tags."""

    stems: tuple[str, ...]
    """Catalog stems; index ``n`` is ``stems[n - 1]``."""

    groups: tuple[FlagGroup, ...]
    """Tag groups sorted by tag (group id ``g`` is ``groups[g - 1]``), the "Other" group last."""

    letters: tuple[tuple[str, ...], ...]
    """Tags of each letter of :data:`LETTERS`, sorted by English name."""

    cosmetics: tuple[str, ...]
    """Known cosmetic tags (set by the game's script or named by a flag key), sorted."""

    labels: tuple[str, ...]
    """Localisation text of each index, made of references to game keys."""

    report: dict[str, int] = field(default_factory=dict)
    """Counts for the generator's summary line."""

    @property
    def index(self) -> dict[str, int]:
        """Return the catalog index of every stem.

        Returns:
            Stem to 1-based index.
        """
        return {stem: n for n, stem in enumerate(self.stems, start=1)}

    @property
    def other_group(self) -> int:
        """Return the group id of the "Other" group.

        Returns:
            The last group id.
        """
        return len(self.groups)


def _name_part(key: str, ideology: str | None, english: dict[str, str]) -> str | None:
    """Return the name reference of a flag key, or None when the game has no name for it.

    Args:
        key: Flag key (stem without the ideology).
        ideology: Ideology suffix of the stem, or None.
        english: English localisation.

    Returns:
        ``$KEY$`` of the most specific existing name.
    """
    stem = key if ideology is None else f"{key}_{ideology}"
    candidates = [stem, key, *(f"{key}_{i}" for i in IDEOLOGIES)]
    return next((f"${c}$" for c in candidates if c in english), None)


def _labels(
    stems: tuple[str, ...], groups: tuple[FlagGroup, ...], english: dict[str, str]
) -> tuple[str, ...]:
    """Return the label of every catalog index.

    A label names the country or cosmetic tag through the game's own key and adds
    the ideology in parentheses; without any key it is the tag name and the
    position in the pool, or "Other flag" and the position.

    Args:
        stems: Catalog stems.
        groups: Pools.
        english: English localisation.

    Returns:
        One text per index.
    """
    position = {}
    for group in groups:
        for i, n in enumerate(group.indices, start=1):
            position[n] = (group.tag, i)
    out = []
    for n, stem in enumerate(stems, start=1):
        key, ideology = split_stem(stem)
        name = _name_part(key, ideology, english)
        if name is None:
            tag, i = position[n]
            name = f"${tag}$ {i}" if tag in english else f"$RN_FP_OTHER_FLAG$ {i}"
        suffix = f" (${ideology}$)" if ideology is not None and ideology in english else ""
        out.append(name + suffix)
    return tuple(out)


def _first_letter(name: str, tag: str) -> int:
    """Return the 1-based letter of a country name (ASCII after removing accents).

    Args:
        name: English name.
        tag: Tag, used when the name has no letter.

    Returns:
        1..26.
    """
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().upper()
    letter = next((c for c in plain if c in LETTERS), tag[0])
    return LETTERS.index(letter) + 1


def _english_name(tag: str, english: dict[str, str]) -> str:
    """Return the plain English name of a tag, or the tag when it is missing or scripted.

    Args:
        tag: Country tag.
        english: English localisation.

    Returns:
        The name used for sorting.
    """
    text = english.get(tag, "")
    return tag if not text or any(c in text for c in "[$§") else text


def build_catalog(
    large: Iterable[str],
    medium: Iterable[str],
    tags: Iterable[str],
    english: dict[str, str],
    cosmetic_values: Iterable[str],
) -> FlagCatalog:
    """Build the catalog from the game's flag files, tags, names and cosmetic tags.

    Args:
        large: Stems in ``gfx/flags``.
        medium: Stems in ``gfx/flags/medium``.
        tags: Country tags.
        english: English localisation (key to text).
        cosmetic_values: Every ``set_cosmetic_tag`` value of the game's script.

    Returns:
        The catalog.
    """
    both = set(large) & set(medium)
    stems = tuple(sorted(s for s in both if STEM.fullmatch(s)))
    index = {s: n for n, s in enumerate(stems, start=1)}
    tagset = set(tags)
    by_key: dict[str, dict[str | None, int]] = {}
    for stem in stems:
        key, ideology = split_stem(stem)
        by_key.setdefault(key, {})[ideology] = index[stem]
    owner = {
        k: k[:TAG_LEN]
        for k in by_key
        if k[:TAG_LEN] in tagset and (len(k) == TAG_LEN or k[TAG_LEN] == "_")
    }
    order = (None, *IDEOLOGIES)

    def pool(keys: list[str]) -> tuple[int, ...]:
        """Return the indices of keys, each key bare first and then by ideology.

        Args:
            keys: Flag keys in pool order.

        Returns:
            Catalog indices.
        """
        return tuple(by_key[k][i] for k in keys for i in order if i in by_key[k])

    pool_tags = sorted(set(owner.values()))
    groups = [
        FlagGroup(
            t, pool(sorted((k for k, o in owner.items() if o == t), key=lambda k: (k != t, k)))
        )
        for t in pool_tags
    ]
    orphans = sorted(k for k in by_key if k not in owner)
    groups.append(FlagGroup("", pool(orphans)))
    letters: list[list[str]] = [[] for _ in LETTERS]
    for t in sorted(pool_tags, key=lambda t: (_english_name(t, english).casefold(), t)):
        letters[_first_letter(_english_name(t, english), t) - 1].append(t)
    cosmetics = {c for c in cosmetic_values if STEM.fullmatch(c) and c not in tagset}
    cosmetics |= {k for k in by_key if k not in tagset}
    labels = _labels(stems, tuple(groups), english)
    report = {
        "flags": len(stems),
        "large_only": len(set(large) - set(medium)),
        "medium_only": len(set(medium) - set(large)),
        "groups": len(pool_tags),
        "other_flags": len(groups[-1].indices),
        "cosmetics": len(cosmetics),
        "unnamed": sum(bool(UNNAMED.search(label)) for label in labels),
    }
    return FlagCatalog(
        stems,
        tuple(groups),
        tuple(tuple(x) for x in letters),
        tuple(sorted(cosmetics)),
        labels,
        report,
    )


def _stems_in(folder: Path) -> list[str]:
    """Return the ``.tga`` stems of one flag folder.

    Args:
        folder: ``gfx/flags`` or ``gfx/flags/medium``.

    Returns:
        Stems, unsorted; empty when the folder is missing.
    """
    if not folder.is_dir():
        return []
    return [p.stem for p in folder.iterdir() if p.suffix == ".tga"]


def _script_files(root: Path) -> Iterator[Path]:
    """Yield the ``.txt`` files of the scanned game script folders in sorted order.

    Args:
        root: Game installation folder.

    Yields:
        Script file paths.
    """
    for name in SCRIPT_DIRS:
        base = root / name
        if base.is_dir():
            for directory, _, files in sorted(os.walk(base)):
                for file in sorted(files):
                    if file.endswith(".txt"):
                        yield Path(directory) / file


def read_catalog(root: str) -> FlagCatalog:
    """Read the catalog from a HOI4 installation.

    Args:
        root: Game installation folder.

    Returns:
        The catalog (empty when the folder has no flags).
    """
    game = Path(root)
    tags: list[str] = []
    for path in sorted((game / "common" / "country_tags").glob("*.txt")):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = TAG.match(line)
            if match:
                tags.append(match[1])
    english: dict[str, str] = {}
    for path in sorted((game / "localisation" / "english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = LOC_LINE.match(line)
            if match:
                english.setdefault(match[1], match[2])
    cosmetic: set[str] = set()
    for path in _script_files(game):
        cosmetic.update(COSMETIC.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    return build_catalog(
        _stems_in(game / "gfx" / "flags"),
        _stems_in(game / "gfx" / "flags" / "medium"),
        tags,
        english,
        cosmetic,
    )


# ----------------------------------------------------------------------------- output


def gfx(catalog: FlagCatalog) -> str:
    """Return the sprite file: a large and a medium sprite per index.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_GFX`.
    """
    lines = [
        GEN_HEADER,
        "# Flag catalog sprites: GFX_rnf_<n> large (preview), GFX_rnfm_<n> medium (grid).\n",
        "# They point at the game's own files and load lazily (no legacy_lazy_load = no).\n",
        "spriteTypes = {\n",
    ]
    for n, stem in enumerate(catalog.stems, start=1):
        lines.append(
            f'\tspriteType = {{ name = "GFX_rnf_{n}" texturefile = "gfx/flags/{stem}.tga" }}\n'
        )
        lines.append(
            f'\tspriteType = {{ name = "GFX_rnfm_{n}" '
            f'texturefile = "gfx/flags/medium/{stem}.tga" }}\n'
        )
    lines.append("}\n")
    return "".join(lines)


def _dispatch(var: str, lo: int, hi: int, leaf: dict[int, str], indent: str) -> list[str]:
    """Return a binary ``if``/``else`` dispatch over ``var`` in ``lo..hi`` with the given leaves.

    Values without a leaf write nothing. The tree compares with ``<`` only, so a
    fraction or a value outside the range reaches no leaf or the nearest one; the
    callers pass whole indices that the effects have checked.

    Args:
        var: Variable compared, such as ``temp_var:rn_fp_w``.
        lo: First value.
        hi: Last value.
        leaf: Effect text of each value.
        indent: Indentation of the emitted lines.

    Returns:
        Lines.
    """
    if not any(lo <= k <= hi for k in leaf):
        return []
    if hi - lo + 1 <= WRITE_LEAF:
        return [f"{indent}if = {{ limit = {{ {check_variable(f'{var} = {lo}')} }} {leaf[lo]} }}\n"]
    mid = (lo + hi + 1) // 2
    left = _dispatch(var, lo, mid - 1, leaf, indent + "\t")
    right = _dispatch(var, mid, hi, leaf, indent + "\t")
    out = []
    if left:
        out += [f"{indent}if = {{\n{indent}\tlimit = {{ {check_variable(f'{var} < {mid}')} }}\n"]
        out += left
        out.append(f"{indent}}}\n")
    if right:
        keyword = "else" if left else "if"
        guard = "" if left else f"\n{indent}\tlimit = {{ {check_variable(f'{var} > {mid - 1}')} }}"
        out += [f"{indent}{keyword} = {{{guard}\n", *right, f"{indent}}}\n"]
    return out


def _write_leaf(stem: str, array: str, length: str) -> str:
    """Return the effect text that writes one packed stem.

    Args:
        stem: Stem.
        array: Array variable (``capie_cf_s`` or ``capie_cf_cos``).
        length: Length variable.

    Returns:
        One line of effects.
    """
    adds = " ".join(f"add_to_array = {{ {array} = {v} }}" for v in pack(stem))
    return f"clear_array = {array} {adds} set_variable = {{ {length} = {len(stem)} }}"


def _resolve_chain(catalog: FlagCatalog, keys: Iterable[str], trigger: str) -> list[str]:
    """Return one ``else_if`` per key: the game's ideology variant, else the bare key.

    Args:
        catalog: The catalog.
        keys: Cosmetic tags or tags, in output order.
        trigger: ``has_cosmetic_tag`` or ``original_tag``.

    Returns:
        Lines of the chain (the first one is an ``if``).
    """
    index = catalog.index
    out: list[str] = []
    for key in keys:
        variants = [(i, index[f"{key}_{i}"]) for i in IDEOLOGIES if f"{key}_{i}" in index]
        bare = index.get(key)
        if not variants and bare is None:
            continue
        parts = []
        for j, (ideology, n) in enumerate(variants):
            word = "if" if j == 0 else "else_if"
            parts.append(
                f"{word} = {{ limit = {{ has_government = {ideology} }} "
                f"set_temp_variable = {{ rn_fp_res = {n} }} }}"
            )
        if bare is not None:
            body = f"set_temp_variable = {{ rn_fp_res = {bare} }}"
            parts.append(f"else = {{ {body} }}" if variants else body)
        word = "if" if not out else "else_if"
        out.append(f"\t{word} = {{ limit = {{ {trigger} = {key} }} {' '.join(parts)} }}\n")
    return out


def _letter_fill(catalog: FlagCatalog) -> str:
    """Return ``rn_fp_fill_letter``: the countries of ``rn_fp_letter`` into ``rn_fp_list``.

    Args:
        catalog: The catalog.

    Returns:
        The effect.
    """
    out = [
        "# ROOT scope. Adds the countries of letter rn_fp_letter (1..26), sorted by English\n",
        "# name, to rn_fp_list. A tag scope works for countries that do not exist yet.\n",
        "rn_fp_fill_letter = {\n",
    ]
    first = True
    for n, tags in enumerate(catalog.letters, start=1):
        if not tags:
            continue
        adds = " ".join(
            f"{t} = {{ ROOT = {{ add_to_array = {{ rn_fp_list = PREV }} }} }}" for t in tags
        )
        word = "if" if first else "else_if"
        first = False
        out.append(
            f"\t{word} = {{ limit = {{ {check_variable(f'rn_fp_letter = {n}')} }} {adds} }}\n"
        )
    out.append("}\n\n")
    return "".join(out)


def effects(catalog: FlagCatalog) -> str:
    """Return the generated catalog effects.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_EFFECTS`.
    """
    n = len(catalog.stems)
    groups = len(catalog.groups)
    out = [
        GEN_HEADER,
        "# Flag catalog lookups for the flag picker (tools/modgen/features/flags.py).\n",
        (
            f"# Catalog: {n} flags, {groups - 1} country pools and the Other pool, "
            f"{len(catalog.cosmetics)} known cosmetic tags.\n\n"
        ),
        "# Constants: catalog size and fingerprint (rn_cf_cat on a country names the catalog its\n",
        "# rn_cf_idx belongs to; another fingerprint means the index is stale).\n",
        "rn_fp_catalog = {\n",
        f"\tset_temp_variable = {{ rn_fp_n = {n} }}\n",
        f"\tset_temp_variable = {{ rn_fp_cat = {fingerprint(catalog.stems)} }}\n",
        f"\tset_temp_variable = {{ rn_fp_other = {catalog.other_group} }}\n",
        "}\n\n",
        "# Country scope. Output temp rn_fp_g: pool group of the original tag, 0 = none.\n",
        "rn_fp_group_of = {\n\tset_temp_variable = { rn_fp_g = 0 }\n",
    ]
    for g, group in enumerate(catalog.groups[:-1], start=1):
        word = "if" if g == 1 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ original_tag = {group.tag} }} "
            f"set_temp_variable = {{ rn_fp_g = {g} }} }}\n"
        )
    out.append("}\n\n")
    leaves = {
        g: " ".join(f"add_to_array = {{ rn_fp_list = {i} }}" for i in group.indices)
        for g, group in enumerate(catalog.groups, start=1)
        if group.indices
    }
    out.append(
        "# ROOT scope. Input temp rn_fp_g (1..groups). Adds its catalog indices to rn_fp_list.\n"
    )
    out.append("rn_fp_fill_group = {\n")
    out += _dispatch("temp_var:rn_fp_g", 1, groups, leaves, "\t")
    out.append("}\n\n")
    out.append(_letter_fill(catalog))
    out.append(
        "# Country scope. Output temp rn_fp_res: the catalog index of the flag the game shows for\n"
        "# this country (cosmetic tag + ideology, cosmetic tag, original tag + ideology,\n"
        "# original tag; CONTRACT 17.1), 0 when no catalog file matches. A flag layer is not\n"
        "# looked at here.\n"
        "rn_fp_resolve_game = {\n\tset_temp_variable = { rn_fp_res = 0 }\n"
    )
    cosmetic_chain = _resolve_chain(catalog, catalog.cosmetics, "has_cosmetic_tag")
    out += cosmetic_chain
    out.append("\tif = {\n\t\tlimit = { check_variable = { temp_var:rn_fp_res = 0 } }\n")
    out += [
        "\t" + line
        for line in _resolve_chain(catalog, (g.tag for g in catalog.groups[:-1]), "original_tag")
    ]
    out.append("\t}\n}\n\n")
    stems = {
        i: _write_leaf(s, "capie_cf_s", "capie_cf_len")
        for i, s in enumerate(catalog.stems, start=1)
    }
    out.append(
        "# Country scope (the country whose flag changes). Input temp rn_fp_w (1..catalog size).\n"
        "# Writes capie_cf_s and capie_cf_len of that stem (CONTRACT 17.3); nothing otherwise.\n"
        "rn_fp_write_stem = {\n"
    )
    out += _dispatch("temp_var:rn_fp_w", 1, n, stems, "\t")
    out.append("}\n\n")
    out.append(
        "# Country scope. Writes the snapshot of the country's cosmetic tag (capie_cf_cos and\n"
        "# capie_cf_cos_len, CONTRACT 17.2) when it is a known one; otherwise removes the\n"
        '# snapshot, because script cannot tell "no cosmetic tag" from one it does not know.\n'
        "rn_fp_cos_write = {\n"
    )
    for i, cosmetic in enumerate(catalog.cosmetics):
        word = "if" if i == 0 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ has_cosmetic_tag = {cosmetic} }} "
            f"{_write_leaf(cosmetic, 'capie_cf_cos', 'capie_cf_cos_len')} }}\n"
        )
    out.append("\telse = { clear_array = capie_cf_cos clear_variable = capie_cf_cos_len }\n}\n\n")
    out.append(
        "# Country scope. Output temps rn_fp_cos_known (1 = the country has a known cosmetic tag)\n"
        "# and rn_fp_cos_same (1 = it is the one in the snapshot capie_cf_cos).\n"
        "rn_fp_cos_match = {\n"
        "\tset_temp_variable = { rn_fp_cos_known = 0 }\n"
        "\tset_temp_variable = { rn_fp_cos_same = 0 }\n"
    )
    for i, cosmetic in enumerate(catalog.cosmetics):
        word = "if" if i == 0 else "else_if"
        same = " ".join(
            [check_variable(f"capie_cf_cos_len = {len(cosmetic)}")]
            + [check_variable(f"capie_cf_cos^{j} = {v}") for j, v in enumerate(pack(cosmetic))]
        )
        out.append(
            f"\t{word} = {{ limit = {{ has_cosmetic_tag = {cosmetic} }} "
            f"set_temp_variable = {{ rn_fp_cos_known = 1 }} "
            f"if = {{ limit = {{ {same} }} set_temp_variable = {{ rn_fp_cos_same = 1 }} }} }}\n"
        )
    out.append("}\n")
    return "".join(out)


def scripted_loc(catalog: FlagCatalog) -> str:
    """Return the name of the selected flag and the flag cooldown's days left.

    Args:
        catalog: The catalog.

    Returns:
        Contents of :data:`CATALOG_SCRIPTED_LOC`.
    """
    n = len(catalog.stems)
    buckets = range((n + NAME_BUCKET - 1) // NAME_BUCKET)
    out = [
        GEN_HEADER,
        "# Name of the selected flag (ROOT.rn_fp_sel, catalog index): bucket, then index.\n",
        defined_text(
            "RN_FP_SEL_NAME",
            [
                (check_variable(f"rn_fp_sel < {(b + 1) * NAME_BUCKET}"), f"RN_FPB_{b}")
                for b in buckets
            ],
            EMPTY_KEY,
        ),
    ]
    for b in buckets:
        lo, hi = max(1, b * NAME_BUCKET), min(n, (b + 1) * NAME_BUCKET - 1)
        out.append(
            defined_text(
                f"RN_FP_SEL_NAME_{b}",
                [(check_variable(f"rn_fp_sel = {i}"), f"RN_FPL_{i}") for i in range(lo, hi + 1)],
                EMPTY_KEY,
            )
        )
    left = (
        "set_temp_variable = { rn_ip_cd_left = rn_ip_cd_flag_until } "
        "subtract_from_temp_variable = { rn_ip_cd_left = global.num_days }"
    )
    out.append("# Days left of the flag cooldown (scope: the country whose flag changes).\n")
    out.append(
        defined_text(
            "RN_IP_CD_LEFT_FLAG",
            [
                (f"{left} {check_variable(f'rn_ip_cd_left < {d + 1}')}", f"RN_IP_CD_DAYS_{d}")
                for d in range(1, 31)
            ],
            "RN_IP_CD_DAYS_MORE",
        )
    )
    return "".join(out)


def localisation(catalog: FlagCatalog, lang: str) -> str:
    """Return the label file of one language (identical text in every language).

    Args:
        catalog: The catalog.
        lang: Game language.

    Returns:
        The ``.yml`` text (the caller adds the BOM).
    """
    n = len(catalog.stems)
    lines = [f"l_{lang}:\n"]
    lines += [
        f' RN_FPB_{b}:0 "[ROOT.RN_FP_SEL_NAME_{b}]"\n'
        for b in range((n + NAME_BUCKET - 1) // NAME_BUCKET)
    ]
    lines += [f' RN_FPL_{i}:0 "{label}"\n' for i, label in enumerate(catalog.labels, start=1)]
    lines += [f' RN_FP_L_{c}:0 "{c}"\n RN_FP_L_{c}_ON:0 "§Y{c}§!"\n' for c in LETTERS]
    return "".join(lines)


def on_actions() -> str:
    """Return the daily flag checks.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE`.
    """
    return (
        GEN_HEADER
        + "# Daily: a country with a flag layer whose cosmetic tag changed loses the layer\n"
        "# (ADR-0032, CONTRACT 17.4; no cooldown, it is not a player's action), and an open\n"
        "# flag picker refreshes (dirty = rn_fp_dirty) so the cooldown days stay current.\n"
        "on_actions = {\n\ton_daily = {\n\t\teffect = {\n"
        "\t\t\tif = { limit = { has_variable = capie_cf_ver } rn_fp_daily_check = yes }\n"
        "\t\t\tif = { limit = { is_ai = no has_country_flag = rn_fp_open_own } "
        "add_to_variable = { rn_fp_dirty = 1 } }\n"
        "\t\t}\n\t}\n}\n"
    )


def write_files(catalog: FlagCatalog) -> list[tuple[str, str, bool]]:
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
        (f"localisation/{lang}/rn_flag_catalog_l_{lang}.yml", localisation(catalog, lang), True)
        for lang in LANGS
    ]
    return files
