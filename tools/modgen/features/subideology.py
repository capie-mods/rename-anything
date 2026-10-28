"""Ruling party sub-ideology name: the generated part (CAPIE API level 8, contract section 20).

The editor itself is hand-written (``tools/inline_editor``: ``rn_subideology*``).
CAPIE binds a name to the sub-ideology the country had at the commit, so the panel
shows the game's name again once the ruling party or its sub-ideology changes.
Rename Anything also removes the variables then, so a name never returns by
itself and the save stays tidy. Script cannot read the sub-ideology key, so the
generator lists the sub-ideologies of the game (``common/ideologies``) and the
script records which one was in power at Apply.

Generated files (relative to ``mod/``):

* ``common/scripted_effects/rn_subideology_catalog.txt``: ``rn_si_current``
  (country scope: temp ``rn_si_cur`` = number of the country leader's
  sub-ideology, 0 when it is none the game files define) and ``rn_si_catalog``
  (temp ``rn_si_cat``: fingerprint of the list, so a changed list never matches
  an old number).
* ``common/scripted_localisation/rn_subideology_catalog.txt``: the cooldown's
  days left.
* ``common/on_actions/rn_subideology_on_actions.txt``: the name lapses at a
  change of the ruling party, and daily when the sub-ideology changed.
"""

from __future__ import annotations

import re
from pathlib import Path

from modgen.common import GEN_HEADER
from modgen.features.catalog_common import days_left_loc, fingerprint

EFFECTS_FILE = "common/scripted_effects/rn_subideology_catalog.txt"
"""Generated effects, relative to ``mod/``."""

SCRIPTED_LOC_FILE = "common/scripted_localisation/rn_subideology_catalog.txt"
"""Generated scripted localisation, relative to ``mod/``."""

ON_ACTIONS_FILE = "common/on_actions/rn_subideology_on_actions.txt"
"""Lapse checks, relative to ``mod/``."""

_TOKEN = re.compile(r'"[^"]*"|[{}=]|[^\s{}="]+')
"""One token of a Paradox script file."""


def parse_types(text: str) -> list[str]:
    """Return the sub-ideologies (``types`` entries) of one ideology file.

    Args:
        text: File contents.

    Returns:
        Names in file order.
    """
    text = re.sub(r"#[^\n]*", "", text)
    tokens = _TOKEN.findall(text)
    out: list[str] = []
    depth = 0
    types_depth: int | None = None
    for i, tok in enumerate(tokens):
        if tok == "{":
            depth += 1
            if i >= 2 and tokens[i - 2] == "types" and tokens[i - 1] == "=":  # noqa: PLR2004
                types_depth = depth
            elif (
                types_depth is not None
                and depth == types_depth + 1
                and i >= 2  # noqa: PLR2004
                and tokens[i - 1] == "="
            ):
                out.append(tokens[i - 2])
        elif tok == "}":
            if types_depth is not None and depth == types_depth:
                types_depth = None
            depth -= 1
    return out


def read_types(root: str) -> tuple[str, ...]:
    """Return every sub-ideology of the game, sorted by name.

    Args:
        root: Game installation folder.

    Returns:
        Names, sorted and without duplicates.
    """
    names: set[str] = set()
    for path in sorted((Path(root) / "common" / "ideologies").glob("*.txt")):
        names.update(parse_types(path.read_text(encoding="utf-8-sig", errors="replace")))
    return tuple(sorted(names))


def effects(types: tuple[str, ...]) -> str:
    """Return the generated effects.

    Args:
        types: Sub-ideologies (:func:`read_types`).

    Returns:
        Contents of :data:`EFFECTS_FILE`.
    """
    out = [
        GEN_HEADER,
        f"# Sub-ideologies of the game (tools/modgen/features/subideology.py): {len(types)}.\n\n",
        "# Constant: fingerprint of the list (rn_sn_cat on a country names the list its\n",
        "# rn_sn_sub belongs to; another fingerprint means the number is stale).\n",
        f"rn_si_catalog = {{\n\tset_temp_variable = {{ rn_si_cat = {fingerprint(types)} }}\n}}\n\n",
        "# Country scope. Output temp rn_si_cur: number of the country leader's sub-ideology\n",
        "# (1..N in this list), 0 when the game files do not define it.\n",
        "rn_si_current = {\n\tset_temp_variable = { rn_si_cur = 0 }\n",
    ]
    for n, name in enumerate(types, start=1):
        word = "if" if n == 1 else "else_if"
        out.append(
            f"\t{word} = {{ limit = {{ has_country_leader_ideology = {name} }} "
            f"set_temp_variable = {{ rn_si_cur = {n} }} }}\n"
        )
    out.append("}\n")
    return "".join(out)


def scripted_loc() -> str:
    """Return the sub-ideology cooldown's days left.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    return (
        GEN_HEADER
        + "# Days left of the sub-ideology name cooldown (scope: the player's country).\n"
        + days_left_loc("RN_IP_CD_LEFT_SUBIDEO", "rn_ip_cd_subideo_until")
    )


def on_actions() -> str:
    """Return the lapse checks.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE`.
    """
    return (
        GEN_HEADER
        + "# The sub-ideology name lapses when the ruling party changes (election, coup,\n"
        "# set_politics) and, checked daily, when the ruling sub-ideology changes without a\n"
        "# party change (a new leader). CAPIE already shows the game's name then (CONTRACT\n"
        "# section 20); removing the variables keeps the name from coming back. No cooldown.\n"
        "on_actions = {\n"
        "\ton_ruling_party_change = {\n\t\teffect = {\n"
        "\t\t\tif = { limit = { has_variable = capie_sn_ver } "
        "rn_subideology_name_carrier_clear = yes }\n"
        "\t\t}\n\t}\n"
        "\ton_daily = {\n\t\teffect = {\n"
        "\t\t\tif = { limit = { has_variable = capie_sn_ver } rn_si_daily_check = yes }\n"
        "\t\t}\n\t}\n"
        "}\n"
    )


def write_files(types: tuple[str, ...]) -> list[tuple[str, str, bool]]:
    """Return every generated sub-ideology file.

    Args:
        types: Sub-ideologies (:func:`read_types`).

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    return [
        (EFFECTS_FILE, effects(types), False),
        (SCRIPTED_LOC_FILE, scripted_loc(), False),
        (ON_ACTIONS_FILE, on_actions(), False),
    ]
