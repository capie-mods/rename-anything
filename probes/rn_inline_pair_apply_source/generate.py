"""Generate the inactive pair Apply effects and party name buffers for the in-place UI.

This generator writes only two NEW source files under
``probes/rn_in_place_ui/common`` plus this probe's ``contract.json``. It does
not edit any mod descriptor, GUI, existing helper, native source, config or
build output, and nothing it writes is wired to a GUI button or to the native
transport, so the files stay inactive until a reviewer connects them.

Before writing anything it checks that the shared pair payload validator
``scripted_effects/rn_inline_pair_payload.txt`` still has its reviewed SHA-256
(``e278df...``). If that helper changed, generation stops so the new code is not
built on top of an unreviewed dependency.

``scripted_effects/rn_inline_pair_apply.txt`` holds eight effects, four per
kind (``country`` and ``party``):

* ``rn_inline_pair_guard_<kind>`` is a pure guard that only sets temp
  variables. It requires the local POL player, the panel's own open flag and
  no other rename panel, a positive integer epoch that matches the command
  epoch, exactly one typed pin of the current country, and for parties the
  pinned neutrality group 4. For a country it also requires the fresh native
  capability ``rn_native_cap = 1``. The error code goes to ``rn_pair_err``
  (7 context, 8 epoch, 9 pin or party group, 10 capability, 0 success).
* ``rn_inline_pair_open_<kind>`` and ``rn_inline_pair_cancel_<kind>`` are
  lifecycle helpers that nothing calls yet. Open pins THIS, bumps the epoch and
  sets the open flag; Cancel clears the flag and pin and bumps the epoch. They
  never touch a name or a buffer.
* ``rn_inline_pair_apply_<kind>`` runs the guard, the shared
  ``rn_inline_pair_validate`` on both payloads, and then the full guard again.
  Only after all three pass does it copy payload A and B into the kind's two
  buffers (country name and adjective, or party short and long name), call the
  setter (``rn_apply_country_name`` for a country, ``set_party_name`` through
  ``meta_effect`` for a party) and clean up. On any failure it only logs the
  error, field and bad slot.

``scripted_localisation/rn_inline_party_buffers.txt`` defines ``RN_PS_0..31``
and ``RN_PL_0..31``, which render the party short and long name buffers through
the main mod's ``RN_CH_0..84`` character keys and print nothing for slots
past the stored length.

``contract.json`` records the output paths and hashes, the dependency hash,
entry point names, native record key lengths (all at most 15 ASCII bytes) and
the policy notes that the root review relies on.

All text is written as UTF-8 with LF line endings. The generator prints one
summary line. It proves nothing about the game: ``check.py`` in this folder
runs the generated source in a limited offline model, and real behaviour still
needs a fresh HOI4 runtime test.

Usage::

    python probes/rn_inline_pair_apply_source/generate.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
"""This probe folder (``probes/rn_inline_pair_apply_source``)."""

REPO = HERE.parents[1]
"""Repository root."""

COMMON = REPO / "probes/rn_in_place_ui/common"
"""``common`` folder of the in-place UI fixture that receives the new files."""

APPLY = COMMON / "scripted_effects/rn_inline_pair_apply.txt"
"""Output path of the generated guard, lifecycle and Apply effects."""

LOC = COMMON / "scripted_localisation/rn_inline_party_buffers.txt"
"""Output path of the generated party buffer scripted localisation."""

PAIR_PAYLOAD_SHA256 = "e278dfac3a4e3ac5ccca7d7cf74da9d87f0de728d30bca875d543f24956f6fc7"
"""Reviewed SHA-256 of the shared ``rn_inline_pair_payload.txt`` validator."""

SLOTS = 32
"""Character slots per name buffer."""

CHAR_CODES = 84
"""Highest character code defined by the main mod (``RN_CH_1`` to ``RN_CH_84``)."""

MAX_KEY_BYTES = 15
"""Longest allowed ASCII length of a native record variable name."""

QA_TAG = "POL"
"""The only country tag the inactive candidates accept (QA own country)."""

NEUTRALITY_GROUP = 4
"""Logical party group number of the base neutrality ideology."""

ERR_OK = 0
"""``rn_pair_err`` after every guard passed."""

ERR_CONTEXT = 7
"""``rn_pair_err``: wrong country, AI player, panel flags not as required."""

ERR_EPOCH = 8
"""``rn_pair_err``: epoch not a positive integer or not the command epoch."""

ERR_PIN = 9
"""``rn_pair_err``: typed pin or party group/government does not match."""

ERR_CAPABILITY = 10
"""``rn_pair_err``: fresh native country capability missing."""

NO_BAD_SLOT = -1
"""``rn_pair_bad`` when no slot is at fault."""

PANEL_FLAGS = [
    "rn_open",
    "rn_input",
    "rn_ip_leader_open",
    "rn_ip_country_open",
    "rn_ip_party_neutrality_open",
]
"""Every rename panel flag, in the order the context trigger lists them."""

PAYLOAD_PREFIXES = ("rn_native_", "rn_nativeb_")
"""Temp variable prefixes of payload A and payload B."""


class Kind(NamedTuple):
    """Script names of one Apply kind."""

    open_flag: str
    """Country flag of the kind's own open panel."""

    target: str
    """Typed pin array of the kind."""

    buffers: tuple[tuple[str, str], tuple[str, str]]
    """Destination (array, length variable) of payload A and payload B."""


KINDS = {
    "country": Kind(
        "rn_ip_country_open",
        "rn_ip_country_target",
        (("rn_cname", "rn_cname_len"), ("rn_cadj", "rn_cadj_len")),
    ),
    "party": Kind(
        "rn_ip_party_neutrality_open",
        "rn_ip_party_target",
        (("rn_pshort", "rn_pshort_len"), ("rn_plong", "rn_plong_len")),
    ),
}
"""``country`` and ``party`` kinds; payload A/B go to name/adjective or short/long name."""

PARTY_BUFFERS = [("PS", "rn_pshort", "rn_pshort_len"), ("PL", "rn_plong", "rn_plong_len")]
"""Party buffers as (scripted loc prefix, array, length variable)."""


def temp(name: str, value: str) -> str:
    """Return a ``set_temp_variable`` statement.

    Args:
        name: Temp variable name.
        value: Value or variable reference.

    Returns:
        The one-line statement.
    """
    return f"set_temp_variable = {{ {name} = {value} }}"


def effect(name: str, lines: list[str]) -> str:
    """Wrap statement lines into a named scripted effect block.

    Args:
        name: Effect name.
        lines: Body lines; each is indented by one tab.

    Returns:
        The effect block followed by a blank line.
    """
    return name + " = {\n" + "\n".join("\t" + line for line in lines) + "\n}\n\n"


def context(kind: str, *, opening: bool = False) -> list[str]:
    """Return the trigger lines that describe the allowed UI context.

    Args:
        kind: ``country`` or ``party``.
        opening: True for Open, where the kind's own flag must be absent and a
            party must currently have the neutrality government.

    Returns:
        Trigger lines: POL, human player, and the required flag state.
    """
    own = KINDS[kind].open_flag
    lines = [f"tag = {QA_TAG}", "is_ai = no"]
    lines.extend(
        f"has_country_flag = {flag}"
        if flag == own and not opening
        else f"NOT = {{ has_country_flag = {flag} }}"
        for flag in PANEL_FLAGS
    )
    if opening and kind == "party":
        lines.append("has_government = neutrality")
    return lines


def guard(kind: str) -> str:
    """Generate the pure context, epoch, pin and capability guard.

    Args:
        kind: ``country`` or ``party``.

    Returns:
        The ``rn_inline_pair_guard_<kind>`` effect.
    """
    target = KINDS[kind].target
    lines = [
        temp("rn_pair_err", str(ERR_CONTEXT)),
        temp("rn_pair_field", "0"),
        temp("rn_pair_bad", str(NO_BAD_SLOT)),
        "if = {",
        "\tlimit = {",
    ]
    lines += ["\t\t" + line for line in context(kind)]
    lines += [
        "\t}",
        "\t" + temp("rn_pair_err", str(ERR_EPOCH)),
        "\t" + temp("rn_pair_epoch_round", "rn_ip_epoch"),
        "\tround_temp_variable = rn_pair_epoch_round",
        "\tif = {",
        "\t\tlimit = {",
        "\t\t\tcheck_variable = { rn_ip_epoch > 0 }",
        "\t\t\tcheck_variable = { temp_var:rn_pair_epoch_round = rn_ip_epoch }",
        "\t\t\tcheck_variable = { temp_var:rn_ip_cmd_epoch = rn_ip_epoch }",
        "\t\t}",
        "\t\t" + temp("rn_pair_err", str(ERR_PIN)),
        "\t\tif = {",
        "\t\t\tlimit = {",
        f"\t\t\t\tcheck_variable = {{ {target}^num = 1 }}",
        f"\t\t\t\tis_in_array = {{ array = {target} value = THIS }}",
    ]
    if kind == "party":
        lines += [
            f"\t\t\t\tcheck_variable = {{ rn_ip_party_group = {NEUTRALITY_GROUP} }}",
            "\t\t\t\thas_government = neutrality",
        ]
    lines += ["\t\t\t}"]
    if kind == "country":
        lines += [
            "\t\t\t" + temp("rn_pair_err", str(ERR_CAPABILITY)),
            "\t\t\tif = {",
            "\t\t\t\tlimit = { check_variable = { temp_var:rn_native_cap = 1 } }",
            "\t\t\t\t" + temp("rn_pair_err", str(ERR_OK)),
            "\t\t\t}",
        ]
    else:
        lines += ["\t\t\t" + temp("rn_pair_err", str(ERR_OK))]
    lines += ["\t\t}", "\t}", "}"]
    return effect("rn_inline_pair_guard_" + kind, lines)


def cleanup(kind: str) -> list[str]:
    """Return the statements that close a panel after Apply or Cancel.

    Args:
        kind: ``country`` or ``party``.

    Returns:
        Lines clearing the open flag and pin (and the party group) and bumping the epoch.
    """
    flag, target = KINDS[kind].open_flag, KINDS[kind].target
    lines = [f"clr_country_flag = {flag}", f"clear_array = {target}"]
    if kind == "party":
        lines += ["clear_variable = rn_ip_party_group"]
    return [*lines, "add_to_variable = { rn_ip_epoch = 1 }"]


def lifecycle(kind: str) -> str:
    """Generate the uncalled Open and Cancel lifecycle effects.

    Args:
        kind: ``country`` or ``party``.

    Returns:
        The ``rn_inline_pair_open_<kind>`` and ``rn_inline_pair_cancel_<kind>`` effects.
    """
    flag, target = KINDS[kind].open_flag, KINDS[kind].target
    lines = ["if = {", "\tlimit = {", *["\t\t" + line for line in context(kind, opening=True)]]
    lines += ["\t}", f"\tclear_array = {target}", f"\tadd_to_array = {{ {target} = THIS }}"]
    if kind == "party":
        lines += [f"\tset_variable = {{ rn_ip_party_group = {NEUTRALITY_GROUP} }}"]
    lines += ["\tadd_to_variable = { rn_ip_epoch = 1 }", f"\tset_country_flag = {flag}", "}"]
    result = effect("rn_inline_pair_open_" + kind, lines)
    lines = ["if = {", f"\tlimit = {{ tag = {QA_TAG} is_ai = no has_country_flag = {flag} }}"]
    lines += ["\t" + line for line in cleanup(kind)] + ["}"]
    return result + effect("rn_inline_pair_cancel_" + kind, lines)


def copy_buffer(array: str, length: str, prefix: str) -> list[str]:
    """Return the statements that copy one validated payload into a buffer.

    Args:
        array: Destination code array.
        length: Destination length variable.
        prefix: Temp variable prefix of the payload (``rn_native_`` or ``rn_nativeb_``).

    Returns:
        Clear, 32 guarded appends and the length assignment.
    """
    lines = [f"clear_array = {array}"]
    lines.extend(
        f"if = {{ limit = {{ check_variable = {{ temp_var:{prefix}len > {i} }} }}"
        f" add_to_array = {{ {array} = temp_var:{prefix}{i} }} }}"
        for i in range(SLOTS)
    )
    return [*lines, f"set_variable = {{ {length} = temp_var:{prefix}len }}"]


def slots(prefix: str) -> str:
    """Return the localisation text that renders all slots of one party buffer.

    Args:
        prefix: ``PS`` (short name) or ``PL`` (long name).

    Returns:
        ``[ROOT.RN_<prefix>_0]`` through ``[ROOT.RN_<prefix>_31]`` concatenated.
    """
    return "".join(f"[ROOT.RN_{prefix}_{i}]" for i in range(SLOTS))


def apply(kind: str) -> str:
    """Generate the Apply effect: guard, validate both payloads, guard again, then write.

    Args:
        kind: ``country`` or ``party``.

    Returns:
        The ``rn_inline_pair_apply_<kind>`` effect.
    """
    lines = [
        "rn_inline_pair_guard_" + kind + " = yes",
        "if = {",
        "\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
        "\trn_inline_pair_validate = yes",
        "\tif = {",
        "\t\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
        "\t\t# Recheck the COMPLETE context/epoch/pin/capability after both payloads.",
        "\t\trn_inline_pair_guard_" + kind + " = yes",
        "\t\tif = {",
        "\t\t\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
        "\t\t\t# First persistent write below: every guard and both inputs passed.",
    ]
    for (array, length), prefix in zip(KINDS[kind].buffers, PAYLOAD_PREFIXES, strict=True):
        lines += ["\t\t\t" + line for line in copy_buffer(array, length, prefix)]
    if kind == "country":
        lines += [
            "\t\t\t# Existing RN_N/RN_J encode both fields in ONE RN1 cosmetic tag.",
            "\t\t\trn_apply_country_name = yes",
        ]
    else:
        lines += [
            "\t\t\t# One setter carries both literal strings; no group/subtype inference.",
            "\t\t\tmeta_effect = {",
            (
                "\t\t\t\ttext = { set_party_name = "
                '{ ideology = neutrality name = "[S]" long_name = "[L]" } }'
            ),
            '\t\t\t\tS = "' + slots(PARTY_BUFFERS[0][0]) + '"',
            '\t\t\t\tL = "' + slots(PARTY_BUFFERS[1][0]) + '"',
            "\t\t\t}",
        ]
    lines += ["\t\t\t" + line for line in cleanup(kind)]
    lines += [
        "\t\t}",
        "\t}",
        "}",
        "if = {",
        "\tlimit = { NOT = { check_variable = { temp_var:rn_pair_err = 0 } } }",
        '\tlog = "RN pair '
        + kind
        + " Apply rejected err=[?temp_var:rn_pair_err] field=[?temp_var:rn_pair_field]"
        ' bad=[?temp_var:rn_pair_bad]"',
        "}",
    ]
    return effect("rn_inline_pair_apply_" + kind, lines)


def party_loc() -> str:
    """Generate the party short and long name buffer scripted localisation.

    Returns:
        Contents of ``rn_inline_party_buffers.txt``.
    """
    lines = [
        "# NEW INACTIVE party buffers. Depends on main mod RN_CH_0..84.",
        "# 32 slots per independent buffer, explicit ROOT COUNTRY in meta_effect.",
        "# RN_PS/RN_PL are slot prefixes; RN_PS_0..31 and RN_PL_0..31 are defined.",
        "",
    ]
    for prefix, array, length in PARTY_BUFFERS:
        for i in range(SLOTS):
            lines += [
                "defined_text = {",
                f"\tname = RN_{prefix}_{i}",
                (
                    f"\ttext = {{ trigger = {{ NOT = {{ check_variable = {{ {length} > {i} }} }} }}"
                    " localization_key = RN_CH_0 }"
                ),
            ]
            lines += [
                f"\ttext = {{ trigger = {{ check_variable = {{ {array}^{i} = {code} }} }}"
                f" localization_key = RN_CH_{code} }}"
                for code in range(1, CHAR_CODES + 1)
            ]
            lines += ["\ttext = { localization_key = RN_CH_0 }", "}"]
    return "\n".join(lines) + "\n"


SOURCE_HEADER = """# NEW INACTIVE source-only candidates; NOT connected to any GUI or transport.
# COUNTRY CURRENT==ROOT must be the local player's player_context, QA own POL.
# tag/is_ai do not independently prove local-player authority; MP is deferred.
# Dependencies: unchanged pure pair_validate E278DF, strict single CD171D,
# main rn_apply_country_name/RN_N/RN_J/RN_CH, and new RN_PS/RN_PL slot localisation.
# Apply error outputs: rn_pair_err/field/bad;7 context,8 epoch,9 typed own pin
# or current neutrality/group4,10 missing/failing country capability; field0.
# Payload1/4/5/6 retains field1/2 and bad index from pair_validate.
# Rejection writes TEMPS/log only; five buffers, draft/open/epoch/pins untouched.
# Both complete payloads and the repeated full guard precede ALL Apply writes.
# Atomic here means validation-before-writes, NOT rollback after engine/crash failure.
# Country needs fresh native command rn_native_cap=1 from active versioned export;
# persistent flags/module presence/saved status do not establish this capability.
# No native capability producer or GUI Apply enabling is implemented in this file.
# Future Open/Cancel helpers below are uncalled lifecycle candidates. Open makes
# typed COUNTRY singleton pins using THIS, plus explicit party base-group4.
# Never call Open inside Apply; it changes epoch/pin and would discard a draft.
# Cancel intentionally works with own open flag even if another panel is open.
# These lifecycle entries change flags/pins/epoch only, never any name/buffer.

"""
"""Comment block written at the top of the generated Apply effects file."""


def main() -> None:
    """Check the pair helper hash, write both source files and the contract manifest."""
    pair_sha = hashlib.sha256(
        (COMMON / "scripted_effects/rn_inline_pair_payload.txt").read_bytes()
    ).hexdigest()
    assert pair_sha == PAIR_PAYLOAD_SHA256, "pair helper changed; review first"
    source = SOURCE_HEADER
    for kind in ("country", "party"):
        source += guard(kind) + lifecycle(kind) + apply(kind)
    APPLY.parent.mkdir(parents=True, exist_ok=True)
    APPLY.write_text(source.rstrip() + "\n", encoding="utf-8", newline="\n")
    LOC.parent.mkdir(parents=True, exist_ok=True)
    LOC.write_text(party_loc(), encoding="utf-8", newline="\n")
    suffixes = ["ok", "len", *map(str, range(SLOTS))]
    record_keys = [
        *[prefix + s for prefix in PAYLOAD_PREFIXES for s in suffixes],
        "rn_ip_cmd_epoch",
    ]
    lengths = {key: len(key.encode("ascii")) for key in [*record_keys, "rn_native_cap"]}
    assert len(record_keys) == 2 * len(suffixes) + 1
    assert len(lengths) == len(record_keys) + 1
    assert max(lengths.values()) <= MAX_KEY_BYTES
    manifest = {
        "status": "offline source-only, inactive, root review required before any runtime",
        "new_sources": [str(p.relative_to(REPO)).replace("\\", "/") for p in (APPLY, LOC)],
        "outputs": {
            str(p.relative_to(REPO)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (APPLY, LOC)
        },
        "strict_pair_dependency_sha256": pair_sha,
        "apply_entries": ["rn_inline_pair_apply_country", "rn_inline_pair_apply_party"],
        "future_lifecycle_not_called": [
            "rn_inline_pair_open_country",
            "rn_inline_pair_cancel_country",
            "rn_inline_pair_open_party",
            "rn_inline_pair_cancel_party",
        ],
        "party_group": (
            "base neutrality only, pinned logical4; no custom subtype/all-ideology claim"
        ),
        # The party record has both payloads and the epoch; the country one adds the capability.
        "native_record_counts": {"party": len(record_keys), "country": len(lengths)},
        "ascii_key_lengths": lengths,
        "capability": (
            "fresh rn_native_cap=1 only from active versioned country DLL export; "
            "no saved flag/module shortcut"
        ),
        "first_write_policy": (
            "pure validation of both A/B then full repeated "
            "context/epoch/typed pin/current party/cap guard"
        ),
        "protected_legacy_buffer": ["rn_buf", "rn_len"],
        "activation": False,
        "runtime": "not tested",
    }
    (HERE / "contract.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "Generated2 NEW inactive sources;8 effects,64 party localisation slots; "
        "no existing helper/GUI/native/config edits."
    )


if __name__ == "__main__":
    main()
