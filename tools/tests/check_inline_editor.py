#!/usr/bin/env python3
"""Check the in-place editor source and its generated copy in ``mod/``.

The in-place editor (country name and adjective, leader, the four base party
groups) lives in ``tools/inline_editor/``. ``tools/gen.py`` copies it into
``mod/`` and adds the parts that depend on the rest of the mod. This script is
the test for that pair. It replaces ``probes/rn_inline_editor_product_qa/check.py``,
which belonged to the retired product fixture.

What it checks:

* Generator output. Every file that ``modgen.features.inline_editor.gen_inline_editor()``
  produces must be in
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
  every field of a two-field editor has a visible label 12 px above its frame,
  the status line sits under the last field, windows stay inside the politics
  panel, only the Apply buttons have a shortcut and none of them is ESCAPE.
* Wording. The design system's voice rules: no dashes, straight quotes in
  English, no internal words such as DLL or bridge, no "okres karencji".
* Limited execution. The ApplyVM from ``probes/rn_inline_pair_apply_source``
  runs the real party and country Apply paths: all four groups under every
  government, the I4-M1 placeholder, the tabs, the cooldown, the missing-bridge
  status, the reason of a rejected field (empty, too long, character), the
  stale-editor sentinel, the caption counters and a set of rejection mutations. Contract
  mutations of the parse trees must each be caught by the structural checks.

The checks live in the ``inline_checks`` package next to this file (one module
per group above); this file only runs them in order.

This is a static, offline test. It is not the HOI4 parser and it does not
prove anything about the game, the native bridge or multiplayer. Run it after
``tools/gen.py``::

    uv run python tools/tests/check_inline_editor.py

It prints a JSON summary and exits with 0, or prints ``FAIL: ...`` and exits
with 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parents[1]
"""The ``tools/`` folder, which holds the ``modgen`` and ``rncommon`` packages."""

if str(TOOLS) not in sys.path:
    # Appended, not inserted: the borrowed probe checker puts its own folder first.
    sys.path.append(str(TOOLS))

# The imports have to follow the sys.path change above.
from inline_checks.constants import MOD  # noqa: E402
from inline_checks.generated import (  # noqa: E402
    check_generated_mod,
    check_legacy_editor,
    check_native_names,
    check_voice,
)
from inline_checks.loading import load_context, load_source  # noqa: E402
from inline_checks.mutations import run_mutations  # noqa: E402
from inline_checks.structure import structural  # noqa: E402
from inline_checks.tree import models_of  # noqa: E402
from inline_checks.vm_cases import (  # noqa: E402
    run_caption_counter,
    run_cooldown,
    run_error_reasons,
    run_keyboard_refresh,
    run_missing_late_guard,
    run_no_bridge,
    run_party_groups,
    run_party_loc_equivalence,
    run_refresh_gate,
    run_refused_sentinels,
    run_rejections,
    run_stale_sentinel,
    run_tabs,
)


def main() -> int:
    """Run every check and print a JSON summary.

    Returns:
        0 when everything passed.
    """
    check_generated_mod()
    check_legacy_editor()
    check_native_names()
    check_voice()
    effects, own, models, gui, triggers, locs = load_source()
    structural(effects, models, gui, triggers, locs)
    ctx = load_context(effects, triggers, locs)
    politics = {k: v for k, v in models.items() if k != "rn_ip_subject_gui"}
    counts = {
        "party_group_cases": run_party_groups(ctx),
        "tab_cases": run_tabs(ctx),
        "no_bridge_cases": run_no_bridge(ctx),
        "error_reason_cases": run_error_reasons(ctx),
        "stale_sentinel_cases": run_stale_sentinel(ctx),
        "refused_sentinel_cases": run_refused_sentinels(ctx),
        "party_loc_equivalence_cases": run_party_loc_equivalence(ctx),
        "refresh_gate_cases": run_refresh_gate(ctx),
        "keyboard_refresh_cases": run_keyboard_refresh(
            ctx,
            models_of(MOD / "common" / "scripted_guis", "rename_anything_*.txt")["rn_input_gui"],
        ),
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
