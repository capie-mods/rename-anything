#!/usr/bin/env python3
"""Check the in-place editor source and its generated copy in ``mod/``.

The in-place editor (country name and adjective, leader, the four base party
groups) lives in ``tools/inline_editor/``. ``tools/gen.py`` copies it into
``mod/`` and adds the parts that depend on the rest of the mod. This script is
the test for that pair. It replaces ``probes/rn_inline_editor_product_qa/check.py``,
which belonged to the retired product fixture.

What it checks:

* Generator output. Every file that ``gen_inline_editor()`` produces must be in
  ``mod/`` byte for byte, all ten languages must have the same keys, the single
  cooldown constant must reach both cooldown effects, and no ``@RN_`` token may
  be left over.
* Native contract. Every ``rn_ip_*`` name that the render bridge
  (``plugin/probes/inline_editor_render_bridge.cpp``) looks up must exist in the
  generated GUI and scripted GUI files.
* Legacy editor. The country Apply and the leader rename of the old editor must
  respect the same cooldowns and the editor bridge signal, the leader row in the
  character list is disabled during the leader cooldown, the global entry button
  is gone and the decision that opens the Characters tab is present.
* Script structure. Guards, the party tabs, the cooldown, the status line, the
  caption revision counters and the party carriers are compared with the
  expected parse trees.
* Geometry. Rectangles taken from the GUI tree: Apply and Cancel do not overlap,
  fields sit inside their frames and are wide enough for 32 of the widest glyphs,
  windows stay inside the politics panel, only the Apply buttons have a
  shortcut and none of them is ESCAPE.
* Limited execution. The ApplyVM from ``probes/rn_inline_pair_apply_source``
  runs the real party and country Apply paths: all four groups under every
  government, the I4-M1 placeholder, the tabs, the cooldown, the missing-bridge
  status, the caption counters and a set of rejection mutations. Contract
  mutations of the parse trees must each be caught by the structural checks.

This is a static, offline test. It is not the HOI4 parser and it does not
prove anything about the game, the native bridge or multiplayer. Run it after
``tools/gen.py``::

    uv run python tools/tests/check_inline_editor.py

It prints a JSON summary and exits with 0, or prints ``FAIL: ...`` and exits
with 1.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from types import ModuleType

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
"""Repository root (two levels above ``tools/tests/``)."""

SOURCE = REPO / "tools" / "inline_editor"
"""In-place editor source that ``tools/gen.py`` copies into ``mod/``."""

MOD = REPO / "mod"
"""Generated mod folder."""

APPLY_QA = REPO / "probes" / "rn_inline_editor_apply_qa"
"""Retired fixture whose party buffer table must stay byte-identical to the source."""

GROUPS = [(1, "democratic"), (2, "communism"), (3, "fascism"), (4, "neutrality")]
"""Logical party group number and HOI4 base ideology group."""

GROUP_KEYS = ["DEMOCRATIC", "COMMUNISM", "FASCISM", "NEUTRALITY"]
"""Suffix of the per-group short-name localisation keys, in :data:`GROUPS` order."""

PAYLOAD_HASHES = {
    "rn_inline_payload.txt": "CD171D6203BD66DC7905C7C3D0E1A2750C4B8EABAB45F0540D75D3AF2CE10800",
    "rn_inline_pair_payload.txt": (
        "E278DFAC3A4E3AC5CCCA7D7CF74DA9D87F0DE728D30BCA875D543F24956F6FC7"
    ),
}
"""SHA-256 (LF line endings) of the payload validators; they must never change."""

BIG_ICON_SPRITES = {"GFX_edit_designer_notes_button", "GFX_preset_button_save"}
"""Vanilla sprites with 30x30 frames that ignore ``size`` and must use ``scale``."""

FONT_WIDEST = {"hoi_18": 11, "hoi_16mbs": 12}
"""Largest glyph advance in pixels over the 84-character alphabet (vanilla ``.fnt``)."""

LEADER_NAME = (18, 262, 173, 298)
"""Vanilla ``leader_name`` text box in the politics panel (left, top, right, bottom)."""

RULING_PARTY_INFO = (88, 305, 343, 365)
"""Vanilla ``ruling_party_info`` box in the politics panel."""

PIE_CHART_X = 270
"""Left edge of the vanilla party pie chart."""

ACTIONS_Y = 383
"""Top of the vanilla bottom decoration above the occupied/subjects/collaboration buttons."""

PANEL_WIDTH = 550
"""Width of the vanilla politics panel."""

RULES_ICON_X = 460
"""Left edge of the vanilla rules icon on the politics title line."""

TITLE_LINE_BOTTOM = 30
"""Lowest y the country pencil may reach to stay on the politics title line."""

MAX_NAME = 32
"""Transport limit of one name field in characters."""

VM_TODAY = 1000
"""``global.num_days`` used by every ApplyVM case."""

VM_EPOCH = 7
"""Opening epoch (and fresh command epoch) of the base ApplyVM state."""

REV_CAP = 999
"""Highest caption revision counter value; the native bridge refuses Apply at it."""

ERR_CLOSED = 7
"""Guard error: editor closed, legacy editor open or wrong country."""

ERR_EPOCH = 8
"""Guard error: missing or stale command epoch."""

ERR_TARGET = 9
"""Guard error: pin or party group does not match."""

ERR_CAPABILITY = 10
"""Country guard error: no fresh native country capability."""

ERR_COOLDOWN = 11
"""Guard error: the rename cooldown of this type is active."""

STATUS_NO_BRIDGE = 12
"""Status code shown when Apply arrived without the editor bridge."""

ERR_NATIVE = 1
"""Validator error: the native encoder rejected the field (ok = 0)."""

ERR_CODE = 5
"""Validator error: a character code outside 1..84."""


def _load(name: str, path: Path) -> ModuleType:
    """Import a Python file by path.

    Args:
        name: Module name to register.
        path: File to import.

    Returns:
        The executed module.

    Raises:
        ImportError: The file cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VM_MODULE = _load("inline_apply_vm", REPO / "probes" / "rn_inline_pair_apply_source" / "check.py")
"""Limited ApplyVM and Paradox-script parser shared with the fixture checkers."""

GEN = _load("rn_gen", REPO / "tools" / "gen.py")
"""The mod generator, imported for its constants and ``gen_inline_editor``."""

parse = VM_MODULE.parse
ApplyVM = VM_MODULE.ApplyVM
Country = VM_MODULE.Country

_ENCODER = (REPO / "plugin" / "src" / "editor_input.hpp").read_text(encoding="utf-8")
"""Text of the native encoder header that defines the accepted alphabet."""
NATIVE_ALPHABET = "".join(
    re.findall(
        r'U"([^"]*)"',
        _ENCODER[
            _ENCODER.index("constexpr std::u32string_view alphabet") : _ENCODER.index(
                "constexpr std::u32string_view delimiters"
            )
        ],
    )
)
"""The 84 characters the native encoder accepts, read from the real C++ source."""


# ----------------------------------------------------------------------------- parse-tree helpers


def sha(path: Path) -> str:
    """Return the upper-case SHA-256 of a text file with CRLF folded to LF.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest().upper()


def get(nodes: list[Any], key: str) -> Any:  # noqa: ANN401 - untyped parse-tree value
    """Return the value of the only node with this key.

    Args:
        nodes: Parse-tree nodes ``(key, operator, value)``.
        key: Key to look up.

    Returns:
        The node value (a string or a nested node list).
    """
    found = [v for k, _, v in nodes if k == key]
    assert len(found) == 1, ("expected singleton", key, len(found))
    return found[0]


def walk(nodes: list[Any]) -> Iterator[Any]:
    """Yield every node of a parse tree, depth first.

    Args:
        nodes: Parse-tree nodes.

    Yields:
        Each ``(key, operator, value)`` node.
    """
    for node in nodes:
        yield node
        if isinstance(node[2], list):
            yield from walk(node[2])


def tokens(nodes: list[Any]) -> set[str]:
    """Return every string value in a parse tree.

    Args:
        nodes: Parse-tree nodes.

    Returns:
        The set of string values.
    """
    return {v for _, _, v in walk(nodes) if isinstance(v, str)}


def named(nodes: list[Any]) -> dict[str, Any]:
    """Map every GUI element name to its node list.

    Args:
        nodes: Parsed GUI tree.

    Returns:
        Element name to element body.
    """
    return {
        get(v, "name"): v
        for _, _, v in walk(nodes)
        if isinstance(v, list) and any(k == "name" for k, _, _ in v)
    }


def then(nodes: list[Any]) -> list[Any]:
    """Return the nodes of a block without its ``limit``.

    Args:
        nodes: Body of an ``if`` block.

    Returns:
        Every node except ``limit``.
    """
    return [n for n in nodes if n[0] != "limit"]


def success_if(nodes: list[Any]) -> list[Any]:
    """Return the body of the first ``if`` that requires a zero error code.

    Args:
        nodes: Effect body.

    Returns:
        The ``if`` body without its ``limit``.
    """
    out = next(value for key, _, value in nodes if key == "if")
    assert get(get(out, "limit"), "check_variable") in (
        [("temp_var:rn_pair_err", "=", "0")],
        [("temp_var:rn_ip_leader_error", "=", "0")],
    ), "unguarded success branch"
    return then(out)


def declarations(folder: Path, pattern: str = "*.txt") -> dict[str, Any]:
    """Parse every top-level declaration of the matching script files.

    The ``@RN_COOLDOWN_DAYS@`` token of the source is replaced exactly as
    ``tools/gen.py`` does it.

    Args:
        folder: Folder to read.
        pattern: Glob pattern of the files.

    Returns:
        Declaration name to body.
    """
    result: dict[str, Any] = {}
    for path in sorted(folder.glob(pattern)):
        text = path.read_text(encoding="utf-8-sig").replace(
            "@RN_COOLDOWN_DAYS@", str(GEN.COOLDOWN_DAYS)
        )
        for name, _, body in parse(text):
            assert name not in result, ("duplicate declaration", name, path)
            result[name] = body
    return result


def models_of(folder: Path, pattern: str = "*.txt") -> dict[str, Any]:
    """Parse every scripted GUI model of the matching files.

    Args:
        folder: ``common/scripted_guis`` folder.
        pattern: Glob pattern of the files.

    Returns:
        Model name to model body.
    """
    return {
        name: body
        for path in sorted(folder.glob(pattern))
        for _, _, outer in parse(path.read_text(encoding="utf-8-sig"))
        for name, _, body in outer
    }


def legacy(folder: str) -> dict[str, Any]:
    """Parse the declarations of the legacy generated ``rename_anything_*`` files.

    Args:
        folder: Folder relative to ``mod/``.

    Returns:
        Declaration name to body.
    """
    return declarations(MOD / folder, "rename_anything_*.txt")


# ----------------------------------------------------------------------------- structural checks


def check_models(models: dict[str, Any], triggers: dict[str, Any]) -> dict[str, Any]:
    """Check the model set, the subject placeholder and the per-model guards.

    Args:
        models: Source scripted GUI models.
        triggers: Source scripted triggers.

    Returns:
        The six politics models (without the subject placeholder).
    """
    assert set(models) == {
        "rn_ip_leader_launcher_gui",
        "rn_ip_leader_gui",
        "rn_ip_party_neutrality_launcher_gui",
        "rn_ip_party_neutrality_gui",
        "rn_ip_country_launcher_gui",
        "rn_ip_country_gui",
        "rn_ip_subject_gui",
    }
    subject = models["rn_ip_subject_gui"]
    assert get(subject, "context_type") == "diplomacy_target_context"
    assert ("rn_ip_subject_rename_enabled", "=", "yes") in get(subject, "visible")
    assert triggers["rn_ip_subject_rename_enabled"] == [("always", "=", "no")]
    assert triggers["rn_ip_subject_country_capability"] == [("always", "=", "no")]
    country_enabled = get(get(subject, "triggers"), "rn_ips_country_click_enabled")
    assert ("rn_ip_subject_country_capability", "=", "yes") in country_enabled
    assert all([k for k, _, _ in body] == ["log"] for _, _, body in get(subject, "effects"))
    politics = {k: v for k, v in models.items() if k != "rn_ip_subject_gui"}
    for name, body in politics.items():
        assert get(body, "context_type") == "player_context"
        assert get(body, "parent_window_token") == "politics_tab"
        assert get(body, "ai_enabled") == [("always", "=", "no")]
        assert ("rn_editor_bridge_available", "=", "yes") in get(body, "visible")
        enabled = [v for k, _, v in get(body, "triggers") if k.endswith("_enabled")]
        for branch in [get(body, "visible"), *enabled]:
            resolved = (
                triggers["rn_ipp_party_target_matches"]
                if branch == [("rn_ipp_party_target_matches", "=", "yes")]
                else branch
            )
            assert ("tag", "=", "ROOT") in resolved, ("own country guard", name)
            assert ("is_ai", "=", "no") in resolved, ("own country guard", name)
            assert not any(v == "POL" for _, _, v in walk(branch)), name
        for key, _, trig in get(body, "triggers"):
            if key.endswith("_apply_click_enabled"):
                symbols = tokens(trig) | {k for k, _, _ in walk(trig)}
                assert not any("temp_var:" in v or "rn_native_" in v for v in symbols)
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in get(body, "visible")
    return politics


def check_callbacks(models: dict[str, Any]) -> None:
    """Check the Open, Apply and Cancel callbacks and the caption revision counters.

    Args:
        models: The six politics models.
    """
    kinds = {
        "leader": ("rn_ip_leader", "rn_inline_leader", "rn_ip_lui_rev", "rn_ip_leader_error"),
        "party": ("rn_ip_party_neutrality", "rn_inline_pair", "rn_ip_pui_rev", "rn_pair_err"),
        "country": ("rn_ip_country", "rn_inline_pair", None, "rn_pair_err"),
    }
    for kind, (prefix, helper_prefix, rev, err) in kinds.items():
        editor = models[prefix + "_gui"]
        launcher = models[prefix + "_launcher_gui"]
        assert get(editor, "window_name") == prefix + "_window"
        assert get(launcher, "window_name") == prefix + "_launcher_window"
        suffix = "" if kind == "leader" else "_" + kind
        open_helper = f"{helper_prefix}_open{suffix}"
        cancel_helper = f"{helper_prefix}_cancel{suffix}"
        apply_helper = f"{helper_prefix}_apply{suffix}"
        status = "rn_ip_status_record_" + ("leader" if kind == "leader" else "pair")
        open_click = get(get(launcher, "effects"), prefix + "_open_click")
        cancel_click = get(get(editor, "effects"), prefix + "_cancel_click")
        apply_click = get(get(editor, "effects"), prefix + "_apply_click")
        assert cancel_click == [(cancel_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in get(
                get(launcher, "triggers"), prefix + "_open_click_enabled"
            )
        if rev is None:
            assert open_click == [(open_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
            assert [k for k, _, _ in apply_click] == ["log", apply_helper, status, "log"]
        else:
            # Caption revision counter: explicit 0 before the first opening, +1 only after a
            # successful Apply, capped at REV_CAP, hidden carriers in launcher and editor.
            init = ("if", "=", [("limit", "=", [("NOT", "=", [("has_variable", "=", rev)])])])
            assert open_click[0][:2] == init[:2]
            assert open_click[0][2][0] == init[2][0]
            assert open_click[1:] == [(open_helper, "=", "yes"), ("rn_ip_status_clear", "=", "yes")]
            assert [k for k, _, _ in apply_click] == ["log", apply_helper, "if", status, "log"]
            assert apply_click[2] == (
                "if",
                "=",
                [
                    (
                        "limit",
                        "=",
                        [
                            ("check_variable", "=", [(f"temp_var:{err}", "=", "0")]),
                            ("check_variable", "=", [(rev, "<", str(REV_CAP))]),
                        ],
                    ),
                    ("add_to_variable", "=", [(rev, "=", "1")]),
                ],
            )
            for model in (editor, launcher):
                assert get(get(model, "triggers"), prefix + "_rev_visible") == [
                    ("always", "=", "no")
                ]
        assert "before" in apply_click[0][2]
        assert "after" in apply_click[-1][2]
        assert "PASS" not in apply_click[-1][2]
        cancel_enabled = get(get(editor, "triggers"), prefix + "_cancel_click_enabled")
        assert not any(k == "has_government" for k, _, _ in walk(cancel_enabled))


def check_exclusive_open(effects: dict[str, Any]) -> None:
    """Check that at most one in-place editor (one Enter target) can be open.

    Args:
        effects: Source scripted effects.
    """
    flags = ["rn_ip_leader_open", "rn_ip_country_open", "rn_ip_party_neutrality_open"]
    for helper, need in (
        ("rn_inline_pair_open_country", flags),
        ("rn_inline_pair_open_party", flags),
        ("rn_inline_leader_open", flags[:2]),
    ):
        limit = get(get(effects[helper], "if"), "limit")
        assert all(("NOT", "=", [("has_country_flag", "=", f)]) in limit for f in need), helper
    leader_open = list(walk(effects["rn_inline_leader_open"]))
    assert ("clr_country_flag", "=", "rn_ip_party_neutrality_open") in leader_open


def check_tabs(effects: dict[str, Any], party: list[Any]) -> None:
    """Check the party tab switch helper and the four tab buttons.

    Args:
        effects: Source scripted effects.
        party: The party editor model.
    """
    switch = get(effects["rn_inline_pair_switch_party"], "if")
    limit = get(switch, "limit")
    for need in (
        ("has_country_flag", "=", "rn_ip_party_neutrality_open"),
        ("NOT", "=", [("rn_ip_cooldown_active_party", "=", "yes")]),
        (
            "NOT",
            "=",
            [("check_variable", "=", [("rn_ip_party_group", "=", "temp_var:rn_ip_party_tab")])],
        ),
    ):
        assert need in limit, ("tab switch guard", need)
    assert then(switch) == [
        ("clear_array", "=", "rn_ip_party_target"),
        ("add_to_array", "=", [("rn_ip_party_target", "=", "THIS")]),
        ("set_variable", "=", [("rn_ip_party_group", "=", "temp_var:rn_ip_party_tab")]),
        ("add_to_variable", "=", [("rn_ip_epoch", "=", "1")]),
    ], "tab switch = re-pin + group + new epoch only"
    for i, _ in GROUPS:
        assert get(get(party, "effects"), f"rn_ipp_tab_{i}_click") == [
            ("set_temp_variable", "=", [("rn_ip_party_tab", "=", str(i))]),
            ("rn_inline_pair_switch_party", "=", "yes"),
            ("rn_ip_status_clear", "=", "yes"),
        ]
        enabled = get(get(party, "triggers"), f"rn_ipp_tab_{i}_click_enabled")
        assert ("NOT", "=", [("check_variable", "=", [("rn_ip_party_group", "=", str(i))])]) in (
            enabled
        )
        assert ("has_country_flag", "=", "rn_ip_party_neutrality_open") in enabled


def group_gate(nodes: list[Any]) -> None:
    """Check the pinned-group gate: groups 1..4, no government condition.

    Args:
        nodes: Trigger or guard body.
    """
    want = (
        "OR",
        "=",
        [("check_variable", "=", [("rn_ip_party_group", "=", str(i))]) for i, _ in GROUPS],
    )
    assert list(walk(nodes)).count(want) == 1, "missing or different exact pinned-group gate"
    assert not any(k == "has_government" for k, _, _ in walk(nodes)), "any base group is allowed"


def check_guards(effects: dict[str, Any], triggers: dict[str, Any]) -> None:
    """Check the guards and the two-round Apply structure of the three editors.

    Args:
        effects: Source scripted effects plus the legacy mod effects.
        triggers: Source scripted triggers.
    """
    group_gate(triggers["rn_ipp_party_target_matches"])
    group_gate(effects["rn_inline_pair_guard_party"])
    for kind in ("party", "country", "leader"):
        name = "rn_inline_leader_guard" if kind == "leader" else "rn_inline_pair_guard_" + kind
        guard = list(walk(effects[name]))
        VM_MODULE.pure_audit(effects, name)
        assert ("tag", "=", "ROOT") in guard
        for flag in ("rn_open", "rn_input"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in guard
        assert ("check_variable", "=", [("temp_var:rn_ip_cmd_epoch", "=", "rn_ip_epoch")]) in guard
        assert ("check_variable", "=", [("rn_ip_epoch", ">", "0")]) in guard
        assert any(k == "round_temp_variable" for k, _, _ in guard)
    for kind in ("party", "country"):
        body = effects["rn_inline_pair_apply_" + kind]
        assert body[0] == ("rn_inline_pair_guard_" + kind, "=", "yes")
        first = success_if(body)
        assert first[0] == ("rn_inline_pair_validate", "=", "yes")
        second = success_if(first)
        assert second[0] == body[0]
        if kind == "party":
            check_party_branches(success_if(second))
    leader = effects["rn_inline_leader_apply"]
    assert leader[0] == ("rn_inline_leader_guard", "=", "yes")
    first = success_if(leader)
    assert first[:2] == [
        ("rn_inline_validate_payload", "=", "yes"),
        ("set_temp_variable", "=", [("rn_ip_leader_error", "=", "temp_var:rn_inline_error")]),
    ]
    second = success_if(first)
    assert second[0] == leader[0]
    final = success_if(second)
    assert final[1] == ("rn_inline_leader_refresh", "=", "yes")
    assert ("check_variable", "=", [("rn_ip_leader_current^num", "=", "1")]) in list(walk(final))
    assert len([n for n in walk(leader) if n[0] == "set_character_name"]) == 1
    assert not any(v == "POL" or v.startswith("POL_") for b in effects.values() for v in tokens(b))
    copies = [
        n for b in effects.values() for n in walk(b) if n[0] == "rn_inline_party_copy_validated"
    ]
    assert len(copies) == len(GROUPS)


def check_party_branches(final: list[Any]) -> None:
    """Check the four literal ``set_party_name`` branches of the party Apply.

    Args:
        final: Body after the second guard round.
    """
    branches = [v for k, _, v in final if k in {"if", "else_if"}]
    assert len(branches) == len(GROUPS)
    for branch, (i, group) in zip(branches, GROUPS, strict=True):
        assert get(branch, "limit") == [
            ("check_variable", "=", [("rn_ip_party_group", "=", str(i))])
        ]
        commands = then(branch)
        assert [k for k, _, _ in commands] == [
            "rn_inline_party_copy_validated",
            "meta_effect",
            "rn_inline_party_finish",
        ]
        setter = get(get(commands[1][2], "text"), "set_party_name")
        assert setter == [("ideology", "=", group), ("name", "=", "[S]"), ("long_name", "=", "[L]")]
        for token, prefix in (("S", "PS"), ("L", "PL")):
            want = "".join(f"[ROOT.RN_{prefix}_{slot}]" for slot in range(MAX_NAME))
            assert get(commands[1][2], token) == want


def check_status(
    effects: dict[str, Any], models: dict[str, Any], triggers: dict[str, Any], locs: dict[str, Any]
) -> None:
    """Check the status-line branches and that status variables stay display-only.

    Args:
        effects: Source scripted effects.
        models: The six politics models.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    party_status = [n for n in locs["RN_IPP_PARTY_STATUS"] if n[0] == "text"]
    assert [get(t[2], "localization_key") for t in party_status] == [
        "RN_IP_ERR_NO_BRIDGE",
        "RN_IP_ERR_CD_PARTY",
        "RN_IP_ERR_PARTY_SHORT",
        "RN_IP_ERR_PARTY_LONG_UNKNOWN",
        "RN_IP_ERR_PARTY_LONG",
        "RN_IP_LONG_NAME",
        "RN_IPP_LONG_UNKNOWN",
        "RN_IPP_TARGET_CHANGED",
    ]
    assert all(
        ("rn_ipp_party_target_matches", "=", "yes") in get(t[2], "trigger")
        for t in party_status[1:7]
    )
    assert [get(t[2], "localization_key") for t in locs["RN_IP_STATUS"] if t[0] == "text"] == [
        "RN_IP_HINT",
        "RN_IP_ERR_NO_BRIDGE",
        "RN_IP_ERR_CD_LEADER",
        "RN_IP_ERR_CD_COUNTRY",
        "RN_IP_ERR_STALE",
        "RN_IP_ERR_LEADER",
        "RN_IP_ERR_COUNTRY_ADJ",
        "RN_IP_ERR_COUNTRY_NAME",
    ]
    for name, body in effects.items():
        if not name.startswith("rn_ip_status_"):
            assert not any("rn_ip_status_" in str(n) for n in walk(body)), ("status read", name)
    for name, body in triggers.items():
        assert not any("rn_ip_status_" in str(n) for n in walk(body)), name
    for name, body in models.items():
        for key, _, trig in get(body, "triggers"):
            assert not any("rn_ip_status_" in str(n) for n in walk(trig)), (name, key)


def check_party_carriers(locs: dict[str, Any]) -> None:
    """Check the short and long party carriers (I4-M1 placeholder for non-ruling groups).

    Args:
        locs: Source scripted localisation.
    """
    for name, ruling in (
        ("RN_IPP_PARTY_SHORT", "RN_IPP_PARTY_SHORT_CURRENT"),
        ("RN_IPP_PARTY_LONG", "RN_IPP_PARTY_LONG_CURRENT"),
    ):
        texts = [n[2] for n in locs[name] if n[0] == "text"]
        matches = ("rn_ipp_party_target_matches", "=", "yes")
        want = [
            [
                (
                    "trigger",
                    "=",
                    [
                        matches,
                        ("check_variable", "=", [("rn_ip_party_group", "=", str(i))]),
                        ("has_government", "=", g),
                    ],
                ),
                ("localization_key", "=", ruling),
            ]
            for i, g in GROUPS
        ]
        for i, _ in GROUPS:
            key = (
                "RN_IPP_PARTY_SHORT_" + GROUP_KEYS[i - 1]
                if name == "RN_IPP_PARTY_SHORT"
                else "RN_IPP_LONG_PLACEHOLDER"
            )
            group = ("check_variable", "=", [("rn_ip_party_group", "=", str(i))])
            want.append([("trigger", "=", [matches, group]), ("localization_key", "=", key)])
        want.append([("localization_key", "=", "RN_IPP_EMPTY")])
        assert texts == want, ("party carrier branches", name)


def check_cooldown(
    effects: dict[str, Any], models: dict[str, Any], triggers: dict[str, Any], locs: dict[str, Any]
) -> None:
    """Check the single constant, the guards, the start points and the pencil gates.

    Args:
        effects: Source scripted effects.
        models: The six politics models.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    constants = [
        n
        for body in effects.values()
        for n in walk(body)
        if n[0] == "set_temp_variable" and n[2][0][0] == "rn_ip_cd_days"
    ]
    assert len(constants) == 1
    assert effects["rn_ip_cooldown_days"] == [
        ("set_temp_variable", "=", [("rn_ip_cd_days", "=", str(GEN.COOLDOWN_DAYS))])
    ]
    starters = {
        "country": "rn_inline_pair_apply_country",
        "leader": "rn_inline_leader_apply",
        "party": "rn_inline_party_finish",
    }
    openers = {
        "country": "rn_inline_pair_open_country",
        "leader": "rn_inline_leader_open",
        "party": "rn_inline_pair_open_party",
    }
    prefixes = {
        "country": "rn_ip_country",
        "leader": "rn_ip_leader",
        "party": "rn_ip_party_neutrality",
    }
    for k in ("country", "leader", "party"):
        active = f"rn_ip_cooldown_active_{k}"
        assert triggers[active] == [
            ("set_temp_variable", "=", [("rn_ip_cd_left", "=", f"rn_ip_cd_{k}_until")]),
            ("subtract_from_temp_variable", "=", [("rn_ip_cd_left", "=", "global.num_days")]),
            ("check_variable", "=", [("rn_ip_cd_left", ">", "0")]),
        ]
        start = effects[f"rn_ip_cooldown_start_{k}"]
        assert ("set_variable", "=", [(f"rn_ip_cd_{k}_until", "=", "global.num_days")]) in start
        guard = effects["rn_inline_leader_guard" if k == "leader" else "rn_inline_pair_guard_" + k]
        err = "rn_ip_leader_error" if k == "leader" else "rn_pair_err"
        assert guard[-1] == (
            "if",
            "=",
            [
                (
                    "limit",
                    "=",
                    [
                        ("check_variable", "=", [(f"temp_var:{err}", "=", "0")]),
                        (active, "=", "yes"),
                    ],
                ),
                ("set_temp_variable", "=", [(err, "=", str(ERR_COOLDOWN))]),
            ],
        ), ("cooldown guard", k)
        callers = [
            n
            for n, b in effects.items()
            if any(x[0] == f"rn_ip_cooldown_start_{k}" for x in walk(b))
        ]
        assert callers == [starters[k]], ("start callers", k, callers)
        assert ("NOT", "=", [(active, "=", "yes")]) in get(get(effects[openers[k]], "if"), "limit")
        launcher = models[prefixes[k] + "_launcher_gui"]
        enabled = get(get(launcher, "triggers"), prefixes[k] + "_open_click_enabled")
        assert ("NOT", "=", [(active, "=", "yes")]) in enabled, ("pencil not disabled", k)
        assert active not in str(get(launcher, "visible")), "pencil must stay visible"
        days = [
            get(x[2], "localization_key")
            for x in locs[f"RN_IP_CD_LEFT_{k.upper()}"]
            if x[0] == "text"
        ]
        assert days == [f"RN_IP_CD_DAYS_{n}" for n in range(1, 31)] + ["RN_IP_CD_DAYS_MORE"]
    tail = next(v for key, _, v in reversed(effects["rn_inline_leader_apply"]) if key == "if")
    assert get(tail, "limit") == [
        ("check_variable", "=", [("temp_var:rn_ip_leader_error", "=", "0")])
    ]
    assert ("rn_ip_cooldown_start_leader", "=", "yes") in tail


def check_widgets(gui: list[Any]) -> None:
    """Check fields, carriers, labels and run the geometry audit.

    Args:
        gui: Parsed source GUI files.
    """
    fields = {
        "rn_ip_leader_edit",
        "rn_ip_party_neutrality_edit",
        "rn_ip_party_neutrality_long_edit",
        "rn_ip_country_name_edit",
        "rn_ip_country_adj_edit",
    }
    assert {get(body, "name") for kind, _, body in walk(gui) if kind == "editBoxType"} == fields
    widgets = named(gui)
    label = widgets["rn_ip_country_label"]
    assert get(label, "font") == "hoi_18mbs"
    assert get(label, "format") == "right"
    assert get(label, "text") == "[ROOT.GetName]"
    lx, ly = xy(widgets["rn_ip_country_launcher_window"])
    bx, by = xy(widgets["rn_ip_country_open"])
    assert ly + by + 20 <= TITLE_LINE_BOTTOM
    assert lx + xy(label)[0] + int(get(label, "maxWidth")) <= lx + bx
    assert lx + bx + 20 <= RULES_ICON_X
    for kind in ("leader", "party_neutrality", "country"):
        assert get(widgets[f"rn_ip_{kind}_epoch"], "text") == "[?ROOT.rn_ip_epoch|0]"
    assert get(widgets["rn_ip_party_neutrality_prefill"], "text") == "[ROOT.RN_IPP_PARTY_SHORT]"
    assert get(widgets["rn_ip_party_neutrality_long_prefill"], "text") == "[ROOT.RN_IPP_PARTY_LONG]"
    assert get(widgets["rn_ip_party_neutrality_long_label"], "text") == "[ROOT.RN_IPP_PARTY_STATUS]"
    for status in ("rn_ip_leader_status", "rn_ip_country_status"):
        assert get(widgets[status], "text") == "[ROOT.RN_IP_STATUS]"
        assert get(widgets[status], "font") == "Arial12"
    revs = [
        b for k, _, b in walk(gui) if k == "instantTextboxType" and get(b, "name").endswith("_rev")
    ]
    assert (
        sorted(get(b, "text") for b in revs)
        == ["[?ROOT.rn_ip_lui_rev|0]"] * 2 + ["[?ROOT.rn_ip_pui_rev|0]"] * 2
    ), "caption counter carriers in both launchers and editors"
    geometry_audit(gui)


# ----------------------------------------------------------------------------- geometry


Rect = tuple[int, int, int, int]
"""Rectangle as (left, top, right, bottom) in politics panel coordinates."""


def xy(node: list[Any], key: str = "position") -> tuple[int, int]:
    """Return the two numbers of a ``position`` or ``size`` block.

    Args:
        node: GUI element body.
        key: ``position`` or ``size``.

    Returns:
        ``(x, y)`` or ``(width, height)``.
    """
    values = {k: v for k, _, v in get(node, key)}
    return int(values.get("x", values.get("width"))), int(values.get("y", values.get("height")))


def button_rect(body: list[Any], ox: int, oy: int) -> Rect:
    """Return the drawn rectangle of a button.

    Args:
        body: Button element.
        ox: Window x.
        oy: Window y.

    Returns:
        The button rectangle.
    """
    x, y = xy(body)
    sprite = [v for k, _, v in body if k == "quadTextureSprite"]
    scale = [float(v) for k, _, v in body if k == "scale"]
    if sprite and sprite[0] in BIG_ICON_SPRITES:
        assert scale, ("30px icon button needs scale", get(body, "name"))
        assert not any(k == "size" for k, _, _ in body), get(body, "name")
        side = round(30 * scale[0])
    elif [v for k, _, v in body if k == "spriteType"] == ["GFX_button_94x31"]:
        return (ox + x, oy + y, ox + x + 94, oy + y + 31)
    else:
        assert sprite == ["GFX_closebutton_16"], get(body, "name")
        assert not scale, get(body, "name")
        side = 16
    return (ox + x, oy + y, ox + x + side, oy + y + side)


def disjoint(a: Rect, b: Rect) -> bool:
    """Return whether two rectangles do not overlap.

    Args:
        a: First rectangle.
        b: Second rectangle.

    Returns:
        True when they share no pixel.
    """
    return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


def inside(a: Rect, b: Rect) -> bool:
    """Return whether rectangle ``a`` lies within rectangle ``b``.

    Args:
        a: Inner rectangle.
        b: Outer rectangle.

    Returns:
        True when ``a`` is fully inside ``b``.
    """
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def rectangles(gui: list[Any]) -> dict[str, Rect]:
    """Collect the rectangles of windows, frames, buttons and fields.

    Args:
        gui: Parsed source GUI files.

    Returns:
        Element name to rectangle.
    """
    rects: dict[str, Rect] = {}
    for kind, _, win in walk(gui):
        name = get(win, "name") if kind == "containerWindowType" else ""
        # Field frames (rn_ipc_/rn_ipl_/rn_ipp_) are nested windows; they are measured
        # relative to their editor below, not as top-level windows.
        frame = name.startswith(("rn_ipc_", "rn_ipl_", "rn_ipp_"))
        if not name.startswith("rn_ip") or frame or name == "rn_ip_subject_window":
            continue
        ox, oy = xy(win)
        w, h = xy(win, "size")
        rects[name] = (ox, oy, ox + w, oy + h)
        for k, _, body in win:
            if k == "buttonType":
                rects[get(body, "name")] = button_rect(body, ox, oy)
            elif k in {"editBoxType", "containerWindowType"}:
                x, y = xy(body)
                ew, eh = xy(body, "size")
                rects[get(body, "name")] = (ox + x, oy + y, ox + x + ew, oy + y + eh)
                if k == "editBoxType":
                    assert get(body, "font") == "hoi_18", get(body, "name")
                    assert ("ignore_enter", "=", "yes") in body, get(body, "name")
                    assert ew >= MAX_NAME * FONT_WIDEST[get(body, "font")], get(body, "name")
                else:
                    sprite = get(get(body, "background"), "spriteType")
                    assert sprite == "GFX_tiles_dark_area_cut_8"
    return rects


def geometry_audit(gui: list[Any]) -> None:
    """Check editor layouts, shortcuts, tabs and pencil positions.

    Args:
        gui: Parsed source GUI files.
    """
    rects = rectangles(gui)
    buttons = {get(b, "name"): b for k, _, b in walk(gui) if k == "buttonType"}
    for editor, fields, frames in (
        ("leader", ["rn_ip_leader_edit"], ["rn_ipl_frame"]),
        (
            "party_neutrality",
            ["rn_ip_party_neutrality_edit", "rn_ip_party_neutrality_long_edit"],
            ["rn_ipp_short_frame", "rn_ipp_long_frame"],
        ),
        (
            "country",
            ["rn_ip_country_name_edit", "rn_ip_country_adj_edit"],
            ["rn_ipc_name_frame", "rn_ipc_adj_frame"],
        ),
    ):
        win = rects[f"rn_ip_{editor}_window"]
        apply_ = rects[f"rn_ip_{editor}_apply"]
        cancel = rects[f"rn_ip_{editor}_cancel"]
        assert disjoint(apply_, cancel), ("Apply/Cancel overlap", editor)
        for field, frame in zip(fields, frames, strict=True):
            assert inside(rects[field], rects[frame]), (editor, field)
            assert disjoint(rects[field], apply_), (editor, field)
            assert disjoint(rects[field], cancel), (editor, field)
        for rect in [apply_, cancel, *(rects[f] for f in fields)]:
            assert inside(rect, win), (editor, rect)
        assert win[2] <= PANEL_WIDTH, editor
        assert win[3] <= ACTIONS_Y, editor
        assert get(buttons[f"rn_ip_{editor}_apply"], "shortcut") == "RETURN"
        assert not any(k == "shortcut" for k, _, _ in buttons[f"rn_ip_{editor}_cancel"])
    shortcuts = [b for b in buttons.values() if any(k == "shortcut" for k, _, _ in b)]
    assert len(shortcuts) == len(("leader", "party", "country")), "only the Apply buttons"
    assert not any(v == "ESCAPE" for _, _, v in walk(gui)), "Esc belongs to the politics panel"
    tabs = [rects[f"rn_ipp_tab_{i}"] for i, _ in GROUPS]
    party_parts = [
        rects[n]
        for n in (
            "rn_ipp_short_frame",
            "rn_ipp_long_frame",
            "rn_ip_party_neutrality_apply",
            "rn_ip_party_neutrality_cancel",
        )
    ]
    for i, tab in enumerate(tabs):
        assert inside(tab, rects["rn_ip_party_neutrality_window"])
        assert all(disjoint(tab, other) for other in tabs[i + 1 :] + party_parts)
    leader_pencil = rects["rn_ip_leader_open"]
    assert disjoint(leader_pencil, LEADER_NAME)
    assert leader_pencil[3] <= LEADER_NAME[1]
    assert inside(leader_pencil, rects["rn_ip_leader_launcher_window"])
    party_pencil = rects["rn_ip_party_neutrality_open"]
    assert inside(party_pencil, RULING_PARTY_INFO)
    assert party_pencil[2] < PIE_CHART_X
    assert inside(party_pencil, rects["rn_ip_party_neutrality_launcher_window"])


# ----------------------------------------------------------------------------- integration


def check_generated_mod() -> None:
    """Check that ``mod/`` holds exactly the generator output and the shared constant."""
    produced = GEN.gen_inline_editor()
    assert len(produced) == len({rel for rel, _, _ in produced})
    for rel, text, bom in produced:
        data = (MOD / rel).read_bytes()
        assert data == (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"), rel
    languages = set(GEN.LANGS)
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
    days = str(GEN.COOLDOWN_DAYS)
    inline_effects = declarations(MOD / "common" / "scripted_effects", "rn_inline_*.txt")
    assert ("set_temp_variable", "=", [("rn_ip_cd_days", "=", days)]) in inline_effects[
        "rn_ip_cooldown_days"
    ]
    assert ("set_temp_variable", "=", [("rn_cd_days", "=", days)]) in legacy(
        "common/scripted_effects"
    )["rn_cd_days"]
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
    assert get(get(country, "effects"), "rn_country_apply_click") == [
        (
            "if",
            "=",
            [
                ("limit", "=", [bridge, no_country_cd, *setter_limit]),
                ("rn_apply_country_name", "=", "yes"),
                ("rn_ip_cooldown_start_country", "=", "yes"),
            ],
        )
    ], "legacy country Apply: one branch for setter and cooldown start"
    enabled = get(get(country, "triggers"), "rn_country_apply_click_enabled")
    assert bridge in enabled
    assert no_country_cd in enabled
    assert get(get(country, "triggers"), "rn_leader_rename_click_enabled") == [
        ("NOT", "=", [("rn_ip_cooldown_active_leader", "=", "yes")])
    ]
    leader_row = ("var:rn_row_character", "=", [("is_country_leader", "=", "yes")])
    chars = get(models["rn_main_chars_gui"], "triggers")
    assert get(chars, "rn_char_rename_click_enabled") == [
        ("NOT", "=", [("AND", "=", [leader_row, ("rn_ip_cooldown_active_leader", "=", "yes")])])
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


# ----------------------------------------------------------------------------- execution


class ProductVM(ApplyVM):
    """ApplyVM with ROOT tracking, a fixed day counter and the editor's own triggers."""

    def __init__(  # noqa: PLR0913 - the four ApplyVM inputs plus tag and triggers
        self,
        effects: dict[str, Any],
        locs: dict[str, Any],
        chars: dict[str, str],
        kind: str,
        *,
        tag: str,
        triggers: dict[str, Any],
    ) -> None:
        """Create a VM for an own country other than the base VM's POL.

        Args:
            effects: Effect name to parsed body.
            locs: Scripted loc name to its ``text`` entries.
            chars: Localisation key to text.
            kind: ``party`` or ``country``.
            tag: Own country tag; the open editor is pinned to it.
            triggers: Source scripted triggers evaluated by name.
        """
        super().__init__(effects, locs, chars, kind)
        self.tag = tag
        self.root_tag = tag
        self.arrays["rn_ip_country_target"] = [Country(tag)]
        self.arrays["rn_ip_party_target"] = [Country(tag)]
        self.triggers = triggers
        self.persistent["global.num_days"] = Decimal(VM_TODAY)

    def condition(self, nodes: list[Any]) -> bool:
        """Evaluate a trigger list.

        Args:
            nodes: Trigger nodes.

        Returns:
            Whether every trigger holds.
        """
        for key, op, value in nodes:
            if key == "tag" and value == "ROOT":
                answer = self.tag == self.root_tag
            elif key in {"rn_ipp_party_target_matches", "rn_ipp_party_pinned_rules"}:
                answer = self.condition(self.triggers[key]) == (value == "yes")
            elif key in {"set_temp_variable", "subtract_from_temp_variable"}:
                # HOI4 allows temp-variable arithmetic in triggers (vanilla ai_strategy/ENG.txt).
                name, _, src = value[0]
                if key == "set_temp_variable":
                    self.temp[name] = self.value(src)
                else:
                    self.temp[name] = self.temp.get(name, Decimal(0)) - self.value(src)
                answer = True
            elif key.startswith("rn_ip_cooldown_active_"):
                kind = key.removeprefix("rn_ip_cooldown_active_")
                left = self.persistent.get(f"rn_ip_cd_{kind}_until", Decimal(0)) - self.value(
                    "global.num_days"
                )
                answer = (left > 0) == (value == "yes")
            else:
                answer = super().condition([(key, op, value)])
            if not answer:
                return False
        return True


class Context:
    """Everything one ApplyVM case needs: effects, localisation, characters and triggers."""

    def __init__(
        self,
        effects: dict[str, Any],
        locmap: dict[str, Any],
        chars: dict[str, str],
        triggers: dict[str, Any],
    ) -> None:
        """Store the shared inputs.

        Args:
            effects: Source plus legacy effects.
            locmap: Scripted localisation name to text branches.
            chars: Localisation key to text (character table and editor strings).
            triggers: Source scripted triggers.
        """
        self.effects = effects
        self.locmap = locmap
        self.chars = chars
        self.triggers = triggers

    def vm(self, kind: str, tag: str = "FRA", effects: dict[str, Any] | None = None) -> ProductVM:
        """Create a fresh VM for one case.

        Args:
            kind: ``party`` or ``country``.
            tag: Own country tag.
            effects: Replacement effects for negative cases.

        Returns:
            The VM, with an open editor, a fresh epoch and a valid payload.
        """
        return ProductVM(
            effects if effects is not None else self.effects,
            self.locmap,
            self.chars,
            kind,
            tag=tag,
            triggers=self.triggers,
        )


def run_party_groups(ctx: Context) -> int:
    """Run the four party groups under every government, plus the I4-M1 placeholder.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for tag in ("GER", "ENG", "FRA"):
        for group, government in GROUPS:
            vm = ctx.vm("party", tag)
            vm.government = government
            vm.persistent["rn_ip_party_group"] = Decimal(group)
            vm.run("rn_inline_pair_apply_party")
            assert len(vm.requests) == 1
            assert vm.pair_count == 1
            assert vm.guard_count == 2  # noqa: PLR2004 - both guard rounds
            request = get(vm.requests[0], "set_party_name")
            assert get(request, "ideology") == government
            assert len(get(request, "long_name")) == MAX_NAME
            assert vm.persistent["rn_ip_epoch"] == VM_EPOCH + 1
            ruling = ctx.vm("party", tag)
            ruling.government = government
            ruling.persistent["rn_ip_party_group"] = Decimal(group)
            assert ruling.localized("RN_IPP_PARTY_SHORT") == ctx.chars["RN_IPP_PARTY_SHORT_CURRENT"]
            assert ruling.localized("RN_IPP_PARTY_LONG") == ctx.chars["RN_IPP_PARTY_LONG_CURRENT"]
            assert ruling.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IP_LONG_NAME"]
            cases += 1 + run_non_ruling(ctx, tag, group, government)
            cases += run_placeholder(ctx, tag, group)
            bad = ctx.vm("party", tag)
            bad.persistent["rn_ip_party_group"] = Decimal(len(GROUPS) + 1)
            state = bad.state()
            bad.run("rn_inline_pair_apply_party")
            assert bad.state() == state
            assert not bad.requests
            assert bad.temp["rn_pair_err"] == ERR_TARGET
            assert bad.localized("RN_IPP_PARTY_SHORT") == ""
            assert bad.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IPP_TARGET_CHANGED"]
            bad.enforce = False
            bad.run("rn_inline_pair_cancel_party")
            assert "rn_ip_party_neutrality_open" not in bad.flags
            cases += 1
    return cases


def run_non_ruling(ctx: Context, tag: str, group: int, government: str) -> int:
    """Rename a pinned group while another ideology (or a custom one) rules.

    Args:
        ctx: Shared VM inputs.
        tag: Own country tag.
        group: Pinned group number.
        government: Ideology of the pinned group.

    Returns:
        Number of cases.
    """
    cases = 0
    for other in [g for _, g in GROUPS if g != government] + ["custom_ideology"]:
        vm = ctx.vm("party", tag)
        vm.government = other
        vm.persistent["rn_ip_party_group"] = Decimal(group)
        assert vm.condition(ctx.triggers["rn_ipp_party_target_matches"])
        short_key = "RN_IPP_PARTY_SHORT_" + GROUP_KEYS[group - 1]
        assert vm.localized("RN_IPP_PARTY_SHORT") == ctx.chars[short_key]
        assert vm.localized("RN_IPP_PARTY_LONG") == ctx.chars["RN_IPP_LONG_PLACEHOLDER"] == "?"
        assert vm.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IPP_LONG_UNKNOWN"]
        vm.run("rn_inline_pair_apply_party")
        assert len(vm.requests) == 1
        assert get(get(vm.requests[0], "set_party_name"), "ideology") == government
        cases += 1
    return cases


def run_placeholder(ctx: Context, tag: str, group: int) -> int:
    """Prove that an unchanged ``?`` placeholder never reaches the setter (I4-M1).

    Args:
        ctx: Shared VM inputs.
        tag: Own country tag.
        group: Pinned group number.

    Returns:
        Number of cases.
    """
    placeholder = ctx.chars["RN_IPP_LONG_PLACEHOLDER"]
    table = {ctx.chars[k] for k in ctx.chars if k.startswith("RN_CH_")}
    assert placeholder
    assert all(c not in NATIVE_ALPHABET and c not in table for c in placeholder)
    empty_b = {f"rn_nativeb_{i}": Decimal(0) for i in range(MAX_NAME)}
    mutations: list[tuple[str, Callable[[ProductVM], None], int]] = [
        (
            "native ok=0",
            lambda v: v.temp.update(rn_nativeb_ok=Decimal(0), rn_nativeb_len=Decimal(0), **empty_b),
            ERR_NATIVE,
        ),
        ("forged code 85", lambda v: v.temp.update(rn_nativeb_0=Decimal(85)), ERR_CODE),
    ]
    for label, mutate, want in mutations:
        vm = ctx.vm("party", tag)
        vm.government = "custom_ideology"
        vm.persistent["rn_ip_party_group"] = Decimal(group)
        mutate(vm)
        state = vm.state()
        vm.run("rn_inline_pair_apply_party")
        assert vm.state() == state, label
        assert not vm.requests, label
        assert vm.temp["rn_pair_err"] == want, label
        assert vm.temp["rn_pair_field"] == 2, label  # noqa: PLR2004 - field B
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.localized("RN_IPP_PARTY_STATUS") == ctx.chars["RN_IP_ERR_PARTY_LONG_UNKNOWN"]
    return len(mutations)


def run_tabs(ctx: Context) -> int:
    """Switch between every pair of tabs and check the no-op cases.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    cases = 0
    for start, _ in GROUPS:
        for tab, ideology in GROUPS:
            vm = ctx.vm("party")
            vm.enforce = False
            vm.persistent["rn_ip_party_group"] = Decimal(start)
            vm.arrays["rn_ip_party_target"] = [Country("FRA")]
            before = vm.state()
            vm.temp["rn_ip_party_tab"] = Decimal(tab)
            vm.run("rn_inline_pair_switch_party")
            if tab == start:
                assert vm.state() == before
            else:
                assert vm.persistent["rn_ip_party_group"] == tab
                assert vm.persistent["rn_ip_epoch"] == VM_EPOCH + 1
                assert not vm.requests
                assert not any(k.startswith("rn_ip_cd_") for k in vm.persistent)
                vm.enforce = True
                vm.pair_count = vm.guard_count = 0
                vm.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH + 1)
                vm.run("rn_inline_pair_apply_party")
                assert get(get(vm.requests[0], "set_party_name"), "ideology") == ideology
            cases += 1
    for blocker in ("closed", "cooldown", "bad tab"):
        vm = ctx.vm("party")
        vm.enforce = False
        vm.temp["rn_ip_party_tab"] = Decimal(len(GROUPS) + 1 if blocker == "bad tab" else 2)
        if blocker == "closed":
            vm.flags.clear()
        if blocker == "cooldown":
            vm.persistent["rn_ip_cd_party_until"] = Decimal(VM_TODAY + 3)
        before = vm.state()
        vm.run("rn_inline_pair_switch_party")
        assert vm.state() == before, blocker
        cases += 1
    return cases


def run_no_bridge(ctx: Context) -> int:
    """Apply without the bridge's command epoch: no write and the extension message.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    for kind in ("party", "country"):
        vm = ctx.vm(kind)
        vm.temp.pop("rn_ip_cmd_epoch")
        state = vm.state()
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.state() == state
        assert not vm.requests
        assert vm.temp["rn_pair_err"] == ERR_EPOCH
        vm.enforce = False
        vm.run("rn_ip_status_record_pair")
        assert vm.persistent["rn_ip_status_err"] == STATUS_NO_BRIDGE
        status = "RN_IP_STATUS" if kind == "country" else "RN_IPP_PARTY_STATUS"
        assert vm.localized(status) == ctx.chars["RN_IP_ERR_NO_BRIDGE"]
        stale = ctx.vm(kind)
        stale.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
        stale.run("rn_inline_pair_apply_" + kind)
        stale.enforce = False
        stale.run("rn_ip_status_record_pair")
        assert stale.persistent["rn_ip_status_err"] == ERR_EPOCH, "a real stale epoch stays stale"
    return 4


def run_caption_counter(ctx: Context, models: dict[str, Any]) -> int:
    """Run the real party Apply callback and check the caption revision counter.

    Args:
        ctx: Shared VM inputs.
        models: The six politics models.

    Returns:
        Number of cases.
    """
    block = get(
        get(models["rn_ip_party_neutrality_gui"], "effects"), "rn_ip_party_neutrality_apply_click"
    )
    block = [n for n in block if n[0] != "log"]
    cases = 0
    for start, success, want in ((0, True, 1), (5, False, 5), (REV_CAP, True, REV_CAP)):
        vm = ctx.vm("party")
        vm.persistent["rn_ip_pui_rev"] = Decimal(start)
        if not success:
            vm.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
            # The rejected callback records its UI status, a write the barrier would flag.
            vm.enforce = False
        vm.execute(block)
        assert vm.persistent["rn_ip_pui_rev"] == want, (start, success)
        cases += 1
    return cases


def run_cooldown(ctx: Context) -> int:
    """Run the cooldown cases: start, boundaries, independence and the late guard.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    expiry = Decimal(VM_TODAY + GEN.COOLDOWN_DAYS)
    cases = 0
    for kind in ("party", "country"):
        other = "country" if kind == "party" else "party"
        ok = ctx.vm(kind)
        ok.run("rn_inline_pair_apply_" + kind)
        assert ok.persistent[f"rn_ip_cd_{kind}_until"] == expiry
        assert f"rn_ip_cd_{other}_until" not in ok.persistent
        assert "rn_ip_cd_leader_until" not in ok.persistent
        rejected = ctx.vm(kind)
        rejected.temp["rn_ip_cmd_epoch"] = Decimal(VM_EPOCH - 1)
        before = rejected.state()
        rejected.run("rn_inline_pair_apply_" + kind)
        assert rejected.state() == before
        cases += 2
        for until, blocked in (
            (VM_TODAY + 1, True),
            (expiry, True),
            (VM_TODAY, False),
            (VM_TODAY - 1, False),
        ):
            vm = ctx.vm(kind)
            vm.persistent[f"rn_ip_cd_{kind}_until"] = Decimal(until)
            before = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            if blocked:
                assert vm.state() == before, (kind, until)
                assert vm.temp["rn_pair_err"] == ERR_COOLDOWN, (kind, until)
            else:
                assert vm.persistent[f"rn_ip_cd_{kind}_until"] == expiry, (kind, until)
            cases += 1
        vm = ctx.vm(kind)
        vm.persistent[f"rn_ip_cd_{other}_until"] = Decimal(VM_TODAY + 3)
        vm.persistent["rn_ip_cd_leader_until"] = Decimal(VM_TODAY + 3)
        vm.run("rn_inline_pair_apply_" + kind)
        assert vm.temp["rn_pair_err"] == 0, ("types independent", kind)
        cases += 1 + run_late_cooldown(ctx, kind)
    for k in ("country", "leader", "party"):
        vm = ctx.vm("party")
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY + 3)
        assert vm.localized(f"RN_IP_CD_LEFT_{k.upper()}") == ctx.chars["RN_IP_CD_DAYS_3"]
        assert vm.localized(f"RN_IP_CD_{k.upper()}") == ctx.chars[f"RN_IP_CD_{k.upper()}_ACTIVE"]
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY)
        assert vm.localized(f"RN_IP_CD_{k.upper()}") == ""
        vm.persistent[f"rn_ip_cd_{k}_until"] = Decimal(VM_TODAY + 45)
        assert vm.localized(f"RN_IP_CD_LEFT_{k.upper()}") == ctx.chars["RN_IP_CD_DAYS_MORE"]
        cases += 1
    return cases


def run_late_cooldown(ctx: Context, kind: str) -> int:
    """A cooldown that starts between the two guard rounds rejects without writes.

    Args:
        ctx: Shared VM inputs.
        kind: ``party`` or ``country``.

    Returns:
        Number of cases.
    """
    vm = ctx.vm(kind)
    observed: list[Any] = []

    def late(v: ProductVM) -> None:
        """Start the cooldown after the first guard round (a queued command)."""
        v.persistent[f"rn_ip_cd_{kind}_until"] = Decimal(VM_TODAY + 2)
        observed.append(v.state())

    vm.late_mutation = late
    vm.run("rn_inline_pair_apply_" + kind)
    assert vm.state() == observed[0]
    assert vm.temp["rn_pair_err"] == ERR_COOLDOWN
    return 1


def run_rejections(ctx: Context) -> int:
    """Reject every bad input before and after validation, with zero writes.

    Args:
        ctx: Shared VM inputs.

    Returns:
        Number of cases.
    """
    mutations: list[tuple[str, Callable[[ProductVM], None], int]] = [
        ("epoch", lambda v: v.temp.update(rn_ip_cmd_epoch=Decimal(VM_EPOCH - 1)), ERR_EPOCH),
        ("fractional epoch", lambda v: v.persistent.update(rn_ip_epoch=Decimal("7.25")), ERR_EPOCH),
        ("root mismatch", lambda v: setattr(v, "root_tag", "GER"), ERR_CLOSED),
        ("foreign pin", lambda v: v.arrays.update(rn_ip_party_target=[Country("GER")]), ERR_TARGET),
        (
            "duplicate pin",
            lambda v: v.arrays.update(rn_ip_party_target=[Country("FRA"), Country("FRA")]),
            ERR_TARGET,
        ),
        ("legacy", lambda v: v.flags.add("rn_input"), ERR_CLOSED),
        ("legacy-open", lambda v: v.flags.add("rn_open"), ERR_CLOSED),
        (
            "group out of range",
            lambda v: v.persistent.update(rn_ip_party_group=Decimal(0)),
            ERR_TARGET,
        ),
        ("invalid B", lambda v: v.temp.update(rn_nativeb_31=Decimal("1.5")), ERR_CODE),
    ]
    cases = 0
    for late in (False, True):
        for label, mutate, want in mutations:
            if late and label == "invalid B":
                continue
            vm = ctx.vm("party")
            observed: list[Any] = []
            if late:

                def callback(
                    v: ProductVM,
                    fn: Callable[[ProductVM], None] = mutate,
                    seen: list[Any] = observed,
                ) -> None:
                    """Apply the mutation between the two guard rounds."""
                    fn(v)
                    seen.append(v.state())

                vm.late_mutation = callback
            else:
                mutate(vm)
            before = vm.state()
            vm.run("rn_inline_pair_apply_party")
            assert vm.state() == (observed[0] if late else before), (late, label)
            assert not vm.requests, (late, label)
            assert vm.temp["rn_pair_err"] == want, (late, label)
            cases += 1
    for cap, want in ((0, ERR_CAPABILITY), (2, ERR_CAPABILITY), (1, 0)):
        vm = ctx.vm("country")
        vm.temp["rn_native_cap"] = Decimal(cap)
        before = vm.state()
        vm.run("rn_inline_pair_apply_country")
        assert vm.temp["rn_pair_err"] == want
        assert (vm.state() == before) if want else (len(vm.requests) == 1)
        cases += 1
    for group, government in [*GROUPS, (0, "custom_ideology")]:
        vm = ctx.vm("party")
        vm.flags.clear()
        vm.government = government
        vm.enforce = False
        before = vm.state()
        vm.run("rn_inline_pair_open_party")
        if group:
            assert vm.persistent["rn_ip_party_group"] == group
        else:
            assert vm.state() == before
        cases += 1
    return cases


def run_missing_late_guard(ctx: Context) -> None:
    """A party Apply without its second guard round must trip the VM's write barrier.

    Args:
        ctx: Shared VM inputs.

    Raises:
        AssertionError: The broken Apply was not caught.
    """
    broken = copy.deepcopy(ctx.effects)
    late = get(next(v for k, _, v in broken["rn_inline_pair_apply_party"] if k == "if"), "if")
    late.remove(("rn_inline_pair_guard_party", "=", "yes"))
    try:
        ctx.vm("party", effects=broken).run("rn_inline_pair_apply_party")
    except AssertionError as exc:
        assert "write before late guard" in str(exc)  # noqa: PT017 - plain script, no pytest
    else:
        msg = "negative fixture missing late guard survived"
        raise AssertionError(msg)


# ----------------------------------------------------------------------------- mutations


def _set(node: list[Any], key: str, value: Any) -> None:  # noqa: ANN401 - parse-tree value
    """Replace the value of one key in an element body, in place.

    Args:
        node: Element body.
        key: Key to replace.
        value: New value.
    """
    node[:] = [(k, op, value if k == key else v) for k, op, v in node]


def contract_mutations() -> dict[
    str, Callable[[dict[str, Any], dict[str, Any], list[Any], dict[str, Any], dict[str, Any]], None]
]:
    """Return named mutations of the parse trees that the structural checks must reject.

    Returns:
        Mutation name to a function taking (effects, models, gui, triggers, locs).
    """

    def long_from_short(
        _e: dict[str, Any],
        _m: dict[str, Any],
        _g: list[Any],
        _t: dict[str, Any],
        loc: dict[str, Any],
    ) -> None:
        """Make a non-ruling long carrier fall back to the short name again."""
        node = next(
            t
            for t in loc["RN_IPP_PARTY_LONG"]
            if t[0] == "text" and ("localization_key", "=", "RN_IPP_LONG_PLACEHOLDER") in t[2]
        )
        _set(node[2], "localization_key", "RN_IPP_PARTY_SHORT_DEMOCRATIC")

    return {
        "partial group gate": lambda _e, _m, _g, t, _l: get(
            t["rn_ipp_party_target_matches"], "OR"
        ).pop(),
        "ctor temp enabled": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_country_gui"], "triggers"), "rn_ip_country_apply_click_enabled"
        ).append(("check_variable", "=", [("temp_var:rn_native_cap", "=", "1")])),
        "country geometry": lambda _e, _m, g, _t, _l: _set(
            named(g)["rn_ip_country_window"], "size", [("width", "=", "420"), ("height", "=", "40")]
        ),
        "cancel under apply": lambda _e, _m, g, _t, _l: _set(
            named(g)["rn_ip_leader_cancel"], "position", [("x", "=", "380"), ("y", "=", "5")]
        ),
        "missing enter": lambda _e, _m, g, _t, _l: named(g)["rn_ip_party_neutrality_apply"].remove(
            ("shortcut", "=", "RETURN")
        ),
        "narrow field": lambda _e, _m, g, _t, _l: _set(
            named(g)["rn_ip_country_adj_edit"], "size", [("x", "=", "176"), ("y", "=", "20")]
        ),
        "status in guard": lambda _e, _m, _g, t, _l: t["rn_ipp_party_target_matches"].append(
            ("has_variable", "=", "rn_ip_status_err")
        ),
        "pencil ignores cooldown": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_party_neutrality_launcher_gui"], "triggers"),
            "rn_ip_party_neutrality_open_click_enabled",
        ).remove(("NOT", "=", [("rn_ip_cooldown_active_party", "=", "yes")])),
        "cooldown on reject": lambda e, _m, _g, _t, _l: e["rn_inline_pair_cancel_party"].append(
            ("rn_ip_cooldown_start_party", "=", "yes")
        ),
        "escape back": lambda _e, _m, g, _t, _l: named(g)["rn_ip_leader_cancel"].append(
            ("shortcut", "=", "ESCAPE")
        ),
        "government gate back": lambda _e, _m, _g, t, _l: t["rn_ipp_party_target_matches"].append(
            ("has_government", "=", "neutrality")
        ),
        "tab writes name": lambda e, _m, _g, _t, _l: get(
            e["rn_inline_pair_switch_party"], "if"
        ).append(("rn_inline_party_finish", "=", "yes")),
        "unscaled icon": lambda _e, _m, g, _t, _l: named(g)["rn_ip_party_neutrality_open"].remove(
            ("scale", "=", "0.67")
        ),
        "raw party carrier": lambda _e, _m, g, _t, _l: _set(
            named(g)["rn_ip_party_neutrality_prefill"], "text", "[ROOT.GetRulingParty]"
        ),
        "short as long prefill": long_from_short,
        "bridge gate removed": lambda _e, m, _g, _t, _l: get(
            m["rn_ip_leader_gui"], "visible"
        ).remove(("rn_editor_bridge_available", "=", "yes")),
        "counter without success": lambda _e, m, _g, _t, _l: get(
            get(m["rn_ip_leader_gui"], "effects"), "rn_ip_leader_apply_click"
        )[2][2][0][2].pop(0),
    }


def structural(
    effects: dict[str, Any],
    models: dict[str, Any],
    gui: list[Any],
    triggers: dict[str, Any],
    locs: dict[str, Any],
) -> None:
    """Run every structural check on one set of parse trees.

    Args:
        effects: Source effects plus the legacy mod effects.
        models: Source scripted GUI models.
        gui: Parsed source GUI files.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.
    """
    own = {
        k: v
        for k, v in effects.items()
        if not k.startswith(("rn_cd_", "rn_apply_", "rn_open_", "rn_close_"))
    }
    politics = check_models(models, triggers)
    check_callbacks(politics)
    check_exclusive_open(effects)
    check_tabs(effects, politics["rn_ip_party_neutrality_gui"])
    assert not any(
        k == "has_government"
        for k, _, _ in walk(get(politics["rn_ip_party_neutrality_gui"], "visible"))
    )
    check_guards(effects, triggers)
    check_status(own, politics, triggers, locs)
    check_cooldown(own, politics, triggers, locs)
    check_party_carriers(locs)
    check_widgets(gui)


def run_mutations(
    effects: dict[str, Any],
    models: dict[str, Any],
    gui: list[Any],
    triggers: dict[str, Any],
    locs: dict[str, Any],
) -> int:
    """Apply every contract mutation to copies and require a structural failure.

    Args:
        effects: Source effects plus the legacy mod effects.
        models: Source scripted GUI models.
        gui: Parsed source GUI files.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.

    Returns:
        Number of rejected mutations.

    Raises:
        AssertionError: A mutation was not rejected.
    """
    rejected = 0
    for name, mutate in contract_mutations().items():
        copies = copy.deepcopy((effects, models, gui, triggers, locs))
        mutate(*copies)
        try:
            structural(*copies)
        except AssertionError:
            rejected += 1
        else:
            msg = f"negative contract mutation survived: {name}"
            raise AssertionError(msg)
    return rejected


# ----------------------------------------------------------------------------- main


def load_source() -> tuple[
    dict[str, Any], set[str], dict[str, Any], list[Any], dict[str, Any], dict[str, Any]
]:
    """Parse the in-place editor source together with the legacy mod effects.

    Returns:
        (effects, own effect names, models, gui, triggers, scripted localisation).
    """
    for name, digest in PAYLOAD_HASHES.items():
        assert sha(SOURCE / "common" / "scripted_effects" / name) == digest, name
    buffers = "common/scripted_localisation/rn_inline_party_buffers.txt"
    assert sha(SOURCE / buffers) == sha(APPLY_QA / buffers)
    effects = declarations(SOURCE / "common" / "scripted_effects")
    legacy_effects = legacy("common/scripted_effects")
    assert not effects.keys() & legacy_effects.keys(), "effect collision with the legacy mod"
    own = set(effects)
    effects.update(legacy_effects)
    models = models_of(SOURCE / "common" / "scripted_guis")
    gui = [
        n
        for p in sorted((SOURCE / "interface").glob("*.gui"))
        for n in parse(p.read_text(encoding="utf-8-sig"))
    ]
    triggers = declarations(SOURCE / "common" / "scripted_triggers")
    locs = {
        get(body, "name"): body
        for p in sorted((SOURCE / "common" / "scripted_localisation").glob("*.txt"))
        for _, _, body in parse(p.read_text(encoding="utf-8-sig"))
    }
    assert (
        not models.keys()
        & models_of(MOD / "common" / "scripted_guis", "rename_anything_*.txt").keys()
    )
    assert not triggers.keys() & legacy("common/scripted_triggers").keys()
    for path in (SOURCE / "common").rglob("*.txt"):
        text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
        assert not re.search(r"\btag\s*=\s*POL\b", text), path
    return effects, own, models, gui, triggers, locs


def load_context(
    effects: dict[str, Any], triggers: dict[str, Any], locs: dict[str, Any]
) -> Context:
    """Build the VM inputs: scripted localisation, character table and editor strings.

    Args:
        effects: Source effects plus the legacy mod effects.
        triggers: Source scripted triggers.
        locs: Source scripted localisation.

    Returns:
        The shared VM context.
    """
    locmap = {name: [n for n in body if n[0] == "text"] for name, body in locs.items()}
    for path in (MOD / "common" / "scripted_localisation").glob("rename_anything_*.txt"):
        for _, _, body in parse(path.read_text(encoding="utf-8-sig")):
            locmap[get(body, "name")] = [n for n in body if n[0] == "text"]
    table = (MOD / "localisation" / "english" / "rename_anything_chars_l_english.yml").read_text(
        encoding="utf-8-sig"
    )
    chars = {
        k: json.loads(v) for k, v in re.findall(r'^ (RN_CH_\d+):\s*(".*")\s*$', table, re.MULTILINE)
    }
    for name in ("rn_inline_product_l_english.yml", "rn_in_place_ui_l_english.yml"):
        text = (SOURCE / "localisation" / "english" / name).read_text(encoding="utf-8-sig")
        chars.update(
            {k: json.loads(v) for k, v in re.findall(r'^ (\w+):\d* (".*")$', text, re.MULTILINE)}
        )
    return Context(effects, locmap, chars, triggers)


def main() -> int:
    """Run every check and print a JSON summary.

    Returns:
        0 when everything passed.
    """
    check_generated_mod()
    check_legacy_editor()
    check_native_names()
    effects, own, models, gui, triggers, locs = load_source()
    structural(effects, models, gui, triggers, locs)
    ctx = load_context(effects, triggers, locs)
    politics = {k: v for k, v in models.items() if k != "rn_ip_subject_gui"}
    counts = {
        "party_group_cases": run_party_groups(ctx),
        "tab_cases": run_tabs(ctx),
        "no_bridge_cases": run_no_bridge(ctx),
        "caption_counter_cases": run_caption_counter(ctx, politics),
        "cooldown_cases": run_cooldown(ctx),
        "rejection_cases": run_rejections(ctx),
    }
    run_missing_late_guard(ctx)
    rejected = run_mutations(effects, models, gui, triggers, locs)
    summary = {
        "blockers": [],
        "source": "tools/inline_editor",
        "own_effects": len(own),
        "models": len(models),
        **counts,
        "vm_cases": sum(counts.values()),
        "contract_mutations_rejected": rejected,
        "mod_matches_generator": True,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, ValueError) as exc:
        print("FAIL:", repr(exc), file=sys.stderr)
        sys.exit(1)
