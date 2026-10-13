"""Assemble the feature slices into the generated files.

The slices produce fragments; this module decides which fragment goes into
which file and in which order. The order reproduces the files exactly as the
single-file generator wrote them, so a refactoring of a slice can be checked by
comparing ``mod/`` byte for byte.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from modgen.common import GEN_HEADER, LANGS, StateTable
from modgen.features import (
    characters,
    cities,
    cooldown,
    country,
    inline_editor,
    input_window,
    legacy_field,
    localisation,
    main_window,
    refresh,
    states,
    textures,
)
from modgen.features.text_buffers import BUFFERS, slot_tables

if TYPE_CHECKING:
    from modgen.output import OutputSink

SCRIPTED_LOC_FILE = "common/scripted_localisation/rename_anything_scripted_loc.txt"
"""Scripted localisation of the legacy editor, relative to ``mod/``."""

TRIGGERS_FILE = "common/scripted_triggers/rename_anything_generated_triggers.txt"
"""Generated scripted triggers, relative to ``mod/``."""

EFFECTS_FILE = "common/scripted_effects/rename_anything_generated_effects.txt"
"""Generated scripted effects, relative to ``mod/``."""

SCRIPTED_GUI_FILE = "common/scripted_guis/rename_anything_scripted_gui.txt"
"""Scripted GUIs of the legacy editor, relative to ``mod/``."""

GUI_FILE = "interface/rename_anything.gui"
"""Window layout of the legacy editor, relative to ``mod/``."""

GFX_FILE = "interface/rename_anything.gfx"
"""Sprite definitions of the legacy editor, relative to ``mod/``."""


def tabs() -> list[main_window.TabSpec]:
    """Return the four main window tabs in tab order.

    Returns:
        Country, Characters, States and Cities.
    """
    y0 = main_window.CONTENT_Y
    return [country.tab(y0), characters.tab(y0), states.tab(y0), cities.tab(y0)]


def scripted_loc(states_table: StateTable, keys: set[int]) -> str:
    """Return the scripted localisation file.

    Args:
        states_table: State table.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        Contents of :data:`SCRIPTED_LOC_FILE`.
    """
    return "".join(
        [
            GEN_HEADER,
            (
                "# Scripted localisation. Always called with an explicit ROOT "
                "(player country / effect ROOT).\n\n"
            ),
            slot_tables([*BUFFERS, *cities.VP_NAME_BUFFERS]),
            cities.province_digit_loc(),
            cities.vp_name_loc(states_table, keys),
            input_window.key_label_loc(),
            input_window.target_type_loc(),
            country.status_loc(),
            cities.vp_row_loc(),
            cooldown.tooltip_loc(),
        ]
    )


def effects(states_table: StateTable) -> str:
    """Return the generated scripted effects file.

    Args:
        states_table: State table.

    Returns:
        Contents of :data:`EFFECTS_FILE`.
    """
    return "".join(
        [
            GEN_HEADER,
            "# Generated scripted effects (country scope = player ROOT).\n\n",
            cities.load_selected_state_effect(states_table),
            cities.vp_name_effects(),
            input_window.apply_input_effect(),
            "\n",
            cooldown.effects(),
            "\n",
            refresh.touch_effect(),
            "\n",
            cities.reset_vp_effect(),
            "\n",
            country.apply_country_name_effect(),
        ]
    )


def generated_triggers() -> str:
    """Return the scripted triggers that the hand-written files do not define.

    Returns:
        Contents of :data:`TRIGGERS_FILE`: the state and city cooldown triggers and
        ``rn_editor_bridge_available``.
    """
    return GEN_HEADER + cooldown.triggers() + "\n" + inline_editor.bridge_gate_trigger()


def scripted_gui() -> str:
    """Return the complete scripted GUI file.

    Returns:
        Contents of :data:`SCRIPTED_GUI_FILE`: the four tab GUIs, the input window
        GUI with every keyboard key, and the state view panel GUI.
    """
    return (
        GEN_HEADER
        + "# Rename Anything scripted GUIs. Every state change happens in these button effects\n"
        "# on the clicking player's own country (ROOT). "
        "Two-client MP verification is still required.\n\n"
        "scripted_gui = {\n"
        + main_window.scripted_guis(tabs())
        + "\n"
        + input_window.input_gui()
        + "\n"
        + legacy_field.field_gui()
        + "\n"
        + states.state_view_gui()
        + "}\n"
    )


def gui() -> str:
    """Return the interface ``.gui`` file.

    Returns:
        Contents of :data:`GUI_FILE`: the tab windows, the list row templates, the
        input window and the state view panel.
    """
    parts = [GEN_HEADER, "guiTypes = {\n", main_window.windows(tabs())]
    parts += characters.list_entry()
    parts += states.list_entry()
    parts += cities.list_entry()
    parts += input_window.target_entry()
    parts.append("\n")
    parts += input_window.input_window()
    parts += legacy_field.field_window()
    parts += states.state_view_window()
    parts.append("}\n")
    return "".join(parts)


def write_all(sink: OutputSink, states_table: StateTable, keys: set[int]) -> None:
    """Write every generated file.

    Args:
        sink: Destination of the files.
        states_table: State table, sorted by state ID.
        keys: Province IDs with a vanilla VP name key.
    """
    sink.write_text(SCRIPTED_LOC_FILE, scripted_loc(states_table, keys))
    sink.write_text(TRIGGERS_FILE, generated_triggers())
    sink.write_text(EFFECTS_FILE, effects(states_table))
    sink.write_text(SCRIPTED_GUI_FILE, scripted_gui())
    sink.write_text(GUI_FILE, gui())
    sink.write_text(GFX_FILE, textures.gen_gfx())
    sink.write_text(refresh.ON_ACTIONS_FILE, GEN_HEADER + refresh.on_actions())
    for name, data in textures.gen_textures().items():
        sink.write_bytes(f"{textures.TEXTURE_DIR}/{name}", data)
    for rel, text, bom in inline_editor.gen_inline_editor():
        sink.write_text(rel, text, bom=bom)
    for lang in LANGS:
        loc_dir = f"localisation/{lang}"
        sink.write_text(
            f"{loc_dir}/rename_anything_l_{lang}.yml", localisation.ui_loc(lang), bom=True
        )
        sink.write_text(
            f"{loc_dir}/rename_anything_chars_l_{lang}.yml",
            localisation.chars_loc(lang, states_table, keys),
            bom=True,
        )


def summary(states_table: StateTable, keys: set[int]) -> str:
    """Return the one-line summary the generator prints.

    Args:
        states_table: State table.
        keys: Province IDs with a vanilla VP name key.

    Returns:
        State, VP and unnamed VP counts.
    """
    nvp = sum(len(v) for v in states_table.values())
    with_vps = sum(bool(v) for v in states_table.values())
    without_key = sum(1 for v in states_table.values() for p in v if p not in keys)
    return (
        f"states: {len(states_table)}, states with VPs: {with_vps}, VP slots: {nvp}, "
        f"VPs without loc key: {without_key}"
    )
