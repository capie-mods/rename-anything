"""Shared parts of the generated pickers' catalogs (flags, portraits).

A catalog numbers the game's items (flag files, portrait sprites) as indices
``1..N``. The pickers write the chosen item into a CAPIE layer as packed
file-name characters (CONTRACT section 17.3, shared by section 18), dispatch
on an index with a generated binary tree, group the items by country tag, list
countries by the first letter of their English name (the same for every player
of a multiplayer game) and name the selected item through a two-level
scripted localisation lookup.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

from modgen.script import check_variable, defined_text

if TYPE_CHECKING:
    from collections.abc import Iterable


STEM = re.compile(r"[A-Za-z0-9_]{1,63}")
"""A flag stem or cosmetic tag CAPIE can carry (CONTRACT 17.3: 1..63 file-name characters)."""


TAG = re.compile(r"\s*([A-Z][A-Z0-9]{2})\s*=")
"""One ``TAG = "countries/..."`` line of ``common/country_tags``."""


LOC_LINE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*$')
"""One ``key:0 "text"`` localisation line."""


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


def first_letter(name: str, tag: str) -> int:
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


def english_name(tag: str, english: dict[str, str]) -> str:
    """Return the plain English name of a tag, or the tag when it is missing or scripted.

    Args:
        tag: Country tag.
        english: English localisation.

    Returns:
        The name used for sorting.
    """
    text = english.get(tag, "")
    return tag if not text or any(c in text for c in "[$§") else text


def dispatch(var: str, lo: int, hi: int, leaf: dict[int, str], indent: str) -> list[str]:
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
    left = dispatch(var, lo, mid - 1, leaf, indent + "\t")
    right = dispatch(var, mid, hi, leaf, indent + "\t")
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


def write_leaf(stem: str, array: str, length: str) -> str:
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


def read_tags(root: str) -> list[str]:
    """Return the country tags of ``common/country_tags``.

    Args:
        root: Game installation folder.

    Returns:
        Tags in file order.
    """
    tags: list[str] = []
    for path in sorted((Path(root) / "common" / "country_tags").glob("*.txt")):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = TAG.match(line)
            if match:
                tags.append(match[1])
    return tags


def read_english(root: str) -> dict[str, str]:
    """Return the English localisation (first definition of each key wins).

    Args:
        root: Game installation folder.

    Returns:
        Key to text.
    """
    english: dict[str, str] = {}
    for path in sorted((Path(root) / "localisation" / "english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = LOC_LINE.match(line)
            if match:
                english.setdefault(match[1], match[2])
    return english


def letters_of(tags: Iterable[str], english: dict[str, str]) -> tuple[tuple[str, ...], ...]:
    """Return the tags of each letter, sorted by English name.

    Args:
        tags: Country tags.
        english: English localisation.

    Returns:
        One tuple per letter of :data:`LETTERS`.
    """
    out: list[list[str]] = [[] for _ in LETTERS]
    for t in sorted(tags, key=lambda t: (english_name(t, english).casefold(), t)):
        out[first_letter(english_name(t, english), t) - 1].append(t)
    return tuple(tuple(x) for x in out)


def selected_name_loc(name: str, var: str, count: int, bucket_key: str, label_key: str) -> str:
    """Return a two-level name lookup: bucket of 64 indices, then the index.

    Args:
        name: Scripted localisation name (also the prefix of the bucket lookups).
        var: ROOT variable with the selected index.
        count: Catalog size.
        bucket_key: Localisation key prefix of a bucket (``<key><b>``).
        label_key: Localisation key prefix of a label (``<key><n>``).

    Returns:
        The ``defined_text`` blocks.
    """
    buckets = range((count + NAME_BUCKET - 1) // NAME_BUCKET)
    out = [
        defined_text(
            name,
            [
                (check_variable(f"{var} < {(b + 1) * NAME_BUCKET}"), f"{bucket_key}{b}")
                for b in buckets
            ],
            EMPTY_KEY,
        )
    ]
    for b in buckets:
        lo, hi = max(1, b * NAME_BUCKET), min(count, (b + 1) * NAME_BUCKET - 1)
        out.append(
            defined_text(
                f"{name}_{b}",
                [(check_variable(f"{var} = {i}"), f"{label_key}{i}") for i in range(lo, hi + 1)],
                EMPTY_KEY,
            )
        )
    return "".join(out)


def bucket_lines(name: str, count: int, bucket_key: str) -> list[str]:
    """Return the localisation lines of the buckets of :func:`selected_name_loc`.

    Args:
        name: Scripted localisation name.
        count: Catalog size.
        bucket_key: Localisation key prefix of a bucket.

    Returns:
        ``.yml`` lines.
    """
    return [
        f' {bucket_key}{b}:0 "[ROOT.{name}_{b}]"\n'
        for b in range((count + NAME_BUCKET - 1) // NAME_BUCKET)
    ]


def days_left_loc(name: str, until: str) -> str:
    """Return a cooldown's days left (1..30, then "more than 30").

    Args:
        name: Scripted localisation name.
        until: Variable with the expiry day (scope of the call).

    Returns:
        The ``defined_text`` block.
    """
    left = (
        f"set_temp_variable = {{ rn_ip_cd_left = {until} }} "
        "subtract_from_temp_variable = { rn_ip_cd_left = global.num_days }"
    )
    return defined_text(
        name,
        [
            (f"{left} {check_variable(f'rn_ip_cd_left < {d + 1}')}", f"RN_IP_CD_DAYS_{d}")
            for d in range(1, 31)
        ],
        "RN_IP_CD_DAYS_MORE",
    )
