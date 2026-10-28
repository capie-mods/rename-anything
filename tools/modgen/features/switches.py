"""Host switches: one on/off game rule for every feature of the mod (ADR-0036).

The host turns a feature off in the game rules; it stays off for the whole game
(the game fixes its rules at the start). A switched-off feature keeps its
buttons, pencils, tabs and diplomatic actions visible, greyed out, with a
tooltip line that says the host turned it off. Every effect that opens an
editor, applies or resets checks the same trigger again, so a forged command
changes nothing.

One trigger per feature is the only place that reads the rule:
``rn_feature_<id>_off``. Everything else (enabled triggers, effect guards,
tooltips, status lines) calls that trigger, so "switched off" can never be
confused with "no rights" or "cooldown", which have their own triggers.

Generated files (relative to ``mod/``):

* ``common/game_rules/rn_feature_rules.txt``: the rules, default on, with the
  descriptions on the options (a rule-level ``desc`` is a parser error);
* ``common/scripted_triggers/rn_feature_switches.txt``: ``rn_feature_<id>_off``;
* ``common/scripted_localisation/rn_feature_switches.txt``: ``RN_FEAT_<ID>``
  (a tooltip line, empty while the feature is on) and ``RN_FEAT_<ID>_LINE``
  (the same line without the leading line break, for a button whose whole
  tooltip it is);
* ``localisation/<lang>/rn_feature_switches_l_<lang>.yml``: rule texts, the
  tooltip lines, the status line and the diplomatic-action prerequisite.

The portrait switch exists before the portrait feature (ADR-0036), so a game
started now keeps its rule when the feature arrives.
"""

from __future__ import annotations

from typing import NamedTuple

from modgen.common import GEN_HEADER, LANGS, POLISH
from modgen.script import defined_text

RULES_FILE = "common/game_rules/rn_feature_rules.txt"
"""Game rules of the switches, relative to ``mod/``."""

TRIGGERS_FILE = "common/scripted_triggers/rn_feature_switches.txt"
"""Switch triggers, relative to ``mod/``."""

SCRIPTED_LOC_FILE = "common/scripted_localisation/rn_feature_switches.txt"
"""Tooltip lines, relative to ``mod/``."""

EMPTY_KEY = "RN_IPP_EMPTY"
"""Existing empty localisation key (in-place editor)."""

ERR_FEATURE_OFF = 21
"""Status code every editor uses for "the host turned this feature off"."""


class Feature(NamedTuple):
    """One switchable feature."""

    id: str
    """Rule and trigger id (``rn_feature_<id>``)."""

    english: str
    """English name in the rule list and in the tooltip line."""

    polish: str
    """Polish name."""


FEATURES = (
    Feature("country", "Country name and adjective", "Nazwa i przymiotnik państwa"),
    Feature("leader", "Leader name", "Imię przywódcy"),
    Feature("party", "Party names", "Nazwy partii"),
    Feature("subideology", "Ruling party sub-ideology name", "Nazwa ideologii partii rządzącej"),
    Feature("flag", "Country flag", "Flaga państwa"),
    Feature("colour", "Country map colour", "Kolor państwa na mapie"),
    Feature("portrait", "Leader portrait", "Portret przywódcy"),
    Feature("states", "State and city names", "Nazwy regionów i miast"),
    Feature("characters", "Other characters' names", "Imiona innych postaci"),
    Feature("factions", "Faction names", "Nazwy frakcji"),
    Feature("subjects", "Other countries (subjects)", "Inne państwa (podmioty)"),
)
"""Every switch, in rule order."""

TEXTS = {
    "on": ("On", "Włączone"),
    "off": ("Off", "Wyłączone"),
    "on_desc": ("Players can use this option.", "Gracze mogą korzystać z tej opcji."),
    "off_desc": (
        "The host has turned this option off. Its buttons stay visible but greyed out.",
        "Host wyłączył tę opcję. Jej przyciski są widoczne, ale wyszarzone.",
    ),
    "status": (
        "§RThe host has turned this off for this game. Nothing was changed.§!",
        "§RHost wyłączył tę opcję w tej grze. Nic nie zmieniono.§!",
    ),
}
"""Shared texts: English and Polish."""

PORTRAIT_NOTE = (
    " The portrait choice comes in a later version.",
    " Wybór portretu pojawi się w późniejszej wersji.",
)
"""Extra sentence of the portrait rule's descriptions."""


def trigger_name(feature: str) -> str:
    """Return the trigger that is true while a feature is switched off.

    Args:
        feature: Feature id.

    Returns:
        ``rn_feature_<id>_off``.
    """
    return f"rn_feature_{feature}_off"


def rules() -> str:
    """Return the game rules file.

    Returns:
        Contents of :data:`RULES_FILE`.
    """
    out = [
        GEN_HEADER,
        "# Host switches (ADR-0036): every feature can be turned off for a game. Default on.\n",
        "# Descriptions sit on the options; a rule-level desc is rejected by the parser.\n",
    ]
    for f in FEATURES:
        up = f.id.upper()
        out.append(
            f"rn_feature_{f.id} = {{\n"
            f'\tname = "RN_RULE_FEATURE_{up}"\n'
            '\tgroup = "RULE_GROUP_GAMEPLAY"\n'
            "\tdefault = {\n"
            f'\t\tname = "RN_FEATURE_{up}_ON"\n'
            '\t\ttext = "RN_RULE_FEATURE_ON"\n'
            f'\t\tdesc = "RN_RULE_FEATURE_{up}_ON_DESC"\n'
            "\t\tallow_achievements = yes\n"
            "\t}\n"
            "\toption = {\n"
            f'\t\tname = "RN_FEATURE_{up}_OFF"\n'
            '\t\ttext = "RN_RULE_FEATURE_OFF"\n'
            f'\t\tdesc = "RN_RULE_FEATURE_{up}_OFF_DESC"\n'
            "\t\tallow_achievements = yes\n"
            "\t}\n"
            "}\n"
        )
    return "".join(out)


def triggers() -> str:
    """Return the switch triggers.

    Returns:
        Contents of :data:`TRIGGERS_FILE`.
    """
    out = [
        GEN_HEADER,
        "# The only place that reads the host switches (ADR-0036). Any scope: rules are global.\n",
    ]
    for f in FEATURES:
        up = f.id.upper()
        out.append(
            f"{trigger_name(f.id)} = {{\n"
            f"\thas_game_rule = {{ rule = rn_feature_{f.id} option = RN_FEATURE_{up}_OFF }}\n"
            "}\n"
        )
    return "".join(out)


def scripted_loc() -> str:
    """Return the tooltip lines.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    out = [GEN_HEADER, "# Tooltip lines of the host switches; empty while a feature is on.\n"]
    for f in FEATURES:
        up = f.id.upper()
        off = [(f"{trigger_name(f.id)} = yes", f"RN_FEAT_{up}_OFF")]
        out.append(defined_text(f"RN_FEAT_{up}", off, EMPTY_KEY))
        line = [(f"{trigger_name(f.id)} = yes", f"RN_FEAT_{up}_OFF_LINE")]
        out.append(defined_text(f"RN_FEAT_{up}_LINE", line, EMPTY_KEY))
    return "".join(out)


def localisation(lang: str) -> str:
    """Return the switch texts of one language (Polish, or English for every other one).

    Args:
        lang: Game language.

    Returns:
        The ``.yml`` text without the BOM.
    """
    pl = 1 if lang == POLISH else 0
    lines = [
        f"l_{lang}:\n",
        f' RN_RULE_FEATURE_ON:0 "{TEXTS["on"][pl]}"\n',
        f' RN_RULE_FEATURE_OFF:0 "{TEXTS["off"][pl]}"\n',
        f' RN_FEATURE_OFF_STATUS:0 "{TEXTS["status"][pl]}"\n',
    ]
    for f in FEATURES:
        up = f.id.upper()
        name = (f.english, f.polish)[pl]
        note = PORTRAIT_NOTE[pl] if f.id == "portrait" else ""
        off_line = (
            f"{name}: the host has turned this off for this game.",
            f"{name}: host wyłączył tę opcję w tej grze.",
        )[pl]
        allowed = (f"{name}: allowed by the host", f"{name}: dozwolone przez hosta")[pl]
        lines += [
            f' RN_RULE_FEATURE_{up}:0 "Rename Anything: {name}"\n',
            f' RN_RULE_FEATURE_{up}_ON_DESC:0 "{TEXTS["on_desc"][pl]}{note}"\n',
            f' RN_RULE_FEATURE_{up}_OFF_DESC:0 "{TEXTS["off_desc"][pl]}{note}"\n',
            f' RN_FEAT_{up}_OFF:0 "\\n§R{off_line}§!"\n',
            f' RN_FEAT_{up}_OFF_LINE:0 "§R{off_line}§!"\n',
            f' RN_FEAT_{up}_TT:0 "[ROOT.RN_FEAT_{up}_LINE]"\n',
            f' RN_FEAT_{up}_ALLOWED:0 "{allowed}"\n',
        ]
    return "".join(lines)


def write_files() -> list[tuple[str, str, bool]]:
    """Return every switch file.

    Returns:
        ``(path relative to mod/, text, needs BOM)`` per file.
    """
    files = [
        (RULES_FILE, rules(), False),
        (TRIGGERS_FILE, triggers(), False),
        (SCRIPTED_LOC_FILE, scripted_loc(), False),
    ]
    files += [
        (f"localisation/{lang}/rn_feature_switches_l_{lang}.yml", localisation(lang), True)
        for lang in LANGS
    ]
    return files
