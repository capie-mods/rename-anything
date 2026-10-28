#!/usr/bin/env python3
"""Deterministic generator for the repetitive parts of the Rename Anything mod.

HOI4 script has no string type, so the mod stores a typed name as an array of
character codes and turns it back into text through scripted localisation
(``defined_text``) that picks one localisation key per slot. All of those
tables, the GUI layout, the on-screen keyboard and the per-state victory point
(VP) lookup are long and regular, and this script writes them so that nobody
has to edit them by hand.

Usage::

    python tools/gen.py [--game "C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV"]

Input. The only external input is the read-only vanilla installation given by
``--game`` (default: the Steam path above). From ``history/states/*.txt`` the
script takes each state's ``id`` and the provinces of its ``victory_points``
entries, after stripping ``#`` comments. Duplicate provinces are dropped, file
order is kept and at most five VPs per state are used. States without VPs are
kept too, so they still get a numeric ID and an intentionally empty Cities
list. From ``localisation/english/*.yml`` it collects which
``VICTORY_POINTS_<id>`` keys exist. A VP without such a key is shown through a
generated ``RN_PROVNAME_<id>`` key whose text is ``#<id>``.

Output. Every file below is overwritten under ``mod/`` and nothing else is
touched:

* ``common/scripted_localisation/rename_anything_scripted_loc.txt``: the
  ``RN_<B|N|J>_<slot>`` tables that render the three name buffers (input,
  country name, country adjective), province ID digits, VP names per slot split
  into buckets of 64 state IDs, the Cities rows ("Original (now New)" from the
  ``RN_VC<k>_<slot>`` tables), the role icon of a Characters row, keyboard key
  labels that follow the caps toggle, the target type label and the country
  status line.
* ``common/scripted_effects/rename_anything_generated_effects.txt``:
  ``rn_load_selected_state`` (one ``if``/``else_if`` per state that stores the
  literal state ID and its VP provinces on the player country), the effects
  that keep a city name applied here on its state, and the ``meta_effect``
  based ``rn_apply_input``, ``rn_reset_vp`` and ``rn_apply_country_name``
  effects.
* ``common/scripted_guis/rename_anything_scripted_gui.txt``: one scripted GUI
  per main tab (a child container's own ``_visible`` trigger
  did not work in 1.19.3, so each tab is a separate window), the input window
  with every keyboard button, and the panel in the state view. The tab and
  input windows update only when ``rn_gui_dirty`` changes; every click bumps it.
* ``interface/rename_anything.gui`` and ``interface/rename_anything.gfx``: the
  window layout and sprite definitions that match those scripted GUIs.
* ``gfx/interface/rename_anything/*.tga``: six small 32-bit TGA textures drawn
  pixel by pixel (key, wide key, space bar, invisible hit area, text field and
  a Backspace shortcut icon that vanilla lacks).
* ``localisation/<lang>/rename_anything_l_<lang>.yml``: UI strings. Polish has
  its own text; all other languages get the English text.
* ``localisation/<lang>/rename_anything_chars_l_<lang>.yml``: the character
  table and the other key-to-scripted-loc indirections. These files are the
  same in every language (apart from the header) because multiplayer clients
  with different game languages must build identical names.
* ``common/scripted_triggers/rename_anything_generated_triggers.txt``: the state
  and city rename cooldown triggers and ``rn_editor_bridge_available``, the gate
  for every in-place editor window.
* ``common/on_actions/rename_anything_on_actions.txt``: the daily bump of the
  legacy windows' refresh gate (``dirty = rn_gui_dirty``) while a human
  player's editor is open.
* The flag catalog and the flag picker (``modgen.features.flags`` and
  ``flag_picker``): sprites for every file of ``gfx/flags`` that also has a
  medium size, the pool, game-flag, stem-writer and cosmetic-snapshot effects,
  the selected flag's name, the labels, the daily cosmetic tag check, and the two
  picker windows with their scripted GUIs. The generator prints a second summary
  line with the catalog counts.
* The in-place editor: every file of ``tools/inline_editor/`` is copied to the
  same relative path (country, leader and party editors, the party tabs, the
  rename cooldown, the status line, the decision that opens the Characters tab,
  the subject editors and the CAPIE v1.1 grammar adapters). Script and GUI files get a header and
  the cooldown length; localisation goes to every language (Polish from the
  Polish source, the rest from English).

Rename cooldown. One constant, ``modgen.features.cooldown.COOLDOWN_DAYS``, sets
the cooldown for every rename type: country name and adjective, leader, parties
(one shared cooldown), states and cities (one per player country and category).
It starts only after a successful rename. The legacy editor checks the same
cooldowns, so it cannot be used to get around them.

The hand-written files are never touched. They are
``common/scripted_effects/rename_anything_effects.txt``,
``common/scripted_triggers/rename_anything_triggers.txt`` and ``descriptor.mod``.

Text files are written as UTF-8 with LF line endings; localisation files also
get a BOM. Output is sorted and byte-for-byte deterministic for the same game
data, so running the generator twice gives identical files. The script prints
one summary line with state and VP counts. If it finds no state file with an
``id``, it prints an error to stderr and exits with 1 without writing anything.

Code layout. This file is only the command line. The generator itself lives in
the ``modgen`` package next to it, one module per feature of the mod (main
window, Country, Characters, States and Cities tabs, input window, name
buffers, cooldown, in-place editor copy, localisation, textures);
``modgen.build`` puts the pieces together. Reading the game folder is shared
with ``tools/check.py`` through ``rncommon.game_data``.

Limits. The generator does not validate its output; run ``tools/check.py``
afterwards. Neither tool proves that the game accepts the script or that
renames survive save/load and multiplayer. The character set is fixed (Latin
letters, digits, space, ``- . '`` and Polish letters); characters that would
break HOI4 script or localisation are left out on purpose.
"""

from __future__ import annotations

import argparse
import sys

from modgen.build import summary, write_all
from modgen.common import MOD
from modgen.features.flags import read_catalog
from modgen.features.portraits import read_catalog as read_portraits
from modgen.features import char_portraits
from modgen.output import DiskSink
from rncommon.game_data import (
    DEFAULT_GAME,
    GameInstallation,
    read_state_inventory,
    vp_key_ids,
)


def main() -> int:
    """Read the vanilla data, write every generated file and print a summary.

    Returns:
        0 on success, 1 when no vanilla state files were found.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=DEFAULT_GAME)
    args = ap.parse_args()
    game = GameInstallation(args.game)
    states = dict(sorted(read_state_inventory(game.state_histories()).states.items()))
    if not states:
        print("no vanilla states found under", args.game, file=sys.stderr)
        return 1
    keys = {int(province) for province in vp_key_ids(game.english_localisation_lines())}
    catalog = read_catalog(args.game)
    portrait_catalog = read_portraits(args.game)
    char_data = char_portraits.read(args.game, portrait_catalog)
    write_all(
        DiskSink(MOD),
        states,
        keys,
        catalog=catalog,
        portrait_catalog=portrait_catalog,
        char_data=char_data,
    )
    print(summary(states, keys))
    print("flags:", ", ".join(f"{k} {v}" for k, v in catalog.report.items()))
    print("portraits:", ", ".join(f"{k} {v}" for k, v in portrait_catalog.report.items()))
    print(
        f"character portraits: {len(char_data.values)} characters, {len(char_data.textures)} sprites"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
