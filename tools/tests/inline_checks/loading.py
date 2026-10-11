"""Load the in-place editor source, the legacy effects and the VM context."""

from __future__ import annotations

import json
import re
from typing import Any

from inline_checks.constants import APPLY_QA, MOD, PAYLOAD_HASHES, SOURCE
from inline_checks.fixtures import parse
from inline_checks.tree import declarations, get, legacy, models_of, sha
from inline_checks.vm_cases import Context


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
