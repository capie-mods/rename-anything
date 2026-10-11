"""Generate only the NEW inactive pair Apply and party-buffer source files.

No mod descriptor, GUI, existing helper, native source, config or build is edited.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
COMMON = REPO / "probes/rn_in_place_ui/common"
APPLY = COMMON / "scripted_effects/rn_inline_pair_apply.txt"
LOC = COMMON / "scripted_localisation/rn_inline_party_buffers.txt"


def temp(name, value):
    return f"set_temp_variable = {{ {name} = {value} }}"


def effect(name, lines):
    return name + " = {\n" + "\n".join("\t" + line for line in lines) + "\n}\n\n"


def context(kind, opening=False):
    own = "rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"
    lines = ["tag = POL", "is_ai = no"]
    flags = ["rn_open", "rn_input", "rn_ip_leader_open", "rn_ip_country_open", "rn_ip_party_neutrality_open"]
    for flag in flags:
        lines.append(f"has_country_flag = {flag}" if flag == own and not opening else f"NOT = {{ has_country_flag = {flag} }}")
    if opening and kind == "party":
        lines.append("has_government = neutrality")
    return lines


def guard(kind):
    target = "rn_ip_country_target" if kind == "country" else "rn_ip_party_target"
    lines = [temp("rn_pair_err", "7"), temp("rn_pair_field", "0"), temp("rn_pair_bad", "-1"), "if = {", "\tlimit = {"]
    lines += ["\t\t" + line for line in context(kind)]
    lines += ["\t}", "\t" + temp("rn_pair_err", "8"),
              "\t" + temp("rn_pair_epoch_round", "rn_ip_epoch"), "\tround_temp_variable = rn_pair_epoch_round",
              "\tif = {", "\t\tlimit = {", "\t\t\tcheck_variable = { rn_ip_epoch > 0 }",
              "\t\t\tcheck_variable = { temp_var:rn_pair_epoch_round = rn_ip_epoch }",
              "\t\t\tcheck_variable = { temp_var:rn_ip_cmd_epoch = rn_ip_epoch }", "\t\t}",
              "\t\t" + temp("rn_pair_err", "9"), "\t\tif = {", "\t\t\tlimit = {",
              f"\t\t\t\tcheck_variable = {{ {target}^num = 1 }}",
              f"\t\t\t\tis_in_array = {{ array = {target} value = THIS }}"]
    if kind == "party":
        lines += ["\t\t\t\tcheck_variable = { rn_ip_party_group = 4 }", "\t\t\t\thas_government = neutrality"]
    lines += ["\t\t\t}"]
    if kind == "country":
        lines += ["\t\t\t" + temp("rn_pair_err", "10"), "\t\t\tif = {",
                  "\t\t\t\tlimit = { check_variable = { temp_var:rn_native_cap = 1 } }",
                  "\t\t\t\t" + temp("rn_pair_err", "0"), "\t\t\t}"]
    else:
        lines += ["\t\t\t" + temp("rn_pair_err", "0")]
    lines += ["\t\t}", "\t}", "}"]
    return effect("rn_inline_pair_guard_" + kind, lines)


def cleanup(kind):
    flag = "rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"
    target = "rn_ip_country_target" if kind == "country" else "rn_ip_party_target"
    lines = [f"clr_country_flag = {flag}", f"clear_array = {target}"]
    if kind == "party":
        lines += ["clear_variable = rn_ip_party_group"]
    return lines + ["add_to_variable = { rn_ip_epoch = 1 }"]


def lifecycle(kind):
    flag = "rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"
    target = "rn_ip_country_target" if kind == "country" else "rn_ip_party_target"
    lines = ["if = {", "\tlimit = {"] + ["\t\t" + line for line in context(kind, opening=True)]
    lines += ["\t}", f"\tclear_array = {target}", f"\tadd_to_array = {{ {target} = THIS }}"]
    if kind == "party":
        lines += ["\tset_variable = { rn_ip_party_group = 4 }"]
    lines += ["\tadd_to_variable = { rn_ip_epoch = 1 }", f"\tset_country_flag = {flag}", "}"]
    result = effect("rn_inline_pair_open_" + kind, lines)
    lines = ["if = {", f"\tlimit = {{ tag = POL is_ai = no has_country_flag = {flag} }}"]
    lines += ["\t" + line for line in cleanup(kind)] + ["}"]
    return result + effect("rn_inline_pair_cancel_" + kind, lines)


def copy_buffer(array, length, prefix):
    lines = [f"clear_array = {array}"]
    for i in range(32):
        lines.append(f"if = {{ limit = {{ check_variable = {{ temp_var:{prefix}len > {i} }} }} add_to_array = {{ {array} = temp_var:{prefix}{i} }} }}")
    return lines + [f"set_variable = {{ {length} = temp_var:{prefix}len }}"]


def slots(prefix):
    return "".join(f"[ROOT.RN_{prefix}_{i}]" for i in range(32))


def apply(kind):
    lines = ["rn_inline_pair_guard_" + kind + " = yes", "if = {",
             "\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
             "\trn_inline_pair_validate = yes", "\tif = {",
             "\t\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
             "\t\t# Recheck the COMPLETE context/epoch/pin/capability after both payloads.",
             "\t\trn_inline_pair_guard_" + kind + " = yes", "\t\tif = {",
             "\t\t\tlimit = { check_variable = { temp_var:rn_pair_err = 0 } }",
             "\t\t\t# First persistent write below: every guard and both inputs passed."]
    destinations = [("rn_cname", "rn_cname_len", "rn_native_"), ("rn_cadj", "rn_cadj_len", "rn_nativeb_")] if kind == "country" else [
                   ("rn_pshort", "rn_pshort_len", "rn_native_"), ("rn_plong", "rn_plong_len", "rn_nativeb_")]
    for array, length, prefix in destinations:
        lines += ["\t\t\t" + line for line in copy_buffer(array, length, prefix)]
    if kind == "country":
        lines += ["\t\t\t# Existing RN_N/RN_J encode both fields in ONE RN1 cosmetic tag.", "\t\t\trn_apply_country_name = yes"]
    else:
        lines += ["\t\t\t# One setter carries both literal strings; no group/subtype inference.",
                  "\t\t\tmeta_effect = {", '\t\t\t\ttext = { set_party_name = { ideology = neutrality name = "[S]" long_name = "[L]" } }',
                  '\t\t\t\tS = "' + slots("PS") + '"', '\t\t\t\tL = "' + slots("PL") + '"', "\t\t\t}"]
    lines += ["\t\t\t" + line for line in cleanup(kind)]
    lines += ["\t\t}", "\t}", "}", "if = {", "\tlimit = { NOT = { check_variable = { temp_var:rn_pair_err = 0 } } }",
              '\tlog = "RN pair ' + kind + ' Apply rejected err=[?temp_var:rn_pair_err] field=[?temp_var:rn_pair_field] bad=[?temp_var:rn_pair_bad]"', "}"]
    return effect("rn_inline_pair_apply_" + kind, lines)


def party_loc():
    lines = ["# NEW INACTIVE party buffers. Depends on main mod RN_CH_0..84.",
             "# 32 slots per independent buffer, explicit ROOT COUNTRY in meta_effect.",
             "# RN_PS/RN_PL are slot prefixes; RN_PS_0..31 and RN_PL_0..31 are defined.", ""]
    for prefix, array, length in [("PS", "rn_pshort", "rn_pshort_len"), ("PL", "rn_plong", "rn_plong_len")]:
        for i in range(32):
            lines += ["defined_text = {", f"\tname = RN_{prefix}_{i}",
                      f"\ttext = {{ trigger = {{ NOT = {{ check_variable = {{ {length} > {i} }} }} }} localization_key = RN_CH_0 }}"]
            for code in range(1, 85):
                lines += [f"\ttext = {{ trigger = {{ check_variable = {{ {array}^{i} = {code} }} }} localization_key = RN_CH_{code} }}"]
            lines += ["\ttext = { localization_key = RN_CH_0 }", "}"]
    return "\n".join(lines) + "\n"


def main():
    pair_sha = hashlib.sha256((COMMON / "scripted_effects/rn_inline_pair_payload.txt").read_bytes()).hexdigest()
    assert pair_sha == "e278dfac3a4e3ac5ccca7d7cf74da9d87f0de728d30bca875d543f24956f6fc7", "pair helper changed; review first"
    source = """# NEW INACTIVE source-only candidates; NOT connected to any GUI or transport.
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
    for kind in ("country", "party"):
        source += guard(kind) + lifecycle(kind) + apply(kind)
    APPLY.parent.mkdir(parents=True, exist_ok=True)
    APPLY.write_text(source.rstrip() + "\n", encoding="utf-8", newline="\n")
    LOC.parent.mkdir(parents=True, exist_ok=True)
    LOC.write_text(party_loc(), encoding="utf-8", newline="\n")
    record_keys = ["rn_native_" + s for s in ["ok", "len", *map(str, range(32))]] + ["rn_nativeb_" + s for s in ["ok", "len", *map(str, range(32))]] + ["rn_ip_cmd_epoch"]
    lengths = {key: len(key.encode("ascii")) for key in record_keys + ["rn_native_cap"]}
    assert len(record_keys) == 69 and len(lengths) == 70 and max(lengths.values()) <= 15
    manifest = {"status": "offline source-only, inactive, root review required before any runtime",
                "new_sources": [str(p.relative_to(REPO)).replace('\\','/') for p in (APPLY, LOC)],
                "outputs": {str(p.relative_to(REPO)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in (APPLY, LOC)},
                "strict_pair_dependency_sha256": pair_sha,
                "apply_entries": ["rn_inline_pair_apply_country", "rn_inline_pair_apply_party"],
                "future_lifecycle_not_called": ["rn_inline_pair_open_country", "rn_inline_pair_cancel_country", "rn_inline_pair_open_party", "rn_inline_pair_cancel_party"],
                "party_group": "base neutrality only, pinned logical4; no custom subtype/all-ideology claim",
                "native_record_counts": {"party": 69, "country": 70}, "ascii_key_lengths": lengths,
                "capability": "fresh rn_native_cap=1 only from active versioned country DLL export; no saved flag/module shortcut",
                "first_write_policy": "pure validation of both A/B then full repeated context/epoch/typed pin/current party/cap guard",
                "protected_legacy_buffer": ["rn_buf", "rn_len"], "activation": False, "runtime": "not tested"}
    (HERE / "contract.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Generated2 NEW inactive sources;8 effects,64 party localisation slots; no existing helper/GUI/native/config edits.")


if __name__ == "__main__":
    main()
