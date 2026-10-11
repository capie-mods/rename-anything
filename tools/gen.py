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
  into buckets of 64 state IDs, keyboard key labels that follow the caps
  toggle, the target type label and the country status line.
* ``common/scripted_effects/rename_anything_generated_effects.txt``:
  ``rn_load_selected_state`` (one ``if``/``else_if`` per state that stores the
  literal state ID and its VP provinces on the player country), and the
  ``meta_effect`` based ``rn_apply_input``, ``rn_reset_vp`` and
  ``rn_apply_country_name`` effects.
* ``common/scripted_guis/rename_anything_scripted_gui.txt``: the entry button,
  one scripted GUI per main tab (a child container's own ``_visible`` trigger
  did not work in 1.19.3, so each tab is a separate window), the input window
  with every keyboard button, and the panel in the state view.
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

The hand-written files are never touched. They are
``common/scripted_effects/rename_anything_effects.txt``,
``common/scripted_triggers/rename_anything_triggers.txt`` and ``descriptor.mod``.

Text files are written as UTF-8 with LF line endings; localisation files also
get a BOM. Output is sorted and byte-for-byte deterministic for the same game
data, so running the generator twice gives identical files. The script prints
one summary line with state and VP counts. If it finds no state file with an
``id``, it prints an error to stderr and exits with 1 without writing anything.

Limits. The generator does not validate its output; run ``tools/check.py``
afterwards. Neither tool proves that the game accepts the script or that
renames survive save/load and multiplayer. The character set is fixed (Latin
letters, digits, space, ``- . '`` and Polish letters); characters that would
break HOI4 script or localisation are left out on purpose.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import struct
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT_DIR = Path(__file__).resolve().parent.parent
"""Repository root (the parent of ``tools/``)."""

MOD = ROOT_DIR / "mod"
"""Output folder; every generated path is relative to it."""

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
"""Vanilla installation read when ``--game`` is not given."""

MAXLEN = 32
"""Maximum number of characters in one name buffer."""

VP_SLOTS = 5
"""Number of victory point rows the Cities tab can show for one state."""

STATE_BUCKET = 64
"""Width of a state-ID bucket in the two-level VP name lookup."""

PAGE = 10
"""Rows per page in the Characters and States lists."""

PROVINCE_DIGITS = 5
"""Decimal digits used to print a province ID (leading zeros are suppressed)."""

GEN_HEADER = (
    "# GENERATED by tools/gen.py - do not edit by hand, edit the generator and re-run it.\n"
)
"""First line of every generated script file."""

# ----------------------------------------------------------------------------- character table
# code -> char. 0 = none. Characters that would break script/loc are deliberately absent:
# " [ ] | $ § £ \ { } # and anything non-printable.
LOWER = "abcdefghijklmnopqrstuvwxyz"
"""Latin lower-case letters, codes 1 to 26."""

UPPER = LOWER.upper()
"""Latin upper-case letters, codes 27 to 52."""

DIGITS = "0123456789"
"""Digits, codes 53 to 62."""

PL_LOWER = "ąćęłńóśźż"
"""Polish lower-case letters, codes 67 to 75."""

PL_UPPER = "ĄĆĘŁŃÓŚŹŻ"
"""Polish upper-case letters, codes 76 to 84."""

CHARS: dict[int, str] = {}
"""Character code to character; code 0 means an empty slot and has no entry."""

for i, c in enumerate(LOWER):
    CHARS[1 + i] = c  # 1..26
for i, c in enumerate(UPPER):
    CHARS[27 + i] = c  # 27..52
for i, c in enumerate(DIGITS):
    CHARS[53 + i] = c  # 53..62
CHARS[63] = " "
CHARS[64] = "-"
CHARS[65] = "."
CHARS[66] = "'"
for i, c in enumerate(PL_LOWER):
    CHARS[67 + i] = c  # 67..75
for i, c in enumerate(PL_UPPER):
    CHARS[76 + i] = c  # 76..84
FORBIDDEN = set('"[]|$§£\\{}#')
"""Characters that must never appear in the table because they break script or loc."""

assert not (FORBIDDEN & set(CHARS.values()))
CODE = {v: k for k, v in CHARS.items()}
"""Character to character code; the inverse of :data:`CHARS`."""

LANGS = [
    "english",
    "polish",
    "french",
    "german",
    "spanish",
    "braz_por",
    "russian",
    "japanese",
    "simp_chinese",
    "korean",
]
"""Game languages that receive localisation files."""

BUFFERS = [  # (loc prefix, array, length variable)
    ("B", "rn_buf", "rn_len"),
    ("N", "rn_cname", "rn_cname_len"),
    ("J", "rn_cadj", "rn_cadj_len"),
]
"""Name buffers as (scripted loc prefix, code array, length variable)."""


def slots_expr(prefix: str) -> str:
    """Return the localisation text that renders every slot of one buffer.

    Args:
        prefix: Buffer prefix from :data:`BUFFERS` (``B``, ``N`` or ``J``).

    Returns:
        ``[ROOT.RN_<prefix>_0]`` through ``[ROOT.RN_<prefix>_31]`` concatenated.
    """
    return "".join(f"[ROOT.RN_{prefix}_{k}]" for k in range(MAXLEN))


# ----------------------------------------------------------------------------- UI strings
UI = {
    # Each value holds the English text first, then the Polish text.
    "RN_ENTRY_BTN": ("Rename", "Zmień nazwy"),
    "RN_ENTRY_BTN_TT": (
        (
            "Open §YRename Anything§!: rename characters, states and cities. "
            "Country renaming needs the native plugin."
        ),
        (
            "Otwórz §YRename Anything§!: zmień nazwy postaci, stanów i miast. "
            "Nazwa kraju wymaga wtyczki natywnej."
        ),
    ),
    # The en dash below is part of the displayed Polish title (RUF001 suppressed).
    "RN_MAIN_TITLE": ("Rename Anything", "Rename Anything – zmiana nazw"),  # noqa: RUF001
    "RN_TAB_1": ("Country", "Kraj"),
    "RN_TAB_2": ("Characters", "Postacie"),
    "RN_TAB_3": ("States", "Stany"),
    "RN_TAB_4": ("Cities", "Miasta"),
    "RN_CUR_NAME": ("Current name: §Y[ROOT.GetName]§!", "Obecna nazwa: §Y[ROOT.GetName]§!"),
    "RN_CUR_ADJ": ("Adjective: §Y[ROOT.GetAdjective]§!", "Przymiotnik: §Y[ROOT.GetAdjective]§!"),
    "RN_CUR_LEADER": ("Leader: §Y[ROOT.GetLeader]§!", "Przywódca: §Y[ROOT.GetLeader]§!"),
    "RN_BTN_RENAME": ("Rename", "Zmień"),
    "RN_BTN_RESET": ("Reset", "Przywróć"),
    "RN_BTN_CITIES": ("Cities", "Miasta"),
    "RN_BTN_TYPE": ("Type...", "Wpisz..."),
    "RN_COUNTRY_HDR": ("Country name and adjective", "Nazwa i przymiotnik kraju"),
    "RN_COUNTRY_STATUS": ("[ROOT.RN_CountryStatus]", "[ROOT.RN_CountryStatus]"),
    "RN_CNAME_LINE": ("Name: §Y" + slots_expr("N") + "§!", "Nazwa: §Y" + slots_expr("N") + "§!"),
    "RN_CADJ_LINE": (
        "Adjective: §Y" + slots_expr("J") + "§!",
        "Przymiotnik: §Y" + slots_expr("J") + "§!",
    ),
    "RN_BTN_COUNTRY_APPLY": ("Apply", "Zastosuj"),
    "RN_BTN_COUNTRY_RESET": ("Original name", "Przywróć oryginalną nazwę"),
    "RN_COUNTRY_APPLY_TT": (
        (
            "Stores the name and adjective. Load the native plugin first; "
            "without it the displayed country name stays unchanged."
        ),
        (
            "Zapisuje nazwę i przymiotnik. Najpierw załaduj wtyczkę natywną; "
            "bez niej wyświetlana nazwa kraju pozostanie bez zmian."
        ),
    ),
    "RN_COUNTRY_RESET_TT": (
        "Drops the current cosmetic tag. A previous cosmetic tag is not restored.",
        "Usuwa bieżący tag kosmetyczny. Poprzedni tag kosmetyczny nie zostanie przywrócony.",
    ),
    "RN_COUNTRY_NOTE": (
        (
            "Country names require the native plugin in every game process. "
            "Without it, Apply stores text but leaves the displayed name unchanged. "
            "Reset removes the cosmetic tag."
        ),
        (
            "Nazwa kraju wymaga wtyczki natywnej w każdym procesie gry. "
            "Bez niej Zastosuj zapisuje tekst, lecz nie zmienia wyświetlanej nazwy. "
            "Reset usuwa tag kosmetyczny."
        ),
    ),
    "RN_COUNTRY_STATUS_READY": (
        "Enter both fields; native plugin required.",
        "Wpisz oba pola; wymagana wtyczka natywna.",
    ),
    "RN_COUNTRY_STATUS_STORED": (
        "Custom text stored. Check the current name above.",
        "Tekst zapisany. Sprawdź obecną nazwę powyżej.",
    ),
    "RN_PLUGIN_STATUS": ("DLL: INACTIVE (RN1)", "DLL: NIEAKTYWNA (RN1)"),
    "RN_COUNTRY_PLUGIN": ("$RN_PLUGIN_STATUS$", "$RN_PLUGIN_STATUS$"),
    "RN_PAGE": (
        "Page [?ROOT.rn_cpage_disp|0] / [?ROOT.rn_cpages|0]",
        "Strona [?ROOT.rn_cpage_disp|0] / [?ROOT.rn_cpages|0]",
    ),
    "RN_SPAGE": (
        "Page [?ROOT.rn_spage_disp|0] / [?ROOT.rn_spages|0]",
        "Strona [?ROOT.rn_spage_disp|0] / [?ROOT.rn_spages|0]",
    ),
    "RN_BTN_PREV": ("< Prev", "< Wstecz"),
    "RN_BTN_NEXT": ("Next >", "Dalej >"),
    "RN_CHAR_NAME": ("[?rn_row_character.GetName]", "[?rn_row_character.GetName]"),
    "RN_STATE_NAME": ("[This.GetName]", "[This.GetName]"),
    "RN_SEL_STATE_LBL": ("State:", "Stan:"),
    "RN_CITIES_HINT": (
        "Pick a state with 'Cities' in the States tab or in the state view on the map.",
        "Wybierz stan przyciskiem „Miasta” w zakładce Stany albo w widoku stanu na mapie.",
    ),
    "RN_NO_CITIES": (
        "This state has no victory points.",
        "Ten stan nie ma punktów zwycięstwa (miast).",
    ),
    "RN_CITIES_NOTE": (
        (
            "City names are shown as originally named; "
            "the new name is visible on the map and in tooltips."
        ),
        (
            "Lista pokazuje pierwotne nazwy miast; "
            "nowa nazwa jest widoczna na mapie i w podpowiedziach."
        ),
    ),
    "RN_CLOSE_TT": ("Close", "Zamknij"),
    # input window
    "RN_INPUT_TITLE": (
        "Rename: [ROOT.RN_TargetTypeLabel]",
        "Zmiana nazwy: [ROOT.RN_TargetTypeLabel]",
    ),
    "RN_TTYPE_0": ("-", "-"),
    "RN_TTYPE_1": ("character", "postać"),
    "RN_TTYPE_2": ("state", "stan"),
    "RN_TTYPE_3": ("city", "miasto"),
    "RN_TTYPE_4": ("country name", "nazwa kraju"),
    "RN_TTYPE_5": ("country adjective", "przymiotnik kraju"),
    "RN_TARGET_PROV": ("§Y[ROOT.RN_TProvName]§!", "§Y[ROOT.RN_TProvName]§!"),
    "RN_TARGET_COUNTRY": ("§Y[ROOT.GetName]§!", "§Y[ROOT.GetName]§!"),
    "RN_TARGET_ENTRY": ("§Y[This.GetName]§!", "§Y[This.GetName]§!"),
    "RN_TARGET_DISPLAY": ("§Y[?rn_header_target.GetName]§!", "§Y[?rn_header_target.GetName]§!"),
    "RN_FIELD_TEXT": (slots_expr("B") + "§Y|§!", slots_expr("B") + "§Y|§!"),
    "RN_FIELD_COUNT": ("[?ROOT.rn_len|0]/32", "[?ROOT.rn_len|0]/32"),
    "RN_KEY_SPACE": ("Space", "Spacja"),
    "RN_KEY_BACKSPACE": ("Backspace", "Backspace"),
    "RN_KEY_CLEAR": ("Clear", "Wyczyść"),
    "RN_KEY_CAPS_OFF": ("abc", "abc"),
    "RN_KEY_CAPS_ON": ("ABC", "ABC"),
    "RN_KEY_CAPS": ("Caps: [ROOT.RN_CapsLabel]", "Wielkie: [ROOT.RN_CapsLabel]"),
    "RN_BTN_CANCEL": ("Cancel", "Anuluj"),
    "RN_BTN_APPLY": ("Apply", "Zastosuj"),
    "RN_INPUT_HINT": (
        (
            "Type letters, Shift+letter, digits, - and .; Backspace deletes, Enter applies. "
            "Game hotkeys also remain active. Polish letters and ' via buttons. Max 32 characters."
        ),
        (
            "Pisz litery, Shift+litera, cyfry, - i .; Backspace kasuje, Enter zatwierdza. "
            "Skróty gry pozostają aktywne. Polskie litery i ' przyciskami. Maks. 32 znaki."
        ),
    ),
    "RN_APPLY_TT": ("Apply the typed name.", "Zatwierdź wpisaną nazwę."),
    # state view panel
    "RN_SV_TITLE": ("Rename Anything", "Rename Anything"),
    "RN_SV_RENAME": ("Rename state", "Zmień nazwę"),
    "RN_SV_CITIES": ("Cities", "Miasta"),
    "RN_SV_RESET": ("Reset", "Przywróć"),
}
"""UI localisation key to (English text, Polish text); other languages use English."""

# ----------------------------------------------------------------------------- helpers


def write(path: Path, text: str, *, bom: bool = False) -> None:
    """Write a generated text file as UTF-8 with LF line endings.

    Args:
        path: Destination file; missing parent folders are created.
        text: File contents. Any CRLF is turned into LF first.
        bom: Prefix the file with a UTF-8 byte order mark.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


def write_bytes(path: Path, data: bytes) -> None:
    """Write a generated binary file, creating missing parent folders.

    Args:
        path: Destination file.
        data: File contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def yml_escape(s: str) -> str:
    """Return a UI string unchanged after checking it holds no double quote.

    Args:
        s: Localisation text.

    Returns:
        The same text. A lone ``"`` is also accepted unchanged.
    """
    assert '"' not in s or s == '"'
    return s


# --------------------------------------------------------------- vanilla state / VP table


def read_vps(game: str) -> tuple[dict[int, list[int]], set[int]]:
    """Read the vanilla state to VP-province table and the existing VP keys.

    Args:
        game: HOI4 installation folder.

    Returns:
        State ID mapped to its first :data:`VP_SLOTS` distinct VP provinces
        (sorted by state ID; a later file wins on a duplicate ID), and the set
        of province IDs that have a ``VICTORY_POINTS_<id>`` English key.
    """
    states = {}
    # glob.glob string order (and its dot-file rules) decides which file wins on a
    # duplicate state ID, so the reads stay on glob/os.path instead of pathlib.
    for f in sorted(glob.glob(os.path.join(game, "history", "states", "*.txt"))):  # noqa: PTH118, PTH207
        t = Path(f).read_text(encoding="utf-8-sig", errors="replace")
        t = re.sub(r"#[^\n]*", "", t)
        m = re.search(r"\bid\s*=\s*(\d+)", t)
        if not m:
            continue
        sid = int(m.group(1))
        vps: list[int] = []
        for vm in re.finditer(r"victory_points\s*=\s*\{\s*(\d+)\s+[-\d.]+\s*\}", t):
            p = int(vm.group(1))
            if p not in vps:
                vps.append(p)
        # States without VPs still need an ordinary numeric ID and a selected
        # state label. Keeping them also lets an empty Cities list be deliberate.
        states[sid] = vps[:VP_SLOTS]
    keys = set()
    for f in glob.glob(os.path.join(game, "localisation", "english", "*.yml")):  # noqa: PTH118, PTH207
        with Path(f).open(encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                m = re.match(r"\s*VICTORY_POINTS_(\d+):", line)
                if m:
                    keys.add(int(m.group(1)))
    return dict(sorted(states.items())), keys


def vp_key(p: int, keys: set[int]) -> str:
    """Return the localisation key that names a VP province.

    Args:
        p: Province ID.
        keys: Province IDs that have a vanilla ``VICTORY_POINTS_<id>`` key.

    Returns:
        The vanilla key if it exists, otherwise the generated ``RN_PROVNAME_<id>``.
    """
    return f"VICTORY_POINTS_{p}" if p in keys else f"RN_PROVNAME_{p}"


# ----------------------------------------------------------------------------- scripted loc


def gen_scripted_loc(states: dict[int, list[int]], keys: set[int]) -> str:
    """Generate the scripted localisation file.

    Args:
        states: State ID to VP provinces, from :func:`read_vps`.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        Contents of ``rename_anything_scripted_loc.txt``.
    """
    out = [
        GEN_HEADER,
        (
            "# Scripted localisation. Always called with an explicit ROOT "
            "(player country / effect ROOT).\n\n"
        ),
    ]
    order = (
        list(range(1, 27))
        + list(range(27, 53))
        + list(range(63, 67))
        + list(range(53, 63))
        + list(range(67, 85))
    )
    for prefix, arr, lenvar in BUFFERS:
        for k in range(MAXLEN):
            out.append(f"defined_text = {{\n\tname = RN_{prefix}_{k}\n")
            out.append(
                f"\ttext = {{ trigger = {{ NOT = {{ check_variable = {{ {lenvar} > {k} }} }} }}"
                " localization_key = RN_CH_0 }\n"
            )
            out.extend(
                f"\ttext = {{ trigger = {{ check_variable = {{ {arr}^{k} = {c} }} }}"
                f" localization_key = RN_CH_{c} }}\n"
                for c in order
            )
            out.append("\ttext = { localization_key = RN_CH_0 }\n}\n")
    # province id digits, leading zeros suppressed
    for k in range(PROVINCE_DIGITS):
        out.append(f"defined_text = {{\n\tname = RN_PD_{k}\n")
        if k < PROVINCE_DIGITS - 1:
            out.append(
                "\ttext = { trigger = { check_variable = "
                f"{{ rn_tprov < {10 ** (PROVINCE_DIGITS - 1 - k)} }} }}"
                " localization_key = RN_CH_0 }\n"
            )
        out.extend(
            f"\ttext = {{ trigger = {{ check_variable = {{ rn_pd_{k} = {d} }} }}"
            f" localization_key = RN_DIG_{d} }}\n"
            for d in range(10)
        )
        out.append("\ttext = { localization_key = RN_DIG_0 }\n}\n")
    # VP names per slot, two-level by state id bucket
    buckets = sorted({s // STATE_BUCKET for s in states})
    for k in range(VP_SLOTS):
        out.append(f"defined_text = {{\n\tname = RN_VpName_{k}\n")
        out.extend(
            "\ttext = { trigger = { check_variable = "
            f"{{ rn_sel_state_id < {(b + 1) * STATE_BUCKET} }} }}"
            f" localization_key = RN_VPB_{k}_{b} }}\n"
            for b in buckets
            if any(s // STATE_BUCKET == b and len(v) > k for s, v in states.items())
        )
        out.append("\ttext = { localization_key = RN_CH_0 }\n}\n")
        for b in buckets:
            items = [(s, v[k]) for s, v in states.items() if s // STATE_BUCKET == b and len(v) > k]
            if not items:
                continue
            out.append(f"defined_text = {{\n\tname = RN_VpName_{k}_{b}\n")
            out.extend(
                f"\ttext = {{ trigger = {{ check_variable = {{ rn_sel_state_id = {s} }} }}"
                f" localization_key = {vp_key(p, keys)} }}\n"
                for s, p in items
            )
            out.append("\ttext = { localization_key = RN_CH_0 }\n}\n")
    out.append("defined_text = {\n\tname = RN_TProvName\n")
    out.extend(
        f"\ttext = {{ trigger = {{ check_variable = {{ rn_tslot = {k} }} }}"
        f" localization_key = RN_TPROV_{k} }}\n"
        for k in range(VP_SLOTS)
    )
    out.append("\ttext = { localization_key = RN_CH_0 }\n}\n")
    # key labels (caps toggle)
    out.extend(
        f"defined_text = {{\n\tname = RN_KeyLabel_{c}\n"
        "\ttext = { trigger = { check_variable = { rn_shift = 1 } }"
        f" localization_key = RN_CH_{27 + i} }}\n"
        f"\ttext = {{ localization_key = RN_CH_{1 + i} }}\n}}\n"
        for i, c in enumerate(LOWER)
    )
    out.extend(
        f"defined_text = {{\n\tname = RN_KeyLabel_pl{i}\n"
        "\ttext = { trigger = { check_variable = { rn_shift = 1 } }"
        f" localization_key = RN_CH_{76 + i} }}\n"
        f"\ttext = {{ localization_key = RN_CH_{67 + i} }}\n}}\n"
        for i in range(len(PL_LOWER))
    )
    out.append(
        "defined_text = {\n\tname = RN_CapsLabel\n"
        "\ttext = { trigger = { check_variable = { rn_shift = 1 } }"
        " localization_key = RN_KEY_CAPS_ON }\n"
        "\ttext = { localization_key = RN_KEY_CAPS_OFF }\n}\n"
    )
    out.append("defined_text = {\n\tname = RN_TargetTypeLabel\n")
    out.extend(
        f"\ttext = {{ trigger = {{ check_variable = {{ rn_ttype = {t} }} }}"
        f" localization_key = RN_TTYPE_{t} }}\n"
        for t in range(1, 6)
    )
    out.append("\ttext = { localization_key = RN_TTYPE_0 }\n}\n")
    out.append(
        "defined_text = {\n\tname = RN_CountryStatus\n"
        "\ttext = { trigger = { has_country_flag = rn_custom_name }"
        " localization_key = RN_COUNTRY_STATUS_STORED }\n"
        "\ttext = { localization_key = RN_COUNTRY_STATUS_READY }\n}\n"
    )
    return "".join(out)


# ----------------------------------------------------------------------------- generated effects


def gen_effects(states: dict[int, list[int]]) -> str:
    """Generate the scripted effects file.

    Args:
        states: State ID to VP provinces, from :func:`read_vps`.

    Returns:
        Contents of ``rename_anything_generated_effects.txt``.
    """
    n_expr = slots_expr("B")
    p_expr = "".join(f"[ROOT.RN_PD_{k}]" for k in range(PROVINCE_DIGITS))
    out = [GEN_HEADER, "# Generated scripted effects (country scope = player ROOT).\n\n"]
    # CURRENT is the selected state; ROOT is the player country. A typed state
    # variable (including THIS.id) cannot be compared to ordinary numeric IDs.
    # Resolve by state trigger and assign a numeric literal, loading VPs in the
    # same pass. This runs on Cities selection/open, never as a per-frame effect.
    out.append(
        "# State scope -> literal numeric ID and VP slots on ROOT (player). "
        "Includes states without VPs.\n"
    )
    out.append("rn_load_selected_state = {\n")
    for i, (s, vps) in enumerate(states.items()):
        kw = "if" if i == 0 else "else_if"
        sets = "".join(f" set_variable = {{ rn_vp_{k} = {p} }}" for k, p in enumerate(vps))
        out.append(
            f"\t{kw} = {{ limit = {{ state = {s} }} ROOT = {{ "
            f"set_variable = {{ rn_sel_state_id = {s} }} "
            f"set_variable = {{ rn_vp_cnt = {len(vps)} }}{sets} }} }}\n"
        )
    out.append("}\n\n")
    # apply. The template below is emitted verbatim, so its long comment lines are
    # generated output and stay unwrapped (hence the E501 suppression at its end).
    out.append(f"""# Apply the input buffer to the current target. meta_effect turns the scripted loc into a literal string,
# so the stored name is plain text. Persistence was observed in stage0 probes; MP still needs a two-client test.
rn_apply_input = {{
	if = {{
		limit = {{ check_variable = {{ rn_len > 0 }} }}
		if = {{
			limit = {{ check_variable = {{ rn_ttype = 1 }} }}
			# Rebuild the player's current characters; a target can transfer/retire while the input stays open.
			rn_refresh_lists = yes
			for_each_scope_loop = {{
				array = rn_tchar
				if = {{
					limit = {{ is_in_array = {{ array = ROOT.rn_chars_all value = THIS }} }}
					meta_effect = {{
						text = {{ set_character_name = "[N]" }}
						N = "{n_expr}"
					}}
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = 2 }} }}
			for_each_scope_loop = {{
				array = rn_tstate
				if = {{
					limit = {{ is_owned_by = ROOT }}
					meta_effect = {{
						text = {{ set_state_name = "[N]" }}
						N = "{n_expr}"
					}}
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = 3 }} check_variable = {{ rn_tprov > 0 }} }}
			for_each_scope_loop = {{
				array = rn_tstate
				if = {{
					limit = {{ is_owned_by = ROOT }}
					meta_effect = {{
						text = {{ set_province_name = {{ id = [P] name = "[N]" }} }}
						P = "{p_expr}"
						N = "{n_expr}"
					}}
				}}
			}}
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = 4 }} }}
			rn_store_country_name = yes
		}}
		else_if = {{
			limit = {{ check_variable = {{ rn_ttype = 5 }} }}
			rn_store_country_adj = yes
		}}
	}}
	rn_cancel_input = yes
}}

# Reset a city (VP province) name by clearing the override. This also works for VPs without a loc key.
rn_reset_vp = {{ # temp rn_k = slot
	rn_target_vp = yes
	if = {{
		limit = {{ check_variable = {{ rn_tprov > 0 }} }}
		for_each_scope_loop = {{
			array = rn_tstate
			if = {{
				limit = {{ is_owned_by = ROOT }}
				meta_effect = {{
					text = {{ reset_province_name = [P] }}
					P = "{p_expr}"
				}}
			}}
		}}
	}}
}}

# ============================================================== COUNTRY NAME - NATIVE RN1 PROTOCOL
# The cosmetic tag is the game's saved/synchronised carrier. The native plugin decodes both fields
# when looking up country localisation keys. Without it, the tag remains saved but display falls back
# to the original country name. Never treat rn_custom_name as proof that the plugin is active.
rn_apply_country_name = {{
	if = {{
		limit = {{
			rn_country_rename_enabled = yes
			check_variable = {{ rn_cname_len > 0 }}
			check_variable = {{ rn_cadj_len > 0 }}
		}}
		meta_effect = {{
			text = {{ set_cosmetic_tag = "RN1|[N]|[J]|" }}
			N = "{slots_expr("N")}"
			J = "{slots_expr("J")}"
		}}
		set_country_flag = rn_custom_name
	}}
}}
# ============================================================== END COUNTRY NAME - NATIVE RN1 PROTOCOL
""")  # noqa: E501
    return "".join(out)


# ----------------------------------------------------------------------------- keyboard layout
KEY = 36
"""Width in pixels of a normal keyboard key texture."""

KEY_H = 32
"""Height in pixels of every keyboard key texture."""

PITCH = 40
"""Distance in pixels between neighbouring keys, horizontally and vertically."""

KB_Y = 124
"""Y position of the first keyboard row inside the input window."""

ROW1 = [*list("1234567890"), "-", ".", "'"]
"""Characters on the first keyboard row (digits and punctuation)."""

ROW2 = list("qwertyuiop")
"""Letters on the second keyboard row."""

ROW3 = list("asdfghjkl")
"""Letters on the third keyboard row."""

ROW4 = list("zxcvbnm")
"""Letters on the fourth keyboard row."""

KeySpec = tuple[str, int, int, str, str | None, str | None, str]
"""Keyboard button as (name, x, y, sprite, text key, shortcut, click effect body)."""


def key_id(ch: str) -> str:
    """Return the identifier part used in a key's button name.

    Args:
        ch: Character on the key.

    Returns:
        ``minus``, ``dot`` or ``apos`` for punctuation, otherwise the character.
    """
    return {"-": "minus", ".": "dot", "'": "apos"}.get(ch, ch)


def keyboard_keys() -> list[KeySpec]:
    """Return list of (button_name, x, y, sprite, text_key, shortcut, effect_body).

    The list holds the visible keys row by row, then Caps, Backspace, Space and
    Clear, and finally 26 invisible ``shift+<letter>`` buttons that always type
    the upper-case letter.
    """
    keys: list[KeySpec] = []
    for i, ch in enumerate(ROW1):
        x = 20 + i * PITCH
        sc = ch if ch != "'" else None
        keys.append(
            (
                f"rn_key_{key_id(ch)}",
                x,
                KB_Y,
                "GFX_rn_key",
                f"RN_CH_{CODE[ch]}",
                sc,
                f"set_temp_variable = {{ rn_c = {CODE[ch]} }} rn_add_char = yes",
            )
        )
    for row, (x0, y) in (
        (ROW2, (40, KB_Y + PITCH)),
        (ROW3, (60, KB_Y + 2 * PITCH)),
        (ROW4, (80, KB_Y + 3 * PITCH)),
    ):
        keys.extend(
            (
                f"rn_key_{ch}",
                x0 + i * PITCH,
                y,
                "GFX_rn_key",
                f"RN_KL_{ch}",
                ch,
                f"set_temp_variable = {{ rn_c = {CODE[ch]} }} rn_add_letter = yes",
            )
            for i, ch in enumerate(row)
        )
    y5 = KB_Y + 4 * PITCH
    keys.extend(
        (
            f"rn_key_pl{i}",
            20 + i * PITCH,
            y5,
            "GFX_rn_key",
            f"RN_KL_pl{i}",
            None,
            f"set_temp_variable = {{ rn_c = {67 + i} }} rn_add_letter = yes",
        )
        for i in range(len(PL_LOWER))
    )
    keys.append(
        ("rn_key_caps", 380, y5, "GFX_rn_key_wide", "RN_KEY_CAPS", None, "rn_toggle_shift = yes")
    )
    keys.append(
        (
            "rn_key_backspace",
            380,
            KB_Y + 3 * PITCH,
            "GFX_rn_key_wide",
            "RN_KEY_BACKSPACE",
            "BACKSPACE",
            "rn_backspace = yes",
        )
    )
    y6 = KB_Y + 5 * PITCH
    keys.append(
        (
            "rn_key_space",
            100,
            y6,
            "GFX_rn_key_space",
            "RN_KEY_SPACE",
            "SPACE",
            f"set_temp_variable = {{ rn_c = {CODE[' ']} }} rn_add_char = yes",
        )
    )
    keys.append(
        ("rn_key_clear", 320, y6, "GFX_rn_key_wide", "RN_KEY_CLEAR", None, "rn_clear_buf = yes")
    )
    # invisible shift+letter buttons (always uppercase)
    keys.extend(
        (
            f"rn_keyS_{ch}",
            2,
            2,
            "GFX_rn_invisible",
            None,
            f"shift+{ch}",
            f"set_temp_variable = {{ rn_c = {27 + i} }} rn_add_char = yes",
        )
        for i, ch in enumerate(LOWER)
    )
    return keys


# ----------------------------------------------------------------------------- scripted GUI


TABS = [(1, "country"), (2, "chars"), (3, "states"), (4, "cities")]
"""Main window tabs as (tab number, tab name)."""


def gen_main_scripted_guis(vp_effects: str, vp_triggers: str) -> str:
    """One complete window per tab, each with its own scripted GUI and visible trigger.

    Element-level ``_visible`` triggers on child containers do not work in
    1.19.3 (verified live), so each tab is its own scripted GUI with its own
    ``visible`` block.

    Args:
        vp_effects: Click effects of the per-slot VP buttons on the Cities tab.
        vp_triggers: Visibility and enable triggers of those VP buttons.

    Returns:
        The scripted GUI blocks for all four tabs.
    """
    header_effects = "\t\t\trn_close_click = { rn_close_all = yes }\n" + "".join(
        f"\t\t\trn_tab_{t}_click = {{ set_temp_variable = {{ rn_newtab = {t} }}"
        " rn_set_tab = yes }\n"
        for t, _ in TABS
    )
    # Effect templates are emitted verbatim (tab-indented generated script), so a few of
    # their lines exceed the Python line limit; E501 is suppressed on those templates only.
    effects = {
        "country": """			rn_leader_rename_click = { rn_target_leader = yes }
			rn_cname_edit_click = { set_variable = { rn_ttype = 4 } rn_open_input = yes }
			rn_cadj_edit_click = { set_variable = { rn_ttype = 5 } rn_open_input = yes }
			rn_country_apply_click = { rn_apply_country_name = yes }
			rn_country_reset_click = { rn_reset_country_name = yes }
""",
        "chars": """			rn_char_rename_click = { var:rn_row_character = { ROOT = { rn_target_character = yes } } }
			rn_cpage_prev_click = { subtract_from_variable = { rn_cpage = 1 } rn_build_char_page = yes }
			rn_cpage_next_click = { add_to_variable = { rn_cpage = 1 } rn_build_char_page = yes }
""",  # noqa: E501
        "states": """			rn_state_rename_click = {
				if = {
					limit = { is_owned_by = ROOT }
					ROOT = { rn_target_state = yes }
				}
			}
			rn_state_reset_click = {
				if = {
					limit = { is_owned_by = ROOT }
					reset_state_name = yes
				}
			}
			rn_state_cities_click = {
				ROOT = {
					set_variable = { rn_sel_state = PREV }
					set_temp_variable = { rn_newtab = 4 }
					rn_set_tab = yes
				}
			}
			rn_spage_prev_click = { subtract_from_variable = { rn_spage = 1 } rn_build_state_page = yes }
			rn_spage_next_click = { add_to_variable = { rn_spage = 1 } rn_build_state_page = yes }
""",  # noqa: E501
        "cities": vp_effects,
    }
    triggers = {
        "country": """			rn_country_apply_click_enabled = {
				rn_country_rename_enabled = yes
				check_variable = { rn_cname_len > 0 }
				check_variable = { rn_cadj_len > 0 }
			}
			rn_country_reset_click_enabled = { has_country_flag = rn_custom_name }
""",
        "chars": """			rn_cpage_prev_click_enabled = { check_variable = { rn_cpage > 0 } }
			rn_cpage_next_click_enabled = { check_variable = { rn_cpage_disp < rn_cpages } }
""",
        "states": """			rn_spage_prev_click_enabled = { check_variable = { rn_spage > 0 } }
			rn_spage_next_click_enabled = { check_variable = { rn_spage_disp < rn_spages } }
""",
        "cities": "\t\t\trn_no_cities_visible = { NOT = { check_variable = { rn_vp_cnt > 0 } } }\n"
        + vp_triggers,
    }
    lists = {
        "chars": ("rn_chars_grid", "rn_chars_page", "rn_char_entry"),
        "states": ("rn_states_grid", "rn_states_page", "rn_state_entry"),
        "cities": ("rn_selstate_grid", "rn_sel_state_arr", "rn_selstate_entry"),
    }
    out = []
    for t, tab in TABS:
        vis = (
            "NOT = { check_variable = { rn_tab > 1 } }"
            if t == 1
            else f"check_variable = {{ rn_tab = {t} }}"
        )
        out.append(f"""	rn_main_{tab}_gui = {{
		context_type = player_context
		window_name = "rn_main_{tab}_window"
		visible = {{
			has_country_flag = rn_open
			NOT = {{ has_country_flag = rn_input }}
			{vis}
		}}
		ai_enabled = {{ always = no }}
		effects = {{
{header_effects}{effects[tab]}		}}
		triggers = {{
			rn_tab_{t}_click_enabled = {{ always = no }}
{triggers[tab]}		}}
""")
        if tab in lists:
            g, arr, entry = lists[tab]
            # The native GUI scope bridge only carries country/state/unit-leader
            # contexts. Keep civilian characters as typed row variables instead.
            row_context = (
                "\t\t\t\tvalue = rn_row_character\n\t\t\t\tchange_scope = no"
                if tab == "chars"
                else "\t\t\t\tchange_scope = yes"
            )
            out.append(f"""		dynamic_lists = {{
			{g} = {{
				array = {arr}
{row_context}
				entry_container = "{entry}"
			}}
		}}
""")
        out.append("\t}\n\n")
    return "".join(out)


def _window_header(name: str, width: int, height: int) -> str:
    """Return the opening of a centred main window with the tiled border background.

    Args:
        name: Window name.
        width: Window width in pixels.
        height: Window height in pixels.

    Returns:
        The ``containerWindowType`` header lines up to the background.
    """
    return (
        f'\tcontainerWindowType = {{\n\t\tname = "{name}"\n\t\torientation = center\n'
        f"\t\tposition = {{ x = {-width // 2} y = {-height // 2} }}\n"
        f"\t\tsize = {{ width = {width} height = {height} }}\n\t\tclipping = no\n"
    )


def _country_tab(y0: int) -> list[str]:
    """Return the elements of the Country tab.

    Args:
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    return [
        txt("rn_cur_name", 20, y0 + 8, "RN_CUR_NAME", w=520),
        txt("rn_cur_adj", 20, y0 + 32, "RN_CUR_ADJ", w=520),
        txt("rn_cur_leader", 20, y0 + 66, "RN_CUR_LEADER", w=380),
        btn("rn_leader_rename", 410, y0 + 58, "GFX_button_123x34", text="RN_BTN_RENAME"),
        txt("rn_country_hdr", 20, y0 + 112, "RN_COUNTRY_HDR", font="hoi_18mbs", w=520),
        txt("rn_cname_line", 20, y0 + 148, "RN_CNAME_LINE", w=380),
        btn("rn_cname_edit", 410, y0 + 140, "GFX_button_123x34", text="RN_BTN_TYPE"),
        txt("rn_cadj_line", 20, y0 + 188, "RN_CADJ_LINE", w=380),
        btn("rn_cadj_edit", 410, y0 + 180, "GFX_button_123x34", text="RN_BTN_TYPE"),
        btn(
            "rn_country_apply",
            20,
            y0 + 226,
            "GFX_button_123x34",
            text="RN_BTN_COUNTRY_APPLY",
            tooltip="RN_COUNTRY_APPLY_TT",
        ),
        btn(
            "rn_country_reset",
            152,
            y0 + 226,
            "GFX_button_261x34",
            text="RN_BTN_COUNTRY_RESET",
            tooltip="RN_COUNTRY_RESET_TT",
        ),
        txt("rn_country_status", 20, y0 + 272, "RN_COUNTRY_STATUS", w=520, h=24),
        txt("rn_country_plugin", 20, y0 + 296, "RN_COUNTRY_PLUGIN", w=520, h=24),
        txt("rn_country_note", 20, y0 + 328, "RN_COUNTRY_NOTE", w=520, h=72),
    ]


def _list_tab(tab: str, y0: int) -> list[str]:
    """Return the elements of the Characters or States tab (paged list).

    Args:
        tab: ``chars`` or ``states``.
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    grid, prev, nxt, page = (
        ("rn_chars_grid", "rn_cpage_prev", "rn_cpage_next", "RN_PAGE")
        if tab == "chars"
        else ("rn_states_grid", "rn_spage_prev", "rn_spage_next", "RN_SPAGE")
    )
    py = y0 + PAGE * 36 + 8
    return [
        (
            f'\t\tgridBoxType = {{\n\t\t\tname = "{grid}"\n\t\t\tposition = {{ x = 20 y = {y0} }}\n'
            f"\t\t\tsize = {{ width = 520 height = {PAGE * 36} }}\n"
            "\t\t\tslotsize = { width = 520 height = 36 }\n"
            '\t\t\tmax_slots_horizontal = 1\n\t\t\tformat = "UPPER_LEFT"\n\t\t}\n'
        ),
        btn(prev, 20, py, "GFX_button_94x31", text="RN_BTN_PREV"),
        txt(f"rn_{tab}_page", 130, py + 6, page, w=300, fmt="centre"),
        btn(nxt, 446, py, "GFX_button_94x31", text="RN_BTN_NEXT"),
    ]


def _cities_tab(y0: int) -> list[str]:
    """Return the elements of the Cities tab.

    Args:
        y0: Y position where the tab content starts.

    Returns:
        GUI element blocks in drawing order.
    """
    o = [
        txt("rn_sel_state_lbl", 20, y0 + 8, "RN_SEL_STATE_LBL", w=100),
        (
            '\t\tgridBoxType = {\n\t\t\tname = "rn_selstate_grid"\n'
            f"\t\t\tposition = {{ x = 110 y = {y0 + 4} }}\n"
            "\t\t\tsize = { width = 420 height = 30 }\n"
            "\t\t\tslotsize = { width = 420 height = 30 }\n"
            '\t\t\tmax_slots_horizontal = 1\n\t\t\tformat = "UPPER_LEFT"\n\t\t}\n'
        ),
        txt("rn_cities_hint", 20, y0 + 38, "RN_CITIES_HINT", w=520, h=40),
        txt("rn_no_cities", 20, y0 + 90, "RN_NO_CITIES", w=520),
    ]
    for k in range(VP_SLOTS):
        y = y0 + 86 + k * 44
        o.append(txt(f"rn_vp_name_{k}", 20, y + 8, f"RN_VPROW_{k}", w=300))
        o.append(btn(f"rn_vp_rename_{k}", 330, y + 2, "GFX_button_94x31", text="RN_BTN_RENAME"))
        o.append(btn(f"rn_vp_reset_{k}", 430, y + 2, "GFX_button_94x31", text="RN_BTN_RESET"))
    o.append(txt("rn_cities_note", 20, y0 + 314, "RN_CITIES_NOTE", w=520, h=60))
    return o


def gen_main_windows() -> str:
    """Generate the four main tab windows of the ``.gui`` file.

    Returns:
        One ``containerWindowType`` block per tab, each with the title, close
        button, tab buttons and that tab's own content.
    """
    width, height, content_y = 560, 520, 86
    o = []
    for _, tab in TABS:
        o.append(_window_header(f"rn_main_{tab}_window", width, height))
        o.append(
            '\t\tbackground = { name = "rn_main_bg"'
            ' quadTextureSprite = "GFX_tiled_window_2b_border" }\n'
        )
        o.append(txt("rn_main_title", 20, 12, "RN_MAIN_TITLE", font="hoi_18mbs", w=480))
        o.append(btn("rn_close", width - 42, 8, "GFX_closebutton", tooltip="RN_CLOSE_TT"))
        o.extend(
            btn(f"rn_tab_{tt}", 20 + (tt - 1) * 132, 42, "GFX_button_123x34", text=f"RN_TAB_{tt}")
            for tt, _ in TABS
        )
        if tab == "country":
            o += _country_tab(content_y)
        elif tab in {"chars", "states"}:
            o += _list_tab(tab, content_y)
        else:
            o += _cities_tab(content_y)
        o.append("\t}\n\n")
    return "".join(o)


def gen_scripted_gui() -> str:
    """Generate the complete scripted GUI file.

    Returns:
        Contents of ``rename_anything_scripted_gui.txt``: the entry button GUI,
        the four tab GUIs, the input window GUI with every keyboard key, and the
        state view panel GUI.
    """
    keys = keyboard_keys()
    key_effects = "".join(f"\t\t\t{name}_click = {{ {body} }}\n" for name, *_r, body in keys)
    vp_effects = "".join(
        f"\t\t\trn_vp_rename_{k}_click = {{ set_temp_variable = {{ rn_k = {k} }}"
        " rn_target_vp = yes rn_open_input = yes }\n"
        f"\t\t\trn_vp_reset_{k}_click = {{ set_temp_variable = {{ rn_k = {k} }}"
        " rn_reset_vp = yes }\n"
        for k in range(VP_SLOTS)
    )
    vp_triggers = "".join(
        f"\t\t\t{el}_{k}_visible = {{ check_variable = {{ rn_vp_cnt > {k} }} }}\n"
        for k in range(VP_SLOTS)
        for el in ("rn_vp_name", "rn_vp_rename", "rn_vp_reset")
    )
    vp_triggers += "".join(
        f"\t\t\t{el}_{k}_click_enabled = {{ check_variable = {{ rn_vp_cnt > {k} }} }}\n"
        for k in range(VP_SLOTS)
        for el in ("rn_vp_rename", "rn_vp_reset")
    )
    main_guis = gen_main_scripted_guis(vp_effects, vp_triggers)
    return (
        GEN_HEADER
        + f"""# Rename Anything scripted GUIs. Every state change happens in these button effects
# on the clicking player's own country (ROOT). Two-client MP verification is still required.

scripted_gui = {{
	rn_entry_gui = {{
		context_type = player_context
		window_name = "rn_entry_window"
		visible = {{ always = yes }}
		ai_enabled = {{ always = no }}
		effects = {{
			rn_entry_btn_click = {{
				if = {{
					limit = {{ has_country_flag = rn_open }}
					rn_close_all = yes
				}}
				else = {{
					rn_open_main = yes
				}}
			}}
		}}
	}}

{main_guis}
	rn_input_gui = {{
		context_type = player_context
		window_name = "rn_input_window"
		visible = {{ has_country_flag = rn_input }}
		ai_enabled = {{ always = no }}
		effects = {{
{key_effects}			rn_cancel_click = {{ rn_cancel_input = yes }}
			rn_apply_click = {{ rn_apply_input = yes }}
		}}
		triggers = {{
			rn_apply_click_enabled = {{ check_variable = {{ rn_len > 0 }} }}
			rn_target_prov_visible = {{ check_variable = {{ rn_ttype = 3 }} }}
			rn_target_country_visible = {{ check_variable = {{ rn_ttype > 3 }} }}
		}}
		dynamic_lists = {{
			rn_target_grid = {{
				array = rn_display_target
				value = rn_header_target
				change_scope = no
				entry_container = "rn_target_entry"
			}}
		}}
	}}

	rn_state_view_gui = {{
		context_type = selected_state_context
		parent_window_token = selected_state_view
		window_name = "rn_state_view_window"
		visible = {{ is_owned_by = ROOT }}
		ai_enabled = {{ always = no }}
		effects = {{
			rn_sv_rename_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					ROOT = {{ rn_target_state = yes }}
				}}
			}}
			rn_sv_cities_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					ROOT = {{
						set_country_flag = rn_open
						clr_country_flag = rn_input
						set_variable = {{ rn_sel_state = PREV }}
						set_temp_variable = {{ rn_newtab = 4 }}
						rn_set_tab = yes
					}}
				}}
			}}
			rn_sv_reset_click = {{
				if = {{
					limit = {{ is_owned_by = ROOT }}
					reset_state_name = yes
				}}
			}}
		}}
	}}
}}
"""
    )


# ----------------------------------------------------------------------------- .gui


# One keyword parameter per attribute of the GUI element, hence PLR0913.
def txt(  # noqa: PLR0913
    name: str,
    x: int,
    y: int,
    text: str,
    *,
    font: str = "hoi_16mbs",
    w: int = 500,
    h: int = 24,
    fmt: str = "left",
    extra: str = "",
) -> str:
    """Return one single-line ``instantTextBoxType`` element.

    Args:
        name: Element name.
        x: X position.
        y: Y position.
        text: Localisation key or literal text.
        font: Font name.
        w: ``maxWidth``.
        h: ``maxHeight``.
        fmt: Text alignment (``left``, ``centre`` or ``right``).
        extra: Raw text appended before the closing brace.

    Returns:
        The element line, indented by two tabs.
    """
    return (
        f'\t\tinstantTextBoxType = {{ name = "{name}" position = {{ x = {x} y = {y} }}'
        f' font = "{font}" '
        f'text = "{text}" maxWidth = {w} maxHeight = {h} format = {fmt} fixedsize = yes{extra} }}\n'
    )


# One keyword parameter per attribute of the GUI element, hence PLR0913.
def btn(  # noqa: PLR0913
    name: str,
    x: int,
    y: int,
    sprite: str,
    *,
    text: str | None = None,
    shortcut: str | None = None,
    font: str = "hoi_16mbs",
    tooltip: str | None = None,
    indent: str = "\t\t",
) -> str:
    """Return one ``buttonType`` element.

    Args:
        name: Element name; its click effect is ``<name>_click``.
        x: X position.
        y: Y position.
        sprite: Sprite type.
        text: Button text key; text and font lines are omitted when empty.
        shortcut: Keyboard shortcut; omitted when empty.
        font: Button font, used only together with ``text``.
        tooltip: Tooltip key; omitted when empty.
        indent: Indentation of the opening line.

    Returns:
        The multi-line element block.
    """
    s = (
        f'{indent}buttonType = {{\n{indent}\tname = "{name}"\n'
        f'{indent}\tposition = {{ x = {x} y = {y} }}\n{indent}\tspriteType = "{sprite}"\n'
    )
    if text not in {None, ""}:
        s += f'{indent}\tbuttonText = "{text}"\n{indent}\tbuttonFont = "{font}"\n'
    if tooltip not in {None, ""}:
        s += f'{indent}\tpdx_tooltip = "{tooltip}"\n'
    if shortcut not in {None, ""}:
        s += f'{indent}\tshortcut = "{shortcut}"\n'
    s += f"{indent}\tclicksound = click_default\n{indent}}}\n"
    return s


def indent(block: str, n: int = 1) -> str:
    """Indent every non-blank line of a block with tabs.

    Args:
        block: Text to indent.
        n: Number of tabs to add.

    Returns:
        The indented text; blank lines are left as they are.
    """
    return "".join(
        ("\t" * n + line) if line.strip() else line for line in block.splitlines(keepends=True)
    )


def _list_entries() -> list[str]:
    """Return the row templates used by the dynamic lists.

    Returns:
        GUI blocks for the character, state, selected-state and target rows.
    """
    return [
        (
            '\tcontainerWindowType = {\n\t\tname = "rn_char_entry"\n'
            "\t\tsize = { width = 520 height = 36 }\n\t\tclipping = no\n"
        ),
        txt("rn_char_name", 6, 8, "RN_CHAR_NAME", w=390),
        btn("rn_char_rename", 420, 2, "GFX_button_94x31", text="RN_BTN_RENAME"),
        "\t}\n",
        (
            '\tcontainerWindowType = {\n\t\tname = "rn_state_entry"\n'
            "\t\tsize = { width = 520 height = 36 }\n\t\tclipping = no\n"
        ),
        txt("rn_state_name", 6, 8, "RN_STATE_NAME", w=215),
        btn("rn_state_rename", 228, 2, "GFX_button_94x31", text="RN_BTN_RENAME"),
        btn("rn_state_reset", 324, 2, "GFX_button_94x31", text="RN_BTN_RESET"),
        btn("rn_state_cities", 420, 2, "GFX_button_94x31", text="RN_BTN_CITIES"),
        "\t}\n",
        (
            '\tcontainerWindowType = {\n\t\tname = "rn_selstate_entry"\n'
            "\t\tsize = { width = 420 height = 30 }\n\t\tclipping = no\n"
        ),
        txt("rn_selstate_name", 0, 4, "RN_TARGET_ENTRY", w=410),
        "\t}\n",
        (
            '\tcontainerWindowType = {\n\t\tname = "rn_target_entry"\n'
            "\t\tsize = { width = 500 height = 26 }\n\t\tclipping = no\n"
        ),
        txt("rn_target_name", 0, 2, "RN_TARGET_DISPLAY", font="hoi_18mbs", w=500),
        "\t}\n\n",
    ]


def _input_window(width: int) -> list[str]:
    """Return the input window with the text field and on-screen keyboard.

    Args:
        width: Window width in pixels.

    Returns:
        GUI blocks in drawing order, ending with the closing brace.
    """
    input_height = 468
    o = [
        _window_header("rn_input_window", width, input_height),
        (
            '\t\tbackground = { name = "rn_input_bg"'
            ' quadTextureSprite = "GFX_tiled_window_2b_border" }\n'
        ),
        txt("rn_input_title", 20, 12, "RN_INPUT_TITLE", font="hoi_18mbs", w=520),
    ]
    o.extend(
        f'\t\tgridBoxType = {{\n\t\t\tname = "{g}"\n\t\t\tposition = {{ x = 20 y = 40 }}\n'
        "\t\t\tsize = { width = 500 height = 26 }\n\t\t\tslotsize = { width = 500 height = 26 }\n"
        '\t\t\tmax_slots_horizontal = 1\n\t\t\tformat = "UPPER_LEFT"\n\t\t}\n'
        for g in ("rn_target_grid",)
    )
    o.append(txt("rn_target_prov", 20, 42, "RN_TARGET_PROV", font="hoi_18mbs", w=500))
    o.append(txt("rn_target_country", 20, 42, "RN_TARGET_COUNTRY", font="hoi_18mbs", w=500))
    o.append(
        '\t\ticonType = { name = "rn_field_bg" position = { x = 20 y = 72 }'
        ' spriteType = "GFX_rn_field" }\n'
    )
    o.append(txt("rn_field_text", 30, 82, "RN_FIELD_TEXT", font="hoi_18mbs", w=440))
    o.append(txt("rn_field_count", 470, 84, "RN_FIELD_COUNT", w=64, fmt="right"))
    keys = keyboard_keys()
    # invisible shift buttons first (drawn underneath)
    o.extend(
        btn(name, x, y, sprite, text=None, shortcut=sc)
        for name, x, y, sprite, _text, sc, _ in keys
        if sprite == "GFX_rn_invisible"
    )
    o.extend(
        btn(name, x, y, sprite, text=text, shortcut=sc)
        for name, x, y, sprite, text, sc, _ in keys
        if sprite != "GFX_rn_invisible"
    )
    by = KB_Y + 6 * PITCH + 2
    o.append(btn("rn_cancel", 150, by, "GFX_button_123x34", text="RN_BTN_CANCEL"))
    o.append(
        btn(
            "rn_apply",
            290,
            by,
            "GFX_button_123x34",
            text="RN_BTN_APPLY",
            shortcut="RETURN",
            tooltip="RN_APPLY_TT",
        )
    )
    o.append(txt("rn_input_hint", 20, by + 40, "RN_INPUT_HINT", font="hoi_16mbs", w=520, h=44))
    o.append("\t}\n\n")
    return o


def gen_gui() -> str:
    """Generate the interface ``.gui`` file.

    Returns:
        Contents of ``rename_anything.gui``: the entry button, the tab windows,
        the list row templates, the input window and the state view panel.
    """
    width = 560
    o = [GEN_HEADER, "guiTypes = {\n"]
    # entry button
    o.append(
        '\tcontainerWindowType = {\n\t\tname = "rn_entry_window"\n\t\torientation = upper_left\n'
        "\t\tposition = { x = 8 y = 150 }\n\t\tsize = { width = 130 height = 36 }\n"
        "\t\tclipping = no\n"
    )
    o.append(
        btn(
            "rn_entry_btn",
            0,
            0,
            "GFX_button_123x34",
            text="RN_ENTRY_BTN",
            tooltip="RN_ENTRY_BTN_TT",
        )
    )
    o.append("\t}\n\n")

    o.append(gen_main_windows())

    # list entries
    o += _list_entries()

    # input window
    o += _input_window(width)

    # state view panel (selected_state_context)
    o.append(
        '\tcontainerWindowType = {\n\t\tname = "rn_state_view_window"\n'
        "\t\torientation = upper_left\n"
        "\t\tposition = { x = 476 y = 95 }\n\t\tsize = { width = 140 height = 136 }\n"
        "\t\tclipping = no\n"
        '\t\tbackground = { name = "rn_sv_bg"'
        ' quadTextureSprite = "GFX_tiled_window_2b_border" }\n'
    )
    o.append(txt("rn_sv_title", 10, 8, "RN_SV_TITLE", w=120, fmt="centre"))
    o.append(btn("rn_sv_rename", 8, 32, "GFX_button_123x34", text="RN_SV_RENAME"))
    o.append(btn("rn_sv_cities", 8, 66, "GFX_button_123x34", text="RN_SV_CITIES"))
    o.append(btn("rn_sv_reset", 8, 100, "GFX_button_123x34", text="RN_SV_RESET"))
    o.append("\t}\n")
    o.append("}\n")
    return "".join(o)


def gen_gfx() -> str:
    """Generate the sprite definitions file.

    Returns:
        Contents of ``rename_anything.gfx`` for the key, field, invisible and
        ``GFX_BACKSPACE`` sprites.
    """
    sprites = [
        ("GFX_rn_key", "rn_key.tga"),
        ("GFX_rn_key_wide", "rn_key_wide.tga"),
        ("GFX_rn_key_space", "rn_key_space.tga"),
        ("GFX_rn_invisible", "rn_invisible.tga"),
    ]
    o = [GEN_HEADER, "spriteTypes = {\n"]
    o.extend(
        f'\tspriteType = {{\n\t\tname = "{name}"\n'
        f'\t\ttexturefile = "gfx/interface/rename_anything/{f}"\n'
        '\t\tnoOfFrames = 1\n\t\teffectFile = "gfx/FX/buttonstate.lua"\n\t}\n'
        for name, f in sprites
    )
    o.append(
        '\tspriteType = {\n\t\tname = "GFX_rn_field"\n'
        '\t\ttexturefile = "gfx/interface/rename_anything/rn_field.tga"\n\t}\n'
    )
    # Shortcut tooltips request GFX_<key name>. Vanilla has no BACKSPACE icon.
    o.append(
        '\tspriteType = {\n\t\tname = "GFX_BACKSPACE"\n'
        '\t\ttexturefile = "gfx/interface/rename_anything/rn_backspace_icon.tga"\n'
        "\t\tlegacy_lazy_load = no\n\t}\n"
    )
    o.append("}\n")
    return "".join(o)


# ------------------------------------------------- textures (TGA, 32-bit BGRA, top-left origin)

Rgba = tuple[int, int, int, int]
"""One pixel as (red, green, blue, alpha), each 0 to 255."""

TGA_TRUECOLOR = 2
"""TGA image type for uncompressed true-colour data."""

TGA_DESCRIPTOR_TOP_LEFT_8BIT_ALPHA = 0x28
"""TGA image descriptor: 8 alpha bits and a top-left origin."""

TRANSPARENT: Rgba = (0, 0, 0, 0)
"""Fully transparent pixel."""


def tga(w: int, h: int, px: Callable[[int, int], Rgba]) -> bytes:
    """Encode an uncompressed 32-bit TGA image.

    Args:
        w: Width in pixels.
        h: Height in pixels.
        px: Function returning the RGBA colour of pixel ``(x, y)``; ``(0, 0)``
            is the top-left corner.

    Returns:
        The complete TGA file contents (18-byte header and BGRA pixel rows).
    """
    head = struct.pack(
        "<BBBHHBHHHHBB",
        0,
        0,
        TGA_TRUECOLOR,
        0,
        0,
        0,
        0,
        0,
        w,
        h,
        32,
        TGA_DESCRIPTOR_TOP_LEFT_8BIT_ALPHA,
    )
    body = bytearray()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px(x, y)
            body += bytes((b, g, r, a))
    return head + bytes(body)


def key_px(
    w: int,
    h: int,
    fill: Rgba = (52, 50, 44, 240),
    border: Rgba = (176, 156, 104, 255),
    hi: Rgba = (96, 92, 80, 255),
) -> Callable[[int, int], Rgba]:
    """Return a pixel function for a key-like rectangle.

    The rectangle has a one-pixel border with transparent corners, a highlight
    line under the top border and a darker band along the bottom.

    Args:
        w: Width in pixels.
        h: Height in pixels.
        fill: Interior colour.
        border: Border colour.
        hi: Highlight colour of row 1.

    Returns:
        A function mapping ``(x, y)`` to an RGBA colour.
    """

    def f(x: int, y: int) -> Rgba:
        """Return the colour of one pixel of the key rectangle."""
        if x == 0 or y == 0 or x == w - 1 or y == h - 1:
            if (x in {0, w - 1}) and (y in {0, h - 1}):
                return TRANSPARENT  # rounded-ish corners
            return border
        if y == 1:
            return hi
        if y >= h - 3:
            return (30, 29, 26, 240)
        return fill

    return f


ICON_TOP_ROW = 1
"""First row of the Backspace icon outline."""

ICON_BOTTOM_ROW = 14
"""Last row of the Backspace icon outline."""

ICON_RIGHT_COLUMN = 32
"""Right edge column of the Backspace icon outline."""

ICON_CROSS_X = 21
"""Column of the centre of the X drawn inside the Backspace icon."""

ICON_CROSS_Y = 7
"""Row of the centre of the X drawn inside the Backspace icon."""

ICON_CROSS_RADIUS = 3
"""Half-size in pixels of the X drawn inside the Backspace icon."""

ICON_LINE: Rgba = (208, 200, 176, 255)
"""Colour of the Backspace icon outline and X."""


def backspace_icon_px(x: int, y: int) -> Rgba:
    """A 34x16 texticon, matching the height of vanilla shortcut icons.

    It draws an outlined arrow-shaped key with an X inside.

    Args:
        x: Pixel column.
        y: Pixel row.

    Returns:
        The RGBA colour of that pixel.
    """
    top, bottom, right = ICON_TOP_ROW, ICON_BOTTOM_ROW, ICON_RIGHT_COLUMN
    if not top <= y <= bottom:
        return TRANSPARENT
    left = 8 - min(y - top, bottom - y)
    if not left <= x <= right:
        return TRANSPARENT
    if x in {left, right} or y in {top, bottom}:
        return ICON_LINE
    dx, dy = abs(x - ICON_CROSS_X), abs(y - ICON_CROSS_Y)
    if dx <= ICON_CROSS_RADIUS and dy <= ICON_CROSS_RADIUS and dx == dy:
        return ICON_LINE
    return (36, 36, 36, 255)


def transparent_px(_x: int, _y: int) -> Rgba:
    """Return a transparent pixel for every position (the invisible hit area texture)."""
    return TRANSPARENT


def gen_textures() -> dict[str, bytes]:
    """Generate every TGA texture.

    Returns:
        File name mapped to TGA contents.
    """
    return {
        "rn_key.tga": tga(KEY, KEY_H, key_px(KEY, KEY_H)),
        "rn_key_wide.tga": tga(116, KEY_H, key_px(116, KEY_H)),
        "rn_key_space.tga": tga(196, KEY_H, key_px(196, KEY_H)),
        "rn_invisible.tga": tga(4, 4, transparent_px),
        "rn_backspace_icon.tga": tga(34, 16, backspace_icon_px),
        "rn_field.tga": tga(
            520,
            40,
            key_px(
                520, 40, fill=(14, 14, 16, 235), border=(200, 180, 120, 255), hi=(14, 14, 16, 235)
            ),
        ),
    }


# ----------------------------------------------------------------------------- localisation


def gen_char_loc(lang: str, states: dict[int, list[int]], keys: set[int]) -> str:
    """Generate the language-independent character table for one language.

    Args:
        lang: Language name used in the ``l_<lang>:`` header.
        states: State ID to VP provinces, from :func:`read_vps`.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        Contents of ``rename_anything_chars_l_<lang>.yml`` (without BOM).
    """
    o = [
        f"l_{lang}:\n",
        (
            " # GENERATED by tools/gen.py - language-independent tables "
            "(must be identical in every language for MP).\n"
        ),
    ]
    o.append(' RN_CH_0: ""\n')
    o.extend(f' RN_CH_{c}: "{CHARS[c]}"\n' for c in sorted(CHARS))
    o.extend(f' RN_DIG_{d}: "{d}"\n' for d in range(10))
    buckets = sorted({s // STATE_BUCKET for s in states})
    for k in range(VP_SLOTS):
        o.extend(
            f' RN_VPB_{k}_{b}: "[ROOT.RN_VpName_{k}_{b}]"\n'
            for b in buckets
            if any(s // STATE_BUCKET == b and len(v) > k for s, v in states.items())
        )
        o.append(f' RN_TPROV_{k}: "[ROOT.RN_VpName_{k}]"\n')
        o.append(f' RN_VPROW_{k}: "[ROOT.RN_VpName_{k}]"\n')
    o.extend(f' RN_KL_{c}: "[ROOT.RN_KeyLabel_{c}]"\n' for c in LOWER)
    o.extend(f' RN_KL_pl{i}: "[ROOT.RN_KeyLabel_pl{i}]"\n' for i in range(len(PL_LOWER)))
    missing = sorted({p for v in states.values() for p in v if p not in keys})
    o.extend(f' RN_PROVNAME_{p}: "#{p}"\n' for p in missing)
    return "".join(o)


def gen_ui_loc(lang: str) -> str:
    """Generate the UI strings file for one language.

    Args:
        lang: Language name; ``polish`` gets the Polish text, all others English.

    Returns:
        Contents of ``rename_anything_l_<lang>.yml`` (without BOM).
    """
    idx = 1 if lang == "polish" else 0
    o = [f"l_{lang}:\n", " # GENERATED by tools/gen.py (UI strings)\n"]
    o.extend(f' {k}: "{yml_escape(v[idx])}"\n' for k, v in UI.items())
    return "".join(o)


# ----------------------------------------------------------------------------- main


def main() -> int:
    """Read the vanilla data, write every generated file and print a summary.

    Returns:
        0 on success, 1 when no vanilla state files were found.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default=DEFAULT_GAME)
    args = ap.parse_args()
    states, keys = read_vps(args.game)
    if not states:
        print("no vanilla states found under", args.game, file=sys.stderr)
        return 1
    common = MOD / "common"
    write(
        common / "scripted_localisation" / "rename_anything_scripted_loc.txt",
        gen_scripted_loc(states, keys),
    )
    write(
        common / "scripted_effects" / "rename_anything_generated_effects.txt",
        gen_effects(states),
    )
    write(common / "scripted_guis" / "rename_anything_scripted_gui.txt", gen_scripted_gui())
    write(MOD / "interface" / "rename_anything.gui", gen_gui())
    write(MOD / "interface" / "rename_anything.gfx", gen_gfx())
    for name, data in gen_textures().items():
        write_bytes(MOD / "gfx" / "interface" / "rename_anything" / name, data)
    for lang in LANGS:
        loc_dir = MOD / "localisation" / lang
        write(loc_dir / f"rename_anything_l_{lang}.yml", gen_ui_loc(lang), bom=True)
        write(
            loc_dir / f"rename_anything_chars_l_{lang}.yml",
            gen_char_loc(lang, states, keys),
            bom=True,
        )
    nvp = sum(len(v) for v in states.values())
    with_vps = sum(bool(v) for v in states.values())
    without_key = sum(1 for v in states.values() for p in v if p not in keys)
    print(
        f"states: {len(states)}, states with VPs: {with_vps}, VP slots: {nvp}, "
        f"VPs without loc key: {without_key}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
