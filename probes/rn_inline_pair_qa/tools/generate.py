"""Generate only this unloaded fixture and the explicitly owned new pair helper.

This does not register a mod, change configuration, or run the game. The reviewed
single helper is copied as bytes and never edited. Run from any working directory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
SHARED = REPO / "probes/rn_in_place_ui/common/scripted_effects"
SUFFIXES = ["ok", "len", *map(str, range(32))]
BUFFERS = [("rn_buf", "rn_len"), ("rn_cname", "rn_cname_len"),
           ("rn_cadj", "rn_cadj_len"), ("rn_pshort", "rn_pshort_len"),
           ("rn_plong", "rn_plong_len")]


def write(relative, text, bom=False):
    target = HERE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8-sig" if bom else "utf-8", newline="\n")


def effect(name, lines):
    return name + " = {\n" + "\n".join("\t" + line for line in lines) + "\n}\n\n"


def settemp(key, source):
    return f"set_temp_variable = {{ {key} = {source} }}"


def copytemps(destination, source):
    return [settemp(destination + suffix, "temp_var:" + source + suffix) for suffix in SUFFIXES]


def pair_helper():
    head = """# Pure two-field validator. No persistent writes, target changes or setters.
# Inputs: complete A rn_native_* and B rn_nativeb_* (ok,len,0..31 each).
# Outputs: rn_pair_err, rn_pair_field (0 success;1 A;2 B), rn_pair_bad.
# Error codes are the unchanged strict single helper's 1/4/5/6; bad=-1
# except active-code/padding failures. A rejects before B is aliased.
# Valid A is backed up in private TEMP rn_paira_* and ALWAYS restored after B.
# B is read-only. rn_inline_* are scratch and may describe B after return.
# This is validation only: callers must separately recheck own target, epoch,
# capability where needed, and both results BEFORE any persistent buffer write.

"""
    lines = [settemp("rn_pair_err", "0"), settemp("rn_pair_field", "0"),
             settemp("rn_pair_bad", "-1"), "rn_inline_validate_payload = yes",
             "if = {", "\tlimit = { NOT = { check_variable = { temp_var:rn_inline_error = 0 } } }",
             "\t" + settemp("rn_pair_err", "temp_var:rn_inline_error"),
             "\t" + settemp("rn_pair_field", "1"),
             "\t" + settemp("rn_pair_bad", "temp_var:rn_inline_bad_index"),
             "}", "else = {"]
    lines += ["\t" + line for line in copytemps("rn_paira_", "rn_native_")]
    lines += ["\t" + line for line in copytemps("rn_native_", "rn_nativeb_")]
    lines += ["\trn_inline_validate_payload = yes",
              "\t" + settemp("rn_pair_err", "temp_var:rn_inline_error"),
              "\t" + settemp("rn_pair_bad", "temp_var:rn_inline_bad_index"),
              "\tif = {", "\t\tlimit = { NOT = { check_variable = { temp_var:rn_inline_error = 0 } } }",
              "\t\t" + settemp("rn_pair_field", "2"), "\t}"]
    lines += ["\t" + line for line in copytemps("rn_native_", "rn_paira_")]
    lines += ["}"]
    return head + effect("rn_inline_pair_validate", lines)


def producer(name, acount, bcount, omit=None):
    lines = []
    for prefix, count, first in [("rn_native_", acount, 84), ("rn_nativeb_", bcount, 1)]:
        for suffix in SUFFIXES:
            if prefix + suffix == omit:
                continue
            value = 1 if suffix == "ok" else count if suffix == "len" else 0
            if suffix.isdigit() and int(suffix) < count:
                value = first - int(suffix) if first == 84 else first + int(suffix)
            lines.append(settemp(prefix + suffix, str(value)))
    return effect(name, lines)


def diagnostics():
    result = """# UNLOADED script-only pair diagnostics. No real rename/party/country effects.
# QA owns rn_prq_* snapshots only; rn_buf/cname/cadj/pshort/plong are READ ONLY.
# All34 A and34 B values are compared against independent rn_prq_a/b_* TEMP
# copies, not the implementation's rn_paira_* scratch. Missing markers are
# deliberately omitted only in their own fresh SG commands, never a batch.
# Scalar length presence and full arrays are checked; no rollback hides FAIL.

"""
    result += producer("rn_prq_payload_a1_b32", 1, 32)
    result += producer("rn_prq_payload_a32_b1", 32, 1)
    result += producer("rn_prq_payload_a32_b32", 32, 32)
    result += producer("rn_prq_payload_a1_b1", 1, 1)
    result += producer("rn_prq_payload_missing_a", 32, 1, "rn_native_ok")
    result += producer("rn_prq_payload_missing_b", 32, 1, "rn_nativeb_ok")
    result += effect("rn_prq_snapshot_temps", copytemps("rn_prq_a_", "rn_native_") + copytemps("rn_prq_b_", "rn_nativeb_"))
    lines = [settemp("rn_prq_adiff", "0"), settemp("rn_prq_bdiff", "0")]
    for prefix, backup, diff in [("rn_native_", "rn_prq_a_", "rn_prq_adiff"),
                                 ("rn_nativeb_", "rn_prq_b_", "rn_prq_bdiff")]:
        for suffix in SUFFIXES:
            lines.append(f"if = {{ limit = {{ NOT = {{ check_variable = {{ temp_var:{prefix}{suffix} = temp_var:{backup}{suffix} }} }} }} add_to_temp_variable = {{ {diff} = 1 }} }}")
    result += effect("rn_prq_compare_temps", lines)
    lines = []
    for i, (array, length) in enumerate(BUFFERS):
        lines += [f"clear_array = rn_prq_bak{i}", settemp(f"rn_prq_len{i}", length),
                  settemp(f"rn_prq_had{i}", "0"),
                  f"if = {{ limit = {{ has_variable = {length} }} {settemp(f'rn_prq_had{i}', '1')} }}",
                  f"for_each_loop = {{ array = {array} value = rn_prq_v add_to_array = {{ rn_prq_bak{i} = rn_prq_v }} }}"]
    result += effect("rn_prq_snapshot_buffers", lines)
    lines = [settemp("rn_prq_pdiff", "0")]
    for i, (array, length) in enumerate(BUFFERS):
        for limit in [f"NOT = {{ check_variable = {{ {length} = temp_var:rn_prq_len{i} }} }}",
                      f"NOT = {{ check_variable = {{ {array}^num = rn_prq_bak{i}^num }} }}",
                      f"check_variable = {{ temp_var:rn_prq_had{i} = 0 }} has_variable = {length}",
                      f"check_variable = {{ temp_var:rn_prq_had{i} = 1 }} NOT = {{ has_variable = {length} }}"]:
            lines.append(f"if = {{ limit = {{ {limit} }} add_to_temp_variable = {{ rn_prq_pdiff = 1 }} }}")
        lines.append(f"for_each_loop = {{ array = {array} value = rn_prq_v index = rn_prq_i if = {{ limit = {{ NOT = {{ check_variable = {{ rn_prq_v = rn_prq_bak{i}^rn_prq_i }} }} }} add_to_temp_variable = {{ rn_prq_pdiff = 1 }} }} }}")
    result += effect("rn_prq_compare_buffers", lines)
    lines = ["rn_prq_snapshot_temps = yes", "rn_prq_snapshot_buffers = yes", "rn_inline_pair_validate = yes",
             "rn_prq_compare_temps = yes", "rn_prq_compare_buffers = yes", "if = {", "\tlimit = {"]
    for actual, expected in [("rn_pair_err", "rn_prq_want_err"), ("rn_pair_field", "rn_prq_want_field"),
                             ("rn_pair_bad", "rn_prq_want_bad")]:
        lines.append(f"\t\tcheck_variable = {{ temp_var:{actual} = temp_var:{expected} }}")
    for diff in ("rn_prq_adiff", "rn_prq_bdiff", "rn_prq_pdiff"):
        lines.append(f"\t\tcheck_variable = {{ temp_var:{diff} = 0 }}")
    observed = "err=[?rn_pair_err|0] field=[?rn_pair_field|0] bad=[?rn_pair_bad|0] adiff=[?rn_prq_adiff|0] bdiff=[?rn_prq_bdiff|0] pdiff=[?rn_prq_pdiff|0]"
    lines += ["\t}", f'\tlog = "RN_PRQ case=[?rn_prq_case|0] PASS {observed}"', "}",
              f'else = {{ log = "RN_PRQ case=[?rn_prq_case|0] FAIL {observed} want=[?rn_prq_want_err|0],[?rn_prq_want_field|0],[?rn_prq_want_bad|0]" }}']
    lines += [f"clear_array = rn_prq_bak{i}" for i in range(len(BUFFERS))]
    result += effect("rn_prq_check", lines)
    cases = []

    def case(ident, group, payload, overrides, expected, description):
        body = [payload + " = yes"]
        body += [settemp(key, value) for key, value in overrides]
        body += [settemp("rn_prq_case", str(ident)), settemp("rn_prq_want_err", str(expected[0])),
                 settemp("rn_prq_want_field", str(expected[1])), settemp("rn_prq_want_bad", str(expected[2])),
                 "rn_prq_check = yes"]
        cases.append({"id": ident, "group": group, "description": description,
                      "expected": {"error": expected[0], "field": expected[1], "bad_index": expected[2]},
                      "payload": payload, "overrides": dict(overrides)})
        return effect(f"rn_prq_case_{ident}", body)

    result += case(1, "rn_prq_valid", "rn_prq_payload_a1_b32", [], (0, 0, -1), "A length1/code84; B length32/codes1..32")
    result += case(2, "rn_prq_valid", "rn_prq_payload_a32_b1", [], (0, 0, -1), "A length32/codes84..53; B length1/code1")
    invalid = [("ok", "0", 1, -1, "zero marker"), ("ok", "2", 1, -1, "wrong marker"),
               ("len", "0", 4, -1, "zero length"), ("len", "33", 4, -1, "overlong length"),
               ("len", "1.5", 4, -1, "fractional length"), ("len", "1.00001", 4, -1, "fractional length lower edge"),
               ("len", "31.99999", 4, -1, "fractional length upper edge"),
               ("0", "0", 5, 0, "zero active code"), ("0", "85", 5, 0, "code above alphabet"),
               ("0", "1.5", 5, 0, "fractional active code"), ("0", "1.00001", 5, 0, "fractional code lower edge"),
               ("0", "83.99999", 5, 0, "fractional code upper edge"),
               ("31", "0", 5, 31, "zero final active code"), ("31", "85", 5, 31, "invalid final active code"),
               ("1", "1", 6, 1, "first padding nonzero"), ("31", "1", 6, 31, "last padding nonzero"),
               ("31", "0.00001", 6, 31, "fractional padding nonzero")]
    for field, group, prefix, base in [(1, "rn_prq_invalid_a", "rn_native_", 100),
                                        (2, "rn_prq_invalid_b", "rn_nativeb_", 200)]:
        for offset, (suffix, value, err, bad, description) in enumerate(invalid):
            # B rejection always begins with full distinct A32, proving every
            # backup/restore slot. A padding uses A1; B padding uses B1.
            payload = "rn_prq_payload_a32_b32" if err != 6 else ("rn_prq_payload_a1_b32" if field == 1 else "rn_prq_payload_a32_b1")
            result += case(base + offset, group, payload, [(prefix + suffix, value)],
                           (err, field, bad), f"field{field}: {description}")
    result += case(300, "rn_prq_priority", "rn_prq_payload_a1_b32",
                   [("rn_native_ok", "0"), ("rn_nativeb_ok", "0")], (1, 1, -1), "both markers0: first field wins")
    result += case(301, "rn_prq_missing_a", "rn_prq_payload_missing_a", [], (1, 1, -1), "A marker not created in this fresh command")
    result += case(302, "rn_prq_missing_b", "rn_prq_payload_missing_b", [], (1, 2, -1), "B marker not created in this fresh command")
    groups = {}
    for entry in cases:
        groups.setdefault(entry["group"], []).append(entry["id"])
    for group, ids in groups.items():
        result += effect(group, [f"rn_prq_case_{ident} = yes" for ident in ids])
    return result, cases, groups


def ui(groups):
    buttons = [("valid", "Valid 1/32", "Poprawne 1/32"), ("invalid_a", "Invalid A", "Błędne A"),
               ("invalid_b", "Invalid B", "Błędne B"), ("priority", "Both invalid", "Oba błędne"),
               ("missing_a", "Missing A", "Brak A"), ("missing_b", "Missing B", "Brak B")]
    guard = "tag = POL is_ai = no NOT = { has_country_flag = rn_input } NOT = { has_country_flag = rn_open }"
    sg = ['# UNLOADED script-only QA, outside every native whitelist.', 'scripted_gui = {', '\trn_prq_gui = {',
          '\t\tcontext_type = player_context', '\t\twindow_name = "rn_prq_window"',
          '\t\tvisible = { tag = POL is_ai = no }', '\t\tai_enabled = { always = no }', '\t\teffects = {']
    for key, _, _ in buttons:
        assert "rn_prq_" + key in groups
        sg.append(f"\t\t\trn_prq_{key}_click = {{ if = {{ limit = {{ {guard} }} rn_prq_{key} = yes }} }}")
    sg += ['\t\t}', '\t\ttriggers = {']
    sg += [f"\t\t\trn_prq_{key}_click_enabled = {{ {guard} }}" for key, _, _ in buttons]
    sg += ['\t\t}', '\t}', '}']
    write("common/scripted_guis/rn_prq_gui.txt", "\n".join(sg) + "\n")
    gui = ['guiTypes = {', '\tcontainerWindowType = {', '\t\tname = "rn_prq_window"', '\t\torientation = upper_left',
           '\t\tposition = { x = 900 y = 80 }', '\t\tsize = { width = 290 height = 208 }', '\t\tclipping = no',
           '\t\tbackground = { name = "Background" quadTextureSprite = "GFX_tiled_window_2b_border" }',
           '\t\tinstantTextboxType = { name = "rn_prq_title" position = { x = 12 y = 10 } font = "hoi_18mbs" text = "RN_PRQ_TITLE" maxWidth = 266 maxHeight = 24 fixedsize = yes }']
    for i, (key, _, _) in enumerate(buttons):
        x, y = 12 + 137 * (i % 2), 42 + 42 * (i // 2)
        gui.append(f'\t\tbuttonType = {{ name = "rn_prq_{key}" position = {{ x = {x} y = {y} }} spriteType = "GFX_button_123x34" buttonText = "RN_PRQ_{key.upper()}" buttonFont = "hoi_16mbs" clicksound = click_default }}')
    gui += ['\t\tinstantTextboxType = { name = "rn_prq_note" position = { x = 12 y = 172 } font = "hoi_16mbs" text = "RN_PRQ_NOTE" maxWidth = 266 maxHeight = 28 fixedsize = yes }', '\t}', '}']
    write("interface/rn_prq.gui", "\n".join(gui) + "\n")
    for language, index, title, note in [("english", 1, "Pair payload QA", "Logs only; buffers read only."),
                                         ("polish", 2, "QA pary payloadów", "Tylko logi; bufory bez zmian.")]:
        loc = [f"l_{language}:", f' RN_PRQ_TITLE: "{title}"']
        loc += [f' RN_PRQ_{key.upper()}: "{item[index]}"' for item in buttons for key in [item[0]]]
        loc += [f' RN_PRQ_NOTE: "{note}"']
        write(f"localisation/{language}/rn_prq_l_{language}.yml", "\n".join(loc) + "\n", bom=True)


def main():
    single = (SHARED / "rn_inline_payload.txt").read_bytes()
    sha = hashlib.sha256(single).hexdigest()
    assert sha == "cd171d6203bd66dc7905c7c3d0e1a2750c4b8eabab45f0540d75d3af2ce10800", "single helper changed; review first"
    pair = pair_helper()
    # Only this new file in the explicitly assigned inactive source directory.
    (SHARED / "rn_inline_pair_payload.txt").write_text(pair, encoding="utf-8", newline="\n")
    write("common/scripted_effects/rn_inline_pair_payload.txt", pair)
    (HERE / "common/scripted_effects/rn_inline_payload.txt").write_bytes(single)
    diag, cases, groups = diagnostics()
    write("common/scripted_effects/rn_prq_diagnostics.txt", diag)
    ui(groups)
    write("descriptor.mod", 'name="Rename Anything pair payload QA (temporary)"\nversion="0.0.1"\nsupported_version="1.19.*"\n')
    keys = ["rn_native_" + s for s in SUFFIXES] + ["rn_nativeb_" + s for s in SUFFIXES]
    lengths = {key: len(key.encode("ascii")) for key in keys + ["rn_ip_cmd_epoch", "rn_native_cap"]}
    assert len(set(keys)) == 68 and max(lengths.values()) <= 15
    contract = {
        "status": "unloaded; source-only; runtime pending root review",
        "entry": "rn_inline_pair_validate", "inputs": keys,
        "outputs": {"rn_pair_err": "0 success;1 marker;4 length;5 code;6 padding",
                    "rn_pair_field": "0 success;1 A;2 B", "rn_pair_bad": "-1 unless code/padding index"},
        "single_helper_sha256": sha,
        "pair_helper_sha256": hashlib.sha256(pair.encode("utf-8")).hexdigest(),
        "preserved": "all34 values of A and B; no persistent writes",
        "scratch": "rn_inline_* may contain B result; private temp rn_paira_* overwritten",
        "buffers_observed": [{"array": a, "length": n} for a, n in BUFFERS],
        "key_ascii_byte_lengths": lengths,
        "future_only_not_validated": ["rn_ip_cmd_epoch", "rn_native_cap", "own target", "country/party setters"],
        "qa_groups": groups, "qa_cases": cases,
        "missing_marker_note": "Dedicated fresh SG command omits marker assignment; value-level comparisons do not prove temp-record presence.",
        "not_loaded_with": ["rn_in_place_ui", "rn_inline_payload_qa", "rn_inline_leader_apply_qa"],
        "allowed_exact_qa_co_load": ["mod/", "probes/rn_inline_leader_transport_qa/", "probes/rn_inline_pair_qa/"],
        "co_load_conditions": ["root review before freshprocess activation", "transport fixture retains log-only leader Apply and disabled party Apply",
                               "pair commands remain rn_prq_gui and outside native whitelist", "no pair records injected into editor model",
                               "native transport and pure validation assessed separately", "no real rename Apply or setters invoked"],
        "co_load_evidence": "co-load-review.json; exact SG/GUI/effect/localisation inventories and reachable write targets",
        "native_transport": False, "rename_or_target_write": False,
    }
    write("contract.json", json.dumps(contract, ensure_ascii=False, indent=2) + "\n")
    print(f"Generated unloaded fixture: {len(cases)} cases / {len(groups)} buttons; single helper byte copy {sha}.")


if __name__ == "__main__":
    main()
