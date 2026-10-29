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
  GUI or the generated effects must have a ``defined_text`` in one of the
  ``common/scripted_localisation`` files (legacy tables, cooldown tooltips and
  the in-place editor carriers). Every ``localization_key`` in those files must
  exist in the mod's English tables or as a vanilla ``VICTORY_POINTS_<id>`` key.
* Layer writers. Only the colour carrier (and the cosmetic snapshot it calls,
  generated in ``rn_colour_catalog.txt``) writes ``capie_cc_*`` (CONTRACT 19), and only
  the party ideology carrier writes ``capie_sn_*`` (CONTRACT 20).
* Typed state scope misuse. ``rn_sel_state`` holds a state scope, so comparing it
  inside ``check_variable`` is reported, as is assigning ``THIS.id`` to
  ``rn_sel_state_id``.
* State and victory point table. The ``rn_load_selected_state`` chain in the
  generated effects is compared with an inventory built from vanilla
  ``history/states``: one entry per state, the numeric ID equal to the state ID,
  consecutive VP slots matching the declared count, and the first five distinct
  VP provinces in file order. Missing, extra and wrong mappings are reported.
* Effects and GUI wiring. Every ``rn_... = yes`` call must name an effect or
  trigger defined in any ``common/scripted_effects`` or
  ``common/scripted_triggers`` file. Every button must have a ``_click`` effect and every ``_click``
  effect a button. ``_visible`` and ``_click_enabled`` triggers and scripted GUI
  ``window_name`` values must name existing elements.
* Syntax shape. Curly braces must balance in every ``common/**/*.txt``,
  ``interface/*.gui`` and ``interface/*.gfx`` file (quoted strings and comments
  are ignored). Each localisation file must start with a UTF-8 BOM and the
  ``l_<lang>:`` header, and every other non-comment line must match the loc line
  format.

The vanilla state inventory is read with the same parser the generator uses
(``rncommon.game_data``); the check therefore verifies that the generated chain
matches the parsed inventory, not that the parsing rules themselves are right.

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

from rncommon.game_data import (
    DEFAULT_GAME,
    HAS_DLC_NAMES,
    GameData,
    GameInstallation,
    read_state_inventory,
    vp_key_ids,
)
from rncommon.loc_files import UTF8_BOM, loc_entries

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mod")
"""Absolute path of the ``mod/`` folder; the script runs with this as its working directory."""

GUI_FILE = "interface/rename_anything.gui"
"""Legacy editor layout, relative to ``mod/``."""

GFX_FILE = "interface/rename_anything.gfx"
"""Legacy editor sprites, relative to ``mod/``."""

GENERATED_EFFECTS_FILE = "common/scripted_effects/rename_anything_generated_effects.txt"
"""Generated effects holding ``rn_load_selected_state``, relative to ``mod/``."""

SCRIPTED_GUI_FILE = "common/scripted_guis/rename_anything_scripted_gui.txt"
"""Legacy editor scripted GUIs, relative to ``mod/``."""

BAD_LOC_LINE_PREVIEW = 60
"""How many characters of a malformed loc line are shown in its finding."""

LOC_SUFFIX = ".yml"
"""File extension of localisation files; cut off the file name to get the language."""

CHARS_TABLE_MARKER = "_chars_l_"
"""File name part of the language-independent character tables."""

REFERENCE_LANGUAGE = "english"
"""Language whose key set and character table every other language must match."""

NESTED_LOC_REF = re.compile(r"\$(RN_[A-Za-z0-9_]+)\$")
"""A nested ``$RN_...$`` localisation reference."""

GUI_TEXT_KEY = re.compile(r'(?:buttonText|text|pdx_tooltip)\s*=\s*"([^"]+)"')
"""A text, button caption or tooltip key in a ``.gui`` file."""

GUI_SPRITE = re.compile(r'(?:spriteType|quadTextureSprite)\s*=\s*"([^"]+)"')
"""A sprite reference in a ``.gui`` file."""

GFX_TEXTURE = re.compile(r'texturefile = "([^"]+)"')
"""A texture path in a ``.gfx`` file."""

ROOT_SCRIPTED_LOC = re.compile(r"\[ROOT\.(RN_\w+)\]")
"""A ``[ROOT.RN_...]`` scripted localisation call."""

DEFINED_TEXT_NAME = re.compile(r"name = (\S+)")
"""The name of a ``defined_text`` block."""

LOCALIZATION_KEY = re.compile(r"localization_key = (\S+)")
"""A ``localization_key`` inside a ``defined_text`` block."""

TOP_LEVEL_RN_DEFINITION = re.compile(r"^(rn_\w+) = \{", re.MULTILINE)
"""A top-level ``rn_*`` effect or trigger definition."""

CHECK_VARIABLE_BODY = re.compile(r"check_variable\s*=\s*\{([^{}]*)\}")
"""The body of a one-level ``check_variable`` block."""

SEL_STATE_VARIABLE = re.compile(r"\brn_sel_state\b")
"""The typed ``rn_sel_state`` scope variable."""

THIS_ID_ASSIGNMENT = re.compile(r"rn_sel_state_id\s*=\s*THIS\.id\b", re.IGNORECASE)
"""Assignment of the typed ``THIS.id`` to the numeric state ID."""

STATE_MAPPING = re.compile(
    r"(?:if|else_if)\s*=\s*\{\s*limit\s*=\s*\{\s*state\s*=\s*(\d+)\s*\}\s*"
    r"ROOT\s*=\s*\{\s*set_variable\s*=\s*\{\s*rn_sel_state_id\s*=\s*(\d+)\s*\}\s*"
    r"set_variable\s*=\s*\{\s*rn_vp_cnt\s*=\s*(\d+)\s*\}"
    r"((?:\s*set_variable\s*=\s*\{\s*rn_vp_\d\s*=\s*\d+\s*\})*)\s*\}\s*\}"
)
"""One branch of ``rn_load_selected_state``: state, numeric ID, VP count and VP slots."""

VP_SLOT_ASSIGNMENT = re.compile(r"rn_vp_(\d)\s*=\s*(\d+)")
"""One ``rn_vp_<slot> = <province>`` assignment inside a state mapping."""

YES_CALL = re.compile(r"\b(rn_\w+) = yes")
"""A call of an ``rn_*`` effect or trigger."""

GUI_BUTTON_NAME = re.compile(r'buttonType = \{\s*name = "([^"]+)"')
"""The name of a ``buttonType`` element."""

GUI_ELEMENT_NAME = re.compile(r'name = "([^"]+)"')
"""The name of any ``.gui`` element."""

CLICK_EFFECT = re.compile(r"(\w+)_click = \{")
"""A scripted GUI ``<element>_click`` effect."""

VISIBLE_TRIGGER = re.compile(r"(\w+)_visible = \{")
"""A scripted GUI ``<element>_visible`` trigger."""

ENABLED_TRIGGER = re.compile(r"(\w+)_click_enabled = \{")
"""A scripted GUI ``<element>_click_enabled`` trigger."""

WINDOW_NAME = re.compile(r'window_name = "([^"]+)"')
"""The window a scripted GUI belongs to."""

QUOTED = re.compile(r'"[^"\n]*"')
"""A quoted string on one line (braces inside it do not count)."""

COMMENT = re.compile(r"#[^\n]*")
"""A ``#`` comment up to the end of its line."""

LOC_FORMAT_LINE = re.compile(r'^ [A-Za-z0-9_.]+:\d? ".*"$')
"""A well-formed localisation entry line (without line ending)."""


def rd(f: str) -> str:
    """Read a whole UTF-8 text file.

    Args:
        f: Path relative to the working directory (``mod/``) or absolute.

    Returns:
        The decoded file contents.
    """
    with Path(f).open(encoding="utf-8") as fh:
        return fh.read()


def read_joined(pattern: str) -> str:
    """Read and concatenate every file matching a glob pattern, in sorted order.

    Args:
        pattern: Glob pattern relative to ``mod/``.

    Returns:
        The concatenated contents.
    """
    return "".join(rd(f) for f in sorted(glob.glob(pattern)))


def english_loc() -> dict[str, str]:
    """Collect key/value pairs from the mod's English localisation files.

    Returns:
        Mapping of loc key to value; a later file wins when a key repeats.
    """
    loc: dict[str, str] = {}
    for f in glob.glob(f"localisation/{REFERENCE_LANGUAGE}/*.yml"):
        loc.update(loc_entries(f))
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
        for key, value in loc_entries(f):
            if key in table:
                bad.append(f"duplicate loc key {lang}: {key}")
            table[key] = value
            if CHARS_TABLE_MARKER in os.path.basename(f):
                chars[key] = value
    for lang, table in sorted(locale_tables.items()):
        bad += [f"missing loc key {lang}: {k}" for k in sorted(loc.keys() - table.keys())]
        bad += [f"unexpected loc key {lang}: {k}" for k in sorted(table.keys() - loc.keys())]
        reference = char_tables.get(REFERENCE_LANGUAGE, {})
        bad += [
            f"language-dependent character table {lang}: {k}"
            for k in sorted(reference.keys() | char_tables[lang].keys())
            if reference.get(k) != char_tables[lang].get(k)
        ]
        dollar_refs = {key for value in table.values() for key in NESTED_LOC_REF.findall(value)}
        bad += [
            f"missing nested loc key {lang}: {key}" for key in sorted(dollar_refs - table.keys())
        ]
    return locale_tables, char_tables


def interface_check(game: GameData, gui: str, loc: dict[str, str]) -> list[str]:
    """Check GUI loc keys, sprites and textures.

    Args:
        game: Vanilla installation (for its sprite definitions).
        gui: Contents of ``interface/rename_anything.gui``.
        loc: English key/value table.

    Returns:
        Findings in the order they were detected.
    """
    bad: list[str] = []
    keys = set(GUI_TEXT_KEY.findall(gui))
    bad += [f"missing loc key {k}" for k in sorted(keys) if not k.startswith("[") and k not in loc]
    sprites = set(GUI_SPRITE.findall(gui))
    gfx = rd(GFX_FILE)
    # Sprites may come from any generated .gfx of the mod (catalogs, mini portraits); their
    # textures are game files, so only rename_anything.gfx gets the texture check below.
    mod_gfx = "".join(rd(f"interface/{p.name}") for p in sorted(Path("interface").glob("*.gfx")))
    van = game.interface_sprites_text()
    bad += [
        f"missing sprite {s}"
        for s in sorted(sprites)
        if f'"{s}"' not in mod_gfx and f'"{s}"' not in van
    ]
    bad += [f"missing texture {tex}" for tex in GFX_TEXTURE.findall(gfx) if not os.path.exists(tex)]
    # Generated catalogs (flags, portraits, mini portraits) point at game files: a texture must
    # exist in the mod, in the game or in one of its DLC folders (a cut path was a real bug).
    root = getattr(game, "root", None)
    if root:
        bases = [
            Path(),
            Path(root),
            *sorted(Path(root, "dlc").glob("*")),
            *sorted(Path(root, "integrated_dlc").glob("*")),
        ]
        seen: set[str] = set()
        for name in sorted(
            p.name for p in Path("interface").glob("*.gfx") if p.name != Path(GFX_FILE).name
        ):
            for tex in GFX_TEXTURE.findall(rd(f"interface/{name}")):
                if tex in seen:
                    continue
                seen.add(tex)
                if not any((base / tex).exists() for base in bases):
                    bad.append(f"missing texture {tex} ({name})")
    return bad


def scripted_loc_check(
    game: GameData,
    locale_tables: dict[str, dict[str, str]],
    loc: dict[str, str],
    sources: tuple[str, str, str],
) -> list[str]:
    """Check that scripted loc calls are defined and its keys exist.

    Args:
        game: Vanilla installation (for ``VICTORY_POINTS_<id>`` keys).
        locale_tables: Every language's table from :func:`locale_tables_check`.
        loc: English key/value table.
        sources: The concatenated scripted localisation files, the GUI and the
            generated effects.

    Returns:
        Findings in the order they were detected.
    """
    sl, gui, eff = sources
    defs = set(DEFINED_TEXT_NAME.findall(sl))
    refs: set[str] = set()
    for v in [v for table in locale_tables.values() for v in table.values()] + [gui, eff]:
        refs |= set(ROOT_SCRIPTED_LOC.findall(v))
    bad = [f"undefined scripted loc {r}" for r in sorted(refs - defs)]
    vk = {f"VICTORY_POINTS_{i}" for i in vp_key_ids(game.english_localisation_lines())}
    bad += [
        f"missing loc for scripted loc key {k}"
        for k in sorted(set(LOCALIZATION_KEY.findall(sl)))
        if k not in loc and k not in vk
    ]
    return bad


def has_dlc_check() -> list[str]:
    """Return every ``has_dlc`` value in the mod that the game does not accept.

    Returns:
        One problem per unknown name (see :data:`rncommon.game_data.HAS_DLC_NAMES`).
    """
    names: set[str] = set()
    for path in sorted(Path().rglob("*.txt")):
        names.update(HAS_DLC.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    return [f"has_dlc name the game does not know: {n!r}" for n in sorted(names - HAS_DLC_NAMES)]


HAS_DLC = re.compile(r'has_dlc\s*=\s*"([^"]*)"')
"""A quoted ``has_dlc`` value."""


LAYER_WRITE = re.compile(
    r"\b(?:set_variable|clear_variable|clear_array|add_to_array|remove_from_array|"
    r"add_to_variable|subtract_from_variable|multiply_variable|divide_variable|"
    r"modulo_variable|round_variable|clamp_variable)\s*=\s*\{?\s*(?:var\s*=\s*)?"
    r"(capie_(?:cc|sn)_\w+)"
)
"""A statement that writes a variable or array of the colour or party ideology layer."""

LAYER_WRITERS = {
    "capie_cc_": {
        "common/scripted_effects/rn_country_colour_carrier.txt",
        "common/scripted_effects/rn_colour_catalog.txt",
    },
    "capie_sn_": {"common/scripted_effects/rn_subideology_name_carrier.txt"},
}
"""Variable prefix to the only files that may write it."""


def layer_writer_check() -> list[str]:
    """Return every write of a ``capie_cc_*`` or ``capie_sn_*`` variable outside its carrier.

    Returns:
        One problem per file and variable.
    """
    bad: list[str] = []
    for path in sorted(Path("common").rglob("*.txt")):
        rel = path.as_posix()
        text = COMMENT.sub("", path.read_text(encoding="utf-8-sig", errors="replace"))
        for name in sorted(set(LAYER_WRITE.findall(text))):
            allowed = next(v for k, v in LAYER_WRITERS.items() if name.startswith(k))
            if rel not in allowed:
                bad.append(f"{rel}: writes {name} outside its carrier")
    return bad


def typed_scope_check(scripts: str, effects: str) -> list[str]:
    """Report numeric use of the typed ``rn_sel_state`` scope.

    Args:
        scripts: Scripted GUIs, effects and scripted localisation, concatenated.
        effects: Every scripted effect file, concatenated.

    Returns:
        Findings in the order they were detected.
    """
    bad = []
    # rn_sel_state stores a typed state scope (PREV), not the numeric map ID.
    if any(SEL_STATE_VARIABLE.search(m.group(1)) for m in CHECK_VARIABLE_BODY.finditer(scripts)):
        bad.append("typed rn_sel_state compared numerically; use rn_sel_state_id")
    if THIS_ID_ASSIGNMENT.search(effects):
        bad.append("THIS.id is a typed scope, not the numeric rn_sel_state_id")
    return bad


def state_inventory_check(game: GameData, bad: list[str]) -> dict[int, list[int]]:
    """Build the vanilla state to VP-province inventory.

    Args:
        game: Vanilla installation.
        bad: Findings list; files without an ID and duplicate IDs are appended.

    Returns:
        State ID mapped to its first five distinct VP provinces in file order.
    """
    inventory = read_state_inventory(game.state_histories())
    for issue in inventory.issues:
        if issue.kind == "missing_id":
            bad.append(f"state history without ID: {issue.detail}")
        else:
            bad.append(f"duplicate state ID in game inventory: {issue.detail}")
    return inventory.states


def generated_states_check(eff: str, bad: list[str]) -> dict[int, list[int]]:
    """Parse the generated ``rn_load_selected_state`` chain.

    Args:
        eff: Contents of the generated scripted effects file.
        bad: Findings list; duplicate, mismatched or inconsistent entries are appended.

    Returns:
        State ID mapped to the VP provinces the generated effect loads.
    """
    generated_states: dict[int, list[int]] = {}
    for state_text, numeric_text, count_text, slots in STATE_MAPPING.findall(eff):
        state_id, numeric_id, count = int(state_text), int(numeric_text), int(count_text)
        if state_id in generated_states:
            bad.append(f"duplicate generated state mapping: {state_id}")
        if numeric_id != state_id:
            bad.append(f"state mapping {state_id} writes numeric ID {numeric_id}")
        vp_slots = [(int(k), int(p)) for k, p in VP_SLOT_ASSIGNMENT.findall(slots)]
        if [k for k, _ in vp_slots] != list(range(count)):
            bad.append(f"state mapping {state_id} has inconsistent VP count/slots")
        generated_states[state_id] = [p for _, p in vp_slots]
    return generated_states


def state_table_check(game: GameData, eff: str, bad: list[str]) -> None:
    """Compare the generated state to literal ID / VP table with the game inventory.

    This includes states without VPs. It checks data coverage, not runtime scope
    evaluation; the Cities paths still need an in-game test.

    Args:
        game: Vanilla installation.
        eff: Contents of the generated scripted effects file.
        bad: Findings list; findings are appended in place.
    """
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


def wiring_check(gui: str, sg: str, scripts: str, definitions: str) -> list[str]:
    """Check effect calls and the wiring between buttons, effects and triggers.

    Args:
        gui: Contents of ``interface/rename_anything.gui``.
        sg: Contents of the legacy scripted GUI file.
        scripts: Scripted GUIs, effects and scripted localisation, concatenated.
        definitions: Every scripted effect and trigger file, concatenated.

    Returns:
        Findings in the order they were detected.
    """
    fxdefs = set(TOP_LEVEL_RN_DEFINITION.findall(definitions))
    used = set(YES_CALL.findall(scripts))
    bad = [f"undefined effect/trigger {u}" for u in sorted(used - fxdefs)]
    btns = set(GUI_BUTTON_NAME.findall(gui))
    clicks = set(CLICK_EFFECT.findall(sg))
    bad += [f"button without effect {b}" for b in sorted(btns - clicks)]
    bad += [f"effect without button {c}" for c in sorted(clicks - btns)]
    names = set(GUI_ELEMENT_NAME.findall(gui))
    bad += [
        f"trigger for unknown element {v}" for v in sorted(set(VISIBLE_TRIGGER.findall(sg)) - names)
    ]
    bad += [
        f"enabled trigger for unknown button {v}"
        for v in sorted(set(ENABLED_TRIGGER.findall(sg)) - btns)
    ]
    bad += [
        f"scripted GUI for unknown window {v}" for v in sorted(set(WINDOW_NAME.findall(sg)) - names)
    ]
    return bad


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
        t = COMMENT.sub("", QUOTED.sub('""', rd(f)))
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
        lang = f.replace("\\", "/").split("_l_")[-1][: -len(LOC_SUFFIX)]
        if b[: len(UTF8_BOM)] != UTF8_BOM:
            bad.append(f"no BOM {f}")
        lines = b[len(UTF8_BOM) :].decode("utf-8").split("\n")
        if lines[0] != f"l_{lang}:":
            bad.append(f"bad header {f}")
        bad += [
            f"bad loc line {f}: {line[:BAD_LOC_LINE_PREVIEW]}"
            for line in lines[1:]
            if line.strip() and not line.strip().startswith("#") and not LOC_FORMAT_LINE.match(line)
        ]
    return bad


def run_checks(game: GameData) -> list[str]:
    """Run every check in order on the current working directory (``mod/``).

    Args:
        game: Vanilla installation.

    Returns:
        Every finding, in check order.
    """
    bad: list[str] = []
    gui = rd(GUI_FILE)
    loc = english_loc()
    locale_tables, _ = locale_tables_check(loc, bad)
    bad += interface_check(game, gui, loc)
    # Every scripted localisation, effect and trigger file counts: the generator also writes
    # the in-place editor (rn_inline_*) and the cooldown triggers next to the legacy files.
    sl = read_joined("common/scripted_localisation/*.txt")
    eff = rd(GENERATED_EFFECTS_FILE)
    bad += scripted_loc_check(game, locale_tables, loc, (sl, gui, eff))
    allfx = read_joined("common/scripted_effects/*.txt")
    trig = read_joined("common/scripted_triggers/*.txt")
    sg = rd(SCRIPTED_GUI_FILE)
    bad += typed_scope_check(sg + allfx + sl, allfx)
    bad += has_dlc_check()
    bad += layer_writer_check()
    state_table_check(game, eff, bad)
    bad += wiring_check(gui, sg, sg + allfx + sl, allfx + trig)
    bad += brace_check()
    bad += loc_format_check()
    return bad


def main() -> None:
    """Run every check in order, print the findings and exit with 0 or 1.

    Raises:
        SystemExit: Always; with a message when the game folder has no state
            history, otherwise with 1 when anything was found and 0 when not.
    """
    game_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GAME
    game = GameInstallation(game_path)
    os.chdir(MOD)
    if not game.has_state_history():
        msg = f"game directory is missing history/states: {game_path}"
        raise SystemExit(msg)
    bad = run_checks(game)
    for b_ in bad:
        print(b_)
    print(f"{len(bad)} findings")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
