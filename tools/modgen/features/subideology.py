"""Ruling party ideology name: the generated part (CAPIE API level 8, contract section 20).

CAPIE calls it the sub-ideology name layer (``capie_sn_*``); it renames the
ideology line of the ruling-party box in the politics panel. The editor itself is
hand-written (``tools/inline_editor``: ``rn_subideology*``). CAPIE binds a name to
the ruling party and its leader at the commit and shows the game's name again
once either changes; Rename Anything then removes the variables too (CONTRACT
20.3), so a save never keeps a name of an earlier government.

Generated files (relative to ``mod/``):

* ``common/scripted_localisation/rn_subideology_catalog.txt``: the cooldown's
  days left.
* ``common/on_actions/rn_subideology_on_actions.txt``: the name lapses at a
  change of the ruling party or the government, and daily when the country
  leader is another one than at Apply.
"""

from __future__ import annotations

from modgen.common import GEN_HEADER
from modgen.features.catalog_common import days_left_loc

SCRIPTED_LOC_FILE = "common/scripted_localisation/rn_subideology_catalog.txt"
"""Generated scripted localisation, relative to ``mod/``."""

ON_ACTIONS_FILE = "common/on_actions/rn_subideology_on_actions.txt"
"""Lapse checks, relative to ``mod/``."""

LAPSE_ACTIONS = ("on_ruling_party_change", "on_government_change")
"""On actions after which the name is removed (CONTRACT 20.3)."""


def scripted_loc() -> str:
    """Return the cooldown's days left.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    return (
        GEN_HEADER
        + "# Days left of the party ideology name cooldown (scope: the player's country).\n"
        + days_left_loc("RN_IP_CD_LEFT_SUBIDEO", "rn_ip_cd_subideo_until")
    )


def on_actions() -> str:
    """Return the lapse checks.

    Returns:
        Contents of :data:`ON_ACTIONS_FILE`.
    """
    lapse = "".join(
        f"\t{action} = {{\n\t\teffect = {{\n"
        "\t\t\tif = { limit = { has_variable = capie_sn_ver } "
        "rn_subideology_name_carrier_clear = yes }\n"
        "\t\t}\n\t}\n"
        for action in LAPSE_ACTIONS
    )
    return (
        GEN_HEADER
        + "# The party ideology name lapses when the ruling party or the government changes\n"
        "# (election, coup, set_politics) and, checked daily, when the country leader is not\n"
        "# the one at Apply (a new leader is how the sub-ideology changes). CAPIE already shows\n"
        "# the game's name then (CONTRACT 20.3); removing the variables keeps the save\n"
        "# consistent. No cooldown: it is not a player's action.\n"
        "on_actions = {\n" + lapse + "\ton_daily = {\n\t\teffect = {\n"
        "\t\t\tif = { limit = { has_variable = capie_sn_ver } rn_si_daily_check = yes }\n"
        "\t\t}\n\t}\n"
        "}\n"
    )


def write_files() -> list[tuple[str, str, bool]]:
    """Return every generated party ideology name file.

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    return [
        (SCRIPTED_LOC_FILE, scripted_loc(), False),
        (ON_ACTIONS_FILE, on_actions(), False),
    ]
