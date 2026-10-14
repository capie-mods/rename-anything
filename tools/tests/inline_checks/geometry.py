"""Rectangle checks of the in-place editor layout (politics panel coordinates)."""

from __future__ import annotations

from typing import Any

from inline_checks.constants import (
    ACTIONS_Y,
    BIG_ICON_SPRITES,
    FONT_WIDEST,
    GROUPS,
    LABEL_PITCH,
    LEADER_NAME,
    MAX_NAME,
    PANEL_WIDTH,
    PIE_CHART_X,
    RULING_PARTY_INFO,
    STATUS_HEIGHT,
    Rect,
)
from inline_checks.tree import get, walk, xy


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
    elif [v for k, _, v in body if k == "spriteType"] in (
        ["GFX_button_94x31"],
        ["GFX_button_123x34"],
    ):
        w, h = (94, 31) if get(body, "spriteType") == "GFX_button_94x31" else (123, 34)
        return (ox + x, oy + y, ox + x + w, oy + y + h)
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


def text_rects(gui: list[Any]) -> dict[str, Rect]:
    """Collect the rectangles of the text boxes placed directly in the editor windows.

    Args:
        gui: Parsed source GUI files.

    Returns:
        Text box name to rectangle (panel coordinates).
    """
    rects: dict[str, Rect] = {}
    for kind, _, win in walk(gui):
        if kind != "containerWindowType" or not get(win, "name").endswith("_window"):
            continue
        ox, oy = xy(win)
        for k, _, body in win:
            if k == "instantTextboxType" and any(key == "maxWidth" for key, _, _ in body):
                x, y = xy(body)
                w, h = int(get(body, "maxWidth")), int(get(body, "maxHeight"))
                rects[get(body, "name")] = (ox + x, oy + y, ox + x + w, oy + y + h)
    return rects


def label_audit(gui: list[Any], rects: dict[str, Rect]) -> None:
    """Check the field labels and status lines against the design-system grid.

    Every field of a two-field editor has a visible label 12 px above its frame,
    labelled rows repeat every 42 px, and one 14 px status line sits under the
    last field, inside the editor.

    Args:
        gui: Parsed source GUI files.
        rects: Rectangles from :func:`rectangles`.
    """
    texts = text_rects(gui)
    row_pitch = 30
    for editor, pairs in (
        (
            "country",
            [("rn_ipc_name_label", "rn_ipc_name_frame"), ("rn_ipc_adj_label", "rn_ipc_adj_frame")],
        ),
        (
            "party_neutrality",
            [
                ("rn_ip_party_neutrality_short_label", "rn_ipp_short_frame"),
                ("rn_ip_party_neutrality_long_label", "rn_ipp_long_frame"),
            ],
        ),
    ):
        win = rects[f"rn_ip_{editor}_window"]
        for label, frame in pairs:
            assert texts[label][1] + LABEL_PITCH == rects[frame][1], (editor, label)
            assert inside(texts[label], win), (editor, label)
            assert rects[frame][0] <= texts[label][0], (editor, label)
        first, second = (rects[frame] for _, frame in pairs)
        assert second[1] - first[1] == row_pitch + LABEL_PITCH, editor
    for editor, last in (
        ("leader", "rn_ipl_frame"),
        ("country", "rn_ipc_adj_frame"),
        ("party_neutrality", "rn_ipp_long_frame"),
    ):
        status = texts[f"rn_ip_{editor}_status"]
        assert status[3] - status[1] == STATUS_HEIGHT, editor
        assert status[1] >= rects[last][3], editor
        assert inside(status, rects[f"rn_ip_{editor}_window"]), editor
    tabs = [rects[f"rn_ipp_tab_{i}"] for i, _ in GROUPS]
    short_label = texts["rn_ip_party_neutrality_short_label"]
    assert all(disjoint(tab, short_label) for tab in tabs)
    # Restore name: inside the country editor, under its status line, clear of every control.
    reset = rects["rn_ip_country_reset"]
    assert inside(reset, rects["rn_ip_country_window"])
    assert reset[1] >= texts["rn_ip_country_status"][3]
    for other in (
        "rn_ipc_name_frame",
        "rn_ipc_adj_frame",
        "rn_ip_country_apply",
        "rn_ip_country_cancel",
    ):
        assert disjoint(reset, rects[other]), other


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
    shortcuts = {get(b, "name") for b in buttons.values() if any(k == "shortcut" for k, _, _ in b)}
    applies = {f"rn_ip_{e}_apply" for e in ("leader", "party_neutrality", "country")}
    subjects = {
        f"capie_v1_ed__rn__{e}_apply" for e in ("subcountry", "subleader", "subparty", "faction")
    }
    assert shortcuts == applies | subjects, "only the Apply buttons"
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
    label_audit(gui, rects)
    leader_pencil = rects["rn_ip_leader_open"]
    assert disjoint(leader_pencil, LEADER_NAME)
    assert leader_pencil[3] <= LEADER_NAME[1]
    assert inside(leader_pencil, rects["rn_ip_leader_launcher_window"])
    party_pencil = rects["rn_ip_party_neutrality_open"]
    assert inside(party_pencil, RULING_PARTY_INFO)
    assert party_pencil[2] < PIE_CHART_X
    assert inside(party_pencil, rects["rn_ip_party_neutrality_launcher_window"])
