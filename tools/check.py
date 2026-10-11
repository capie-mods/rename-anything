#!/usr/bin/env python3
"""Static cross-reference checks for the generated Rename Anything mod.

Run this after ``tools/gen.py``. It reads the files under ``mod/`` (the script
changes its working directory there) and, read-only, a few files from the HOI4
installation, then prints one line per problem followed by ``<n> findings``.
The exit code is 0 when nothing was found and 1 otherwise. If the game folder
has no ``history/states`` directory the script stops at once with an error
message on stderr and exit code 1.

The game folder is the first command-line argument, or the default Steam path
when no argument is given.

The checks run in this order, and their findings are printed in the same order:

* Localisation tables. Every ``localisation/<lang>/*.yml`` file is parsed with a
  simple ``KEY:N "value"`` line pattern. A key defined twice in one language is
  reported, and every language must have exactly the English key set. The
  ``*_chars_l_*`` tables (the character code table) must hold the same values in
  every language, because multiplayer clients with different languages must
  build identical strings. Nested ``$RN_...$`` references must resolve.
* Interface. Text, button and tooltip keys used in ``rename_anything.gui`` must
  exist in English. Sprites used by the GUI must be defined in the mod ``.gfx``
  or in a vanilla ``interface/*.gfx`` file, and every texture the mod ``.gfx``
  points at must exist.
* Scripted localisation. Every ``[ROOT.RN_...]`` reference in localisation, the
  GUI or the generated effects must have a ``defined_text``. Every
  ``localization_key`` in the scripted localisation file must exist in the
  mod's English tables or as a vanilla ``VICTORY_POINTS_<id>`` key.
* Typed state scope misuse. ``rn_sel_state`` holds a state scope, so comparing it
  inside ``check_variable`` is reported, as is assigning ``THIS.id`` to
  ``rn_sel_state_id``.
* State and victory point table. The ``rn_load_selected_state`` chain in the
  generated effects is compared with an inventory built from vanilla
  ``history/states``: one entry per state, the numeric ID equal to the state ID,
  consecutive VP slots matching the declared count, and the first five distinct
  VP provinces in file order. Missing, extra and wrong mappings are reported.
* Effects and GUI wiring. Every ``rn_... = yes`` call must name a defined effect
  or trigger. Every button must have a ``_click`` effect and every ``_click``
  effect a button. ``_visible`` and ``_click_enabled`` triggers and scripted GUI
  ``window_name`` values must name existing elements.
* Syntax shape. Curly braces must balance in every ``common/**/*.txt``,
  ``interface/*.gui`` and ``interface/*.gfx`` file (quoted strings and comments
  are ignored). Each localisation file must start with a UTF-8 BOM and the
  ``l_<lang>:`` header, and every other non-comment line must match the loc line
  format.

This is a static check built on regular expressions. It does not replace the
game's own parser, a save and load test, a check of scope evaluation at runtime
or a multiplayer test.

Usage::

    python tools/check.py ["C:/path/to/Hearts of Iron IV"]
"""

import glob
import os
import re
import sys
from pathlib import Path

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
"""Game folder used when no path is given on the command line."""

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mod")
"""Absolute path of the ``mod/`` folder; the script runs with this as its working directory."""

LOC_LINE = r' (\S+?):\d? "(.*)"\s*$'
"""Regex for one ``KEY:N "value"`` localisation line (key and value are captured)."""

UTF8_BOM = b"\xef\xbb\xbf"
"""Byte order mark every HOI4 localisation file must start with."""

MAX_VP_SLOTS = 5
"""Number of VP provinces per state that the generated table keeps."""

BAD_LOC_LINE_PREVIEW = 60
"""How many characters of a malformed loc line are shown in its finding."""


def rd(f: str) -> str:
    """Read a whole UTF-8 text file.

    Args:
        f: Path relative to the working directory (``mod/``) or absolute.

    Returns:
        The decoded file contents.
    """
    with Path(f).open(encoding="utf-8") as fh:
        return fh.read()


def english_loc() -> dict[str, str]:
    """Collect key/value pairs from the mod's English localisation files.

    Returns:
        Mapping of loc key to value; a later file wins when a key repeats.
    """
    loc: dict[str, str] = {}
    for f in glob.glob("localisation/english/*.yml"):
        with Path(f).open(encoding="utf-8-sig") as fh:
            for line in fh:
                m = re.match(LOC_LINE, line)
                if m:
                    loc[m.group(1)] = m.group(2)
    return loc


def locale_tables_check(
    loc: dict[str, str], bad: list[str]
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Parse every language's tables and check them against English.

    Args:
        loc: English key/value table from :func:`english_loc`.
        bad: Findings list; new findings are appended in place.

    Returns:
        The per-language full tables and the per-language character tables.
    """
    locale_tables: dict[str, dict[str, str]] = {}
    char_tables: dict[str, dict[str, str]] = {}
    for f in sorted(glob.glob("localisation/*/*.yml")):
        lang = os.path.basename(os.path.dirname(f))
        table = locale_tables.setdefault(lang, {})
        chars = char_tables.setdefault(lang, {})
        with Path(f).open(encoding="utf-8-sig") as fh:
            for line in fh:
                m = re.match(LOC_LINE, line)
                if m:
                    key, value = m.groups()
                    if key in table:
                        bad.append(f"duplicate loc key {lang}: {key}")
                    table[key] = value
                    if "_chars_l_" in os.path.basename(f):
                        chars[key] = value
    for lang, table in sorted(locale_tables.items()):
        bad += [f"missing loc key {lang}: {k}" for k in sorted(loc.keys() - table.keys())]
        bad += [f"unexpected loc key {lang}: {k}" for k in sorted(table.keys() - loc.keys())]
        reference = char_tables.get("english", {})
        bad += [
            f"language-dependent character table {lang}: {k}"
            for k in sorted(reference.keys() | char_tables[lang].keys())
            if reference.get(k) != char_tables[lang].get(k)
        ]
        dollar_refs = {
            key for value in table.values() for key in re.findall(r"\$(RN_[A-Za-z0-9_]+)\$", value)
        }
        bad += [
            f"missing nested loc key {lang}: {key}" for key in sorted(dollar_refs - table.keys())
        ]
    return locale_tables, char_tables


def interface_check(game: str, gui: str, loc: dict[str, str]) -> list[str]:
    """Check GUI loc keys, sprites and textures.

    Args:
        game: HOI4 installation folder.
        gui: Contents of ``interface/rename_anything.gui``.
        loc: English key/value table.

    Returns:
        Findings in the order they were detected.
    """
    bad: list[str] = []
    keys = set(re.findall(r'(?:buttonText|text|pdx_tooltip)\s*=\s*"([^"]+)"', gui))
    bad += [f"missing loc key {k}" for k in sorted(keys) if not k.startswith("[") and k not in loc]
    sprites = set(re.findall(r'(?:spriteType|quadTextureSprite)\s*=\s*"([^"]+)"', gui))
    gfx = rd("interface/rename_anything.gfx")
    vanilla_parts = []
    for f in glob.glob(os.path.join(game, "interface", "*.gfx")):
        with Path(f).open(encoding="utf-8", errors="replace") as fh:
            vanilla_parts.append(fh.read())
    van = "".join(vanilla_parts)
    bad += [
        f"missing sprite {s}"
        for s in sorted(sprites)
        if f'"{s}"' not in gfx and f'"{s}"' not in van
    ]
    bad += [
        f"missing texture {tex}"
        for tex in re.findall(r'texturefile = "([^"]+)"', gfx)
        if not os.path.exists(tex)
    ]
    return bad


def vanilla_vp_keys(game: str) -> set[str]:
    """Collect ``VICTORY_POINTS_<id>`` keys from the vanilla English localisation.

    Args:
        game: HOI4 installation folder.

    Returns:
        The set of key names found.
    """
    vk: set[str] = set()
    for f in glob.glob(os.path.join(game, "localisation", "english", "*.yml")):
        with Path(f).open(encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s*(VICTORY_POINTS_\d+):", line)
                if m:
                    vk.add(m.group(1))
    return vk


def state_inventory_check(game: str, bad: list[str]) -> dict[int, list[int]]:
    """Build the vanilla state to VP-province inventory.

    Args:
        game: HOI4 installation folder.
        bad: Findings list; files without an ID and duplicate IDs are appended.

    Returns:
        State ID mapped to its first five distinct VP provinces in file order.
    """
    state_inventory: dict[int, list[int]] = {}
    for f in sorted(glob.glob(os.path.join(game, "history", "states", "*.txt"))):
        with Path(f).open(encoding="utf-8-sig", errors="replace") as fh:
            history = re.sub(r"#[^\n]*", "", fh.read())
        state_match = re.search(r"\bid\s*=\s*(\d+)", history)
        if not state_match:
            bad.append(f"state history without ID: {f}")
            continue
        state_id = int(state_match.group(1))
        if state_id in state_inventory:
            bad.append(f"duplicate state ID in game inventory: {state_id}")
        provinces: list[int] = []
        for province_text in re.findall(r"victory_points\s*=\s*\{\s*(\d+)\s+[-\d.]+\s*\}", history):
            province = int(province_text)
            if province not in provinces:
                provinces.append(province)
        state_inventory[state_id] = provinces[:MAX_VP_SLOTS]
    return state_inventory


def generated_states_check(eff: str, bad: list[str]) -> dict[int, list[int]]:
    """Parse the generated ``rn_load_selected_state`` chain.

    Args:
        eff: Contents of the generated scripted effects file.
        bad: Findings list; duplicate, mismatched or inconsistent entries are appended.

    Returns:
        State ID mapped to the VP provinces the generated effect loads.
    """
    state_entries = re.findall(
        r"(?:if|else_if)\s*=\s*\{\s*limit\s*=\s*\{\s*state\s*=\s*(\d+)\s*\}\s*"
        r"ROOT\s*=\s*\{\s*set_variable\s*=\s*\{\s*rn_sel_state_id\s*=\s*(\d+)\s*\}\s*"
        r"set_variable\s*=\s*\{\s*rn_vp_cnt\s*=\s*(\d+)\s*\}"
        r"((?:\s*set_variable\s*=\s*\{\s*rn_vp_\d\s*=\s*\d+\s*\})*)\s*\}\s*\}",
        eff,
    )
    generated_states: dict[int, list[int]] = {}
    for state_text, numeric_text, count_text, slots in state_entries:
        state_id, numeric_id, count = int(state_text), int(numeric_text), int(count_text)
        if state_id in generated_states:
            bad.append(f"duplicate generated state mapping: {state_id}")
        if numeric_id != state_id:
            bad.append(f"state mapping {state_id} writes numeric ID {numeric_id}")
        vp_slots = [(int(k), int(p)) for k, p in re.findall(r"rn_vp_(\d)\s*=\s*(\d+)", slots)]
        if [k for k, _ in vp_slots] != list(range(count)):
            bad.append(f"state mapping {state_id} has inconsistent VP count/slots")
        generated_states[state_id] = [p for _, p in vp_slots]
    return generated_states


def brace_check() -> list[str]:
    """Report script, GUI and GFX files whose braces do not balance.

    Returns:
        One finding per unbalanced file.
    """
    bad: list[str] = []
    files = (
        glob.glob("common/**/*.txt", recursive=True)
        + glob.glob("interface/*.gui")
        + glob.glob("interface/*.gfx")
    )
    for f in files:
        t = re.sub(r"#[^\n]*", "", re.sub(r'"[^"\n]*"', '""', rd(f)))
        d = 0
        for ch in t:
            d += (ch == "{") - (ch == "}")
            if d < 0:
                break
        if d:
            bad.append(f"brace imbalance {f}")
    return bad


def loc_format_check() -> list[str]:
    """Check BOM, header and line format of every localisation file.

    Returns:
        Findings for files or lines that do not follow the format.
    """
    bad: list[str] = []
    for f in glob.glob("localisation/*/*.yml"):
        b = Path(f).read_bytes()
        lang = f.replace("\\", "/").split("_l_")[-1][:-4]
        if b[:3] != UTF8_BOM:
            bad.append(f"no BOM {f}")
        lines = b[3:].decode("utf-8").split("\n")
        if lines[0] != f"l_{lang}:":
            bad.append(f"bad header {f}")
        bad += [
            f"bad loc line {f}: {line[:BAD_LOC_LINE_PREVIEW]}"
            for line in lines[1:]
            if line.strip()
            and not line.strip().startswith("#")
            and not re.match(r'^ [A-Za-z0-9_.]+:\d? ".*"$', line)
        ]
    return bad


def main() -> None:
    """Run every check in order, print the findings and exit with 0 or 1."""
    game = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    os.chdir(MOD)
    bad: list[str] = []
    if not os.path.isdir(os.path.join(game, "history", "states")):
        sys.exit(f"game directory is missing history/states: {game}")
    gui = rd("interface/rename_anything.gui")
    loc = english_loc()
    locale_tables, _ = locale_tables_check(loc, bad)
    bad += interface_check(game, gui, loc)
    sl = rd("common/scripted_localisation/rename_anything_scripted_loc.txt")
    defs = set(re.findall(r"name = (\S+)", sl))
    eff = rd("common/scripted_effects/rename_anything_generated_effects.txt")
    refs = set()
    for v in [v for table in locale_tables.values() for v in table.values()] + [gui, eff]:
        refs |= set(re.findall(r"\[ROOT\.(RN_\w+)\]", v))
    bad += [f"undefined scripted loc {r}" for r in sorted(refs - defs)]
    vk = vanilla_vp_keys(game)
    bad += [
        f"missing loc for scripted loc key {k}"
        for k in sorted(set(re.findall(r"localization_key = (\S+)", sl)))
        if k not in loc and k not in vk
    ]
    allfx = rd("common/scripted_effects/rename_anything_effects.txt") + eff
    trig = rd("common/scripted_triggers/rename_anything_triggers.txt")
    fxdefs = set(re.findall(r"^(rn_\w+) = \{", allfx + trig, re.MULTILINE))
    sg = rd("common/scripted_guis/rename_anything_scripted_gui.txt")
    # rn_sel_state stores a typed state scope (PREV), not the numeric map ID.
    if any(
        re.search(r"\brn_sel_state\b", m.group(1))
        for m in re.finditer(r"check_variable\s*=\s*\{([^{}]*)\}", sg + allfx + sl)
    ):
        bad.append("typed rn_sel_state compared numerically; use rn_sel_state_id")
    if re.search(r"rn_sel_state_id\s*=\s*THIS\.id\b", allfx, re.IGNORECASE):
        bad.append("THIS.id is a typed scope, not the numeric rn_sel_state_id")
    # Check the generated state -> literal ID / VP table against the read-only game
    # inventory, including states without VPs. This checks data coverage, not runtime
    # scope evaluation; that still requires the Cities paths to be tested in game.
    state_inventory = state_inventory_check(game, bad)
    generated_states = generated_states_check(eff, bad)
    bad += [
        f"missing generated state mapping: {s}"
        for s in sorted(state_inventory.keys() - generated_states.keys())
    ]
    bad += [
        f"unexpected generated state mapping: {s}"
        for s in sorted(generated_states.keys() - state_inventory.keys())
    ]
    bad += [
        f"wrong VP mapping for state {s}: {generated_states[s]} != {state_inventory[s]}"
        for s in sorted(state_inventory.keys() & generated_states.keys())
        if generated_states[s] != state_inventory[s]
    ]
    used = set(re.findall(r"\b(rn_\w+) = yes", sg + allfx + sl))
    bad += [f"undefined effect/trigger {u}" for u in sorted(used - fxdefs)]
    btns = set(re.findall(r'buttonType = \{\s*name = "([^"]+)"', gui))
    clicks = set(re.findall(r"(\w+)_click = \{", sg))
    bad += [f"button without effect {b}" for b in sorted(btns - clicks)]
    bad += [f"effect without button {c}" for c in sorted(clicks - btns)]
    names = set(re.findall(r'name = "([^"]+)"', gui))
    bad += [
        f"trigger for unknown element {v}"
        for v in sorted(set(re.findall(r"(\w+)_visible = \{", sg)) - names)
    ]
    bad += [
        f"enabled trigger for unknown button {v}"
        for v in sorted(set(re.findall(r"(\w+)_click_enabled = \{", sg)) - btns)
    ]
    bad += [
        f"scripted GUI for unknown window {v}"
        for v in sorted(set(re.findall(r'window_name = "([^"]+)"', sg)) - names)
    ]
    bad += brace_check()
    bad += loc_format_check()
    for b_ in bad:
        print(b_)
    print(f"{len(bad)} findings")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
