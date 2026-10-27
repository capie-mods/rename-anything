"""Checks of the generated ``mod/`` files: generator output, legacy editor, wording, names."""

from __future__ import annotations

import re
from typing import Any

from inline_checks.constants import MOD, REPO, SOURCE
from inline_checks.tree import declarations, get, legacy, models_of, then, walk
from modgen.common import LANGS
from modgen.features.cooldown import COOLDOWN_DAYS
from modgen.features.inline_editor import gen_inline_editor
from modgen.ui_strings import UI


def check_generated_mod() -> None:
    """Check that ``mod/`` holds exactly the generator output and the shared constant."""
    produced = gen_inline_editor()
    assert len(produced) == len({rel for rel, _, _ in produced})
    for rel, text, bom in produced:
        data = (MOD / rel).read_bytes()
        assert data == (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"), rel
    languages = set(LANGS)
    stems = {
        rel.split("/")[-1].rsplit("_l_", 1)[0]
        for rel, _, _ in produced
        if rel.startswith("localisation/")
    }
    for stem in stems:
        keysets = {}
        for lang in languages:
            text = (MOD / "localisation" / lang / f"{stem}_l_{lang}.yml").read_text(
                encoding="utf-8-sig"
            )
            assert text.startswith(f"l_{lang}:"), (stem, lang)
            keysets[lang] = set(re.findall(r'^ (\S+?):\d* "', text, re.MULTILINE))
        assert all(keys == keysets["english"] for keys in keysets.values()), stem
    days = str(COOLDOWN_DAYS)
    inline_effects = declarations(MOD / "common" / "scripted_effects", "rn_inline_*.txt")
    # Default branch of the rename cooldown rule = COOLDOWN_DAYS; the legacy cooldown reads the same length.
    assert ("else", "=", [("set_temp_variable", "=", [("rn_ip_cd_days", "=", days)])]) in inline_effects[
        "rn_ip_cooldown_days"
    ]
    assert legacy("common/scripted_effects")["rn_cd_days"] == [
        ("rn_ip_cooldown_days", "=", "yes"),
        ("set_temp_variable", "=", [("rn_cd_days", "=", "temp_var:rn_ip_cd_days")]),
    ]
    assert "@RN_" not in "".join(p.read_text(encoding="utf-8-sig") for p in MOD.rglob("*.txt"))
    assert not any("ieaqa" in p.name or "ieqa" in p.name for p in MOD.rglob("*.yml"))


def check_legacy_editor() -> None:
    """Check the old editor: entry, cooldown gates, bridge gate and the Characters decision."""
    sg = (MOD / "common" / "scripted_guis" / "rename_anything_scripted_gui.txt").read_text(
        encoding="utf-8-sig"
    )
    gui = (MOD / "interface" / "rename_anything.gui").read_text(encoding="utf-8-sig")
    assert "rn_entry" not in sg
    assert "rn_entry" not in gui
    assert "rn_sv_cities_click" in sg
    models = models_of(MOD / "common" / "scripted_guis", "rename_anything_*.txt")
    effects = legacy("common/scripted_effects")
    country = models["rn_main_country_gui"]
    setter_limit = get(get(effects["rn_apply_country_name"], "if"), "limit")
    bridge = ("rn_editor_bridge_available", "=", "yes")
    no_country_cd = ("NOT", "=", [("rn_ip_cooldown_active_country", "=", "yes")])
    # The refresh gate bump (ROOT = { rn_gui_touch }) comes last and changes no game state.
    assert get(get(country, "effects"), "rn_country_apply_click") == [
        (
            "if",
            "=",
            [
                ("limit", "=", [bridge, no_country_cd, *setter_limit]),
                ("rn_apply_country_name", "=", "yes"),
                ("rn_ip_cooldown_start_country", "=", "yes"),
            ],
        ),
        ("ROOT", "=", [("rn_gui_touch", "=", "yes")]),
    ], "legacy country Apply: one branch for setter and cooldown start"
    enabled = get(get(country, "triggers"), "rn_country_apply_click_enabled")
    assert bridge in enabled
    assert no_country_cd in enabled
    assert get(get(country, "triggers"), "rn_leader_rename_click_enabled") == [
        ("NOT", "=", [("rn_ip_cooldown_active_leader", "=", "yes")]),
        ("NOT", "=", [("rn_feature_leader_off", "=", "yes")]),
    ]
    assert ("NOT", "=", [("rn_feature_country_off", "=", "yes")]) in enabled
    leader_row = ("var:rn_row_character", "=", [("is_country_leader", "=", "yes")])
    chars = get(models["rn_main_chars_gui"], "triggers")
    other_row = ("var:rn_row_character", "=", [("NOT", "=", [("is_country_leader", "=", "yes")])])
    assert get(chars, "rn_char_rename_click_enabled") == [
        ("NOT", "=", [("AND", "=", [leader_row, ("rn_ip_cooldown_active_leader", "=", "yes")])]),
        ("NOT", "=", [("AND", "=", [leader_row, ("rn_feature_leader_off", "=", "yes")])]),
        ("NOT", "=", [("AND", "=", [other_row, ("rn_feature_characters_off", "=", "yes")])]),
    ]
    assert 'pdx_tooltip = "RN_CHAR_RENAME_TT"' in gui
    check_legacy_apply_input(effects)
    check_decision()


def check_legacy_apply_input(effects: dict[str, Any]) -> None:
    """Check the cooldown gates inside the legacy ``rn_apply_input``.

    Args:
        effects: Legacy mod effects.
    """
    branches = get(effects["rn_apply_input"], "if")
    characters = next(
        v
        for k, _, v in branches
        if k == "if" and ("check_variable", "=", [("rn_ttype", "=", "1")]) in get(v, "limit")
    )
    row = get(get(characters, "for_each_scope_loop"), "if")
    assert (
        "OR",
        "=",
        [
            ("NOT", "=", [("is_country_leader", "=", "yes")]),
            ("ROOT", "=", [("NOT", "=", [("rn_ip_cooldown_active_leader", "=", "yes")])]),
        ],
    ) in get(row, "limit")
    assert (
        "if",
        "=",
        [
            ("limit", "=", [("is_country_leader", "=", "yes")]),
            ("ROOT", "=", [("rn_ip_cooldown_start_leader", "=", "yes")]),
        ],
    ) in row
    for ttype, active, start in (
        ("2", "rn_cd_state_active", "rn_cd_state_start"),
        ("3", "rn_cd_vp_active", "rn_cd_vp_start"),
    ):
        branch = next(
            v
            for k, _, v in branches
            if k == "else_if"
            and ("check_variable", "=", [("rn_ttype", "=", ttype)]) in get(v, "limit")
        )
        assert ("NOT", "=", [(active, "=", "yes")]) in get(branch, "limit"), ttype
        assert ("NOT", "=", [("rn_feature_states_off", "=", "yes")]) in get(branch, "limit")
        assert ("ROOT", "=", [(start, "=", "yes")]) in list(walk(branch)), ttype


def check_decision() -> None:
    """Check the free decision that opens the editor on the Characters tab."""
    category = declarations(MOD / "common" / "decisions")["rn_entry_layout"]
    decision = get(category, "rn_open_name_editor")
    assert get(decision, "cost") == "0"
    assert get(decision, "fire_only_once") == "no"
    assert get(decision, "icon") == "generic_political_discourse"
    effect = get(get(decision, "complete_effect"), "if")
    assert then(effect) == [
        ("rn_open_main", "=", "yes"),
        ("set_temp_variable", "=", [("rn_newtab", "=", "2")]),
        ("rn_set_tab", "=", "yes"),
    ]
    for flag in (
        "rn_open",
        "rn_input",
        "rn_ip_leader_open",
        "rn_ip_party_neutrality_open",
        "rn_ip_country_open",
    ):
        assert ("NOT", "=", [("has_country_flag", "=", flag)]) in get(effect, "limit")


def check_voice() -> None:
    """Check the player-facing wording against the design system's voice rules.

    No dash used as punctuation, straight quotes in English, no internal words
    (DLL, bridge, epoch, payload, hook, RN1, plugin, extension) and no
    "okres karencji" in the in-place editor strings and the legacy UI strings.
    """
    words = r"\b(DLL|bridge|epoch|payload|hook|RN1|plugin|extension)\b"
    internal = re.compile(words, re.IGNORECASE)
    texts: dict[str, str] = {}
    for lang in ("english", "polish"):
        for path in (SOURCE / "localisation" / lang).glob("*.yml"):
            for key, value in re.findall(
                r'^ (\S+?):\d* "(.*)"$', path.read_text(encoding="utf-8-sig"), re.MULTILINE
            ):
                texts[f"{lang}:{key}"] = value
    for key, (english, polish) in UI.items():
        texts[f"english:{key}"] = english
        texts[f"polish:{key}"] = polish
    for key, value in texts.items():
        assert not re.search("[\u2012-\u2015]", value), ("dash", key)
        assert not internal.search(value), ("internal word", key)
        assert "karencj" not in value.lower(), ("officialese", key)
        if key.startswith("english:"):
            assert not re.search("[\u2018\u2019\u201c\u201d\u201e]", value), ("quotes", key)


def check_native_names() -> None:
    """Check the bridge gate trigger and every render bridge name in the generated files."""
    assert "rn_editor_bridge_available" in legacy("common/scripted_triggers")
    bridge = (REPO / "plugin" / "probes" / "inline_editor_render_bridge.cpp").read_text(
        encoding="utf-8"
    )
    names = set(re.findall(r'"(rn_ip_[a-z_]+)"', bridge))
    assert names, "no rn_ip_* names found in the render bridge"
    generated = "".join(
        p.read_text(encoding="utf-8-sig")
        for p in [
            *(MOD / "interface").glob("rn_*.gui"),
            *(MOD / "common" / "scripted_guis").glob("rn_*.txt"),
        ]
    )
    for name in names:
        pattern = r"\b" + re.escape(name.removesuffix("_click")) + r"\b"
        assert re.search(pattern, generated), ("bridge name missing in mod", name)
