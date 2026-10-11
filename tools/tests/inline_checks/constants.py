"""Paths, limits and error codes of the in-place editor test."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
"""Repository root (three levels above ``tools/tests/inline_checks/``)."""

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

REASONS = ["EMPTY", "LONG", "CHAR"]
"""Status-line reasons in ``rn_ip_status_why`` order (1 empty, 2 too long, 3 character)."""

FIELD_LABELS = {
    "rn_ipc_name_label": "RN_IPC_LABEL_NAME",
    "rn_ipc_adj_label": "RN_IPC_LABEL_ADJ",
    "rn_ip_party_neutrality_short_label": "RN_IPP_LABEL_SHORT",
    "rn_ip_party_neutrality_long_label": "RN_IPP_LABEL_LONG",
}
"""Visible field labels of the two-field editors (design system) and their keys."""

LABEL_PITCH = 12
"""Height a field label adds above its frame (design-system editor grid)."""

STATUS_HEIGHT = 14
"""Height of the one-line status under the last field."""

STALE_SENTINEL = -1
"""Command epoch a bridge can send for an editor widget it did not open (proposal)."""

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

Rect = tuple[int, int, int, int]
"""Rectangle as (left, top, right, bottom) in politics panel coordinates."""
