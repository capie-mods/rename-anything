"""Offline execution of actual candidate Pdx source in a limited contract model.

No HOI4 process, parser, native setter or capability export is exercised here.
The source VM only records emitted setter requests; those are not rename tests.
"""
from __future__ import annotations

import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SHARED = REPO / "probes/rn_in_place_ui/common"
sys.path.insert(0, str(REPO / "probes/rn_inline_pair_qa/tools"))
from check import BUFFERS, VM, parse, payload, pure_audit

APPLY = SHARED / "scripted_effects/rn_inline_pair_apply.txt"
PARTY_LOC = SHARED / "scripted_localisation/rn_inline_party_buffers.txt"


class Country:
    def __init__(self, tag):
        self.tag = tag
    def __eq__(self, other):
        return isinstance(other, Country) and self.tag == other.tag
    def __repr__(self):
        return "Country(" + self.tag + ")"


class ApplyVM(VM):
    def __init__(self, effects, locs, chars, kind, tag="POL", ai=False):
        temp = {**payload("rn_native_", 1, 84), **payload("rn_nativeb_", 32, 1),
                "rn_ip_cmd_epoch": Decimal(7), "rn_native_cap": Decimal(1)}
        persistent = {"rn_ip_epoch": Decimal(7), "rn_ip_party_group": Decimal(4)}
        arrays = {name: [Decimal(11 + i), Decimal(84 - i)] for i, (name, length) in enumerate(BUFFERS)}
        for i, (_, length) in enumerate(BUFFERS):
            persistent[length] = Decimal(i + 2)
        arrays["rn_ip_country_target"] = [Country(tag)]
        arrays["rn_ip_party_target"] = [Country(tag)]
        super().__init__(effects, temp, persistent, arrays)
        self.tag, self.ai, self.government = tag, ai, "neutrality"
        self.kind = kind
        self.flags = {"rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"}
        self.locs, self.chars, self.requests = locs, chars, []
        self.guard_count, self.pair_count, self.pair_complete = 0, 0, False
        self.enforce, self.late_mutation = True, None
        self.trace = []

    def value(self, token):
        if token in ("THIS", "ROOT"):
            return Country(self.tag)
        return super().value(token)

    def condition(self, nodes):
        for key, _, value in nodes:
            if key == "tag":
                answer = self.tag == value
            elif key == "is_ai":
                answer = self.ai == (value == "yes")
            elif key == "has_country_flag":
                answer = value in self.flags
            elif key == "has_government":
                answer = self.government == value
            elif key == "is_in_array":
                params = {k: v for k, _, v in value}
                answer = self.value(params["value"]) in self.arrays.get(params["array"], [])
            elif key == "rn_country_rename_enabled":
                answer = value == "yes"  # Actual main-mod trigger is always=yes.
            else:
                answer = super().condition([(key, "=", value)])
            if not answer:
                return False
        return True

    def run(self, name):
        super().run(name)
        if name == "rn_inline_pair_validate":
            self.pair_count += 1
            self.pair_complete = self.value("temp_var:rn_pair_err") == 0
            if self.pair_complete and self.late_mutation:
                callback, self.late_mutation = self.late_mutation, None
                callback(self)
        if name == "rn_inline_pair_guard_" + self.kind:
            self.guard_count += 1

    def assert_write_barrier(self, key):
        if self.enforce:
            assert self.pair_count == 1 and self.pair_complete, ("write before both payloads valid", key)
            assert self.guard_count == 2 and self.value("temp_var:rn_pair_err") == 0, ("write before late guard", key)
        self.trace.append(key)

    def localized(self, name):
        for _, _, text in self.locs[name]:
            if not isinstance(text, list):
                continue
            trigger = next((v for k, _, v in text if k == "trigger"), [])
            if not trigger or self.condition(trigger):
                key = next(v for k, _, v in text if k == "localization_key")
                return self.chars[key]
        raise AssertionError(("unresolved scripted loc", name))

    def execute(self, nodes):
        # Base VM owns branch control. Only add the missing primitive operations.
        if len(nodes) != 1 or nodes[0][0] in ("if", "else_if", "else"):
            branch_taken = None
            for key, op, value in nodes:
                if key in ("if", "else_if", "else"):
                    if key == "if":
                        branch_taken = False
                    limit = next((v for k, _, v in value if k == "limit"), [])
                    if not branch_taken and (key == "else" or self.condition(limit)):
                        self.execute([n for n in value if n[0] != "limit"])
                        branch_taken = True
                else:
                    branch_taken = None
                    self.execute([(key, op, value)])
            return
        key, _, value = nodes[0]
        if key in ("set_variable", "add_to_variable"):
            self.assert_write_barrier(key)
            name, _, source = value[0]
            prior = self.persistent.get(name, Decimal(0)) if key == "add_to_variable" else Decimal(0)
            self.persistent[name] = prior + self.value(source)
        elif key == "clear_variable":
            self.assert_write_barrier(key)
            self.persistent.pop(value, None)
        elif key in ("set_country_flag", "clr_country_flag"):
            self.assert_write_barrier(key)
            (self.flags.add if key == "set_country_flag" else self.flags.discard)(value)
        elif key == "meta_effect":
            self.assert_write_barrier(key)
            params = {k: v for k, _, v in value}
            substitutions = {k: re.sub(r"\[ROOT\.([^]]+)\]", lambda m: self.localized(m[1]), v)
                             for k, v in params.items() if k != "text"}
            text = copy.deepcopy(params["text"])
            def substitute(items):
                out = []
                for k, op, v in items:
                    if isinstance(v, list):
                        v = substitute(v)
                    else:
                        for token, literal in substitutions.items():
                            v = v.replace("[" + token + "]", literal)
                    out.append((k, op, v))
                return out
            self.requests.append(substitute(text))
        else:
            if key in ("clear_array", "add_to_array"):
                self.assert_write_barrier(key)
            super().execute(nodes)

    def state(self):
        return copy.deepcopy((self.persistent, self.arrays, self.flags))


def load():
    assert APPLY.exists() and PARTY_LOC.exists(), "missing new Apply/party-buffer implementation"
    pair = SHARED / "scripted_effects/rn_inline_pair_payload.txt"
    single = SHARED / "scripted_effects/rn_inline_payload.txt"
    assert hashlib.sha256(pair.read_bytes()).hexdigest() == "e278dfac3a4e3ac5ccca7d7cf74da9d87f0de728d30bca875d543f24956f6fc7"
    assert hashlib.sha256(single.read_bytes()).hexdigest() == "cd171d6203bd66dc7905c7c3d0e1a2750c4b8eabab45f0540d75d3af2ce10800"
    paths = [single, pair, APPLY, REPO / "mod/common/scripted_effects/rename_anything_generated_effects.txt"]
    effects = {name: body for path in paths for name, _, body in parse(path.read_text(encoding="utf-8-sig"))}
    locs = {}
    for path in (PARTY_LOC, REPO / "mod/common/scripted_localisation/rename_anything_scripted_loc.txt"):
        for _, _, body in parse(path.read_text(encoding="utf-8-sig")):
            locs[next(v for k, _, v in body if k == "name")] = [n for n in body if n[0] == "text"]
    source = (REPO / "mod/localisation/english/rename_anything_chars_l_english.yml").read_text(encoding="utf-8-sig")
    chars = {name: json.loads(literal) for name, literal in re.findall(r'^ (RN_CH_\d+):\s*(".*")\s*$', source, re.M)}
    assert len(chars) == 85
    trigger_source = REPO / "mod/common/scripted_triggers/rename_anything_triggers.txt"
    triggers = dict((k, v) for k, _, v in parse(trigger_source.read_text(encoding="utf-8-sig")))
    assert triggers["rn_country_rename_enabled"] == [("always", "=", "yes")], "country setter enable assumption changed"
    new_effects = parse(APPLY.read_text(encoding="utf-8"))
    assert len(new_effects) == 8 and len({name for name, _, _ in new_effects}) == 8
    pair_names = {name for path in (single, pair) for name, _, _ in parse(path.read_text(encoding="utf-8-sig"))}
    main_names = {name for name, _, _ in parse(paths[-1].read_text(encoding="utf-8-sig"))}
    assert not {name for name, _, _ in new_effects} & (pair_names | main_names), "effect name collision"
    new_loc_names = [next(v for k, _, v in body if k == "name") for _, _, body in parse(PARTY_LOC.read_text(encoding="utf-8"))]
    assert set(new_loc_names) == {f"RN_{prefix}_{i}" for prefix in ("PS", "PL") for i in range(32)} and len(new_loc_names) == 64
    main_loc_names = {next(v for k, _, v in body if k == "name") for _, _, body in parse((REPO / "mod/common/scripted_localisation/rename_anything_scripted_loc.txt").read_text(encoding="utf-8-sig"))}
    assert not set(new_loc_names) & main_loc_names, "scripted localisation name collision"
    return effects, locs, chars


def main():
    effects, locs, chars = load()
    for kind in ("country", "party"):
        pure_audit(effects, "rn_inline_pair_guard_" + kind)
    pure_audit(effects, "rn_inline_pair_validate")
    assertions, rejection_cases, lifecycle_cases, loc_checks = 0, 0, 0, 0
    for kind in ("country", "party"):
        def fresh():
            return ApplyVM(effects, locs, chars, kind)

        def reject(mutate, want, field=0, bad=-1, late=False):
            nonlocal rejection_cases
            vm = fresh()
            expected = []
            if late:
                def callback(current):
                    mutate(current)
                    expected.append(current.state())
                vm.late_mutation = callback
            else:
                mutate(vm)
                expected.append(vm.state())
            vm.run("rn_inline_pair_apply_" + kind)
            assert vm.state() == expected[0], (kind, want, "rejection mutated persistent state")
            assert not vm.requests and not vm.trace, (kind, want, "rejected setter/write")
            actual = tuple(int(vm.value("temp_var:" + n)) for n in ("rn_pair_err", "rn_pair_field", "rn_pair_bad"))
            assert actual == (want, field, bad), (kind, actual, (want, field, bad))
            rejection_cases += 1

        reject(lambda vm: setattr(vm, "tag", "GER"), 7)
        reject(lambda vm: setattr(vm, "ai", True), 7)
        own_flag = "rn_ip_country_open" if kind == "country" else "rn_ip_party_neutrality_open"
        reject(lambda vm: vm.flags.discard(own_flag), 7)
        other_flags = ["rn_open", "rn_input", "rn_ip_leader_open", "rn_ip_party_neutrality_open" if kind == "country" else "rn_ip_country_open"]
        for flag in other_flags:
            reject(lambda vm, f=flag: vm.flags.add(f), 7)
        reject(lambda vm: vm.persistent.update(rn_ip_epoch=Decimal(0)), 8)
        reject(lambda vm: vm.temp.update(rn_ip_cmd_epoch=Decimal(8)), 8)
        reject(lambda vm: vm.temp.pop("rn_ip_cmd_epoch"), 8)
        reject(lambda vm: (vm.persistent.update(rn_ip_epoch=Decimal("7.5")), vm.temp.update(rn_ip_cmd_epoch=Decimal("7.5"))), 8)
        target = "rn_ip_country_target" if kind == "country" else "rn_ip_party_target"
        for wrong in ([], [Country("GER")], [Decimal(1)], [Country("POL"), Country("POL")]):
            reject(lambda vm, values=wrong: vm.arrays.update({target: values}), 9)
        if kind == "country":
            for capability in (Decimal(0), Decimal(2), Decimal("1.00001")):
                reject(lambda vm, c=capability: vm.temp.update(rn_native_cap=c), 10)
            reject(lambda vm: vm.temp.pop("rn_native_cap"), 10)
        else:
            reject(lambda vm: vm.persistent.update(rn_ip_party_group=Decimal(3)), 9)
            reject(lambda vm: setattr(vm, "government", "fascism"), 9)
        for prefix, field in (("rn_native_", 1), ("rn_nativeb_", 2)):
            for suffix, value, err, bad in [("ok", "0", 1, -1), ("len", "1.00001", 4, -1), ("0", "1.5", 5, 0), ("0", "85", 5, 0)]:
                reject(lambda vm, p=prefix, s=suffix, v=value: vm.temp.update({p + s: Decimal(v)}), err, field, bad)
            def bad_padding(vm, p=prefix):
                vm.temp[p + "len"] = Decimal(1)
                for i in range(1, 32):
                    vm.temp[p + str(i)] = Decimal(0)
                vm.temp[p + "31"] = Decimal("0.00001")
            reject(bad_padding, 6, field, 31)
        reject(lambda vm: vm.flags.add("rn_input"), 7, late=True)
        reject(lambda vm: vm.persistent.update(rn_ip_epoch=Decimal(8)), 8, late=True)
        reject(lambda vm: vm.arrays.update({target: [Country("GER")]}), 9, late=True)
        if kind == "country":
            reject(lambda vm: vm.temp.update(rn_native_cap=Decimal(0)), 10, late=True)
        else:
            reject(lambda vm: setattr(vm, "government", "democratic"), 9, late=True)
        for alen, blen in [(1, 32), (32, 1)]:
            vm = fresh()
            vm.temp.update(payload("rn_native_", alen, 84))
            vm.temp.update(payload("rn_nativeb_", blen, 1))
            before = vm.state()
            vm.run("rn_inline_pair_apply_" + kind)
            assert vm.guard_count == 2 and vm.pair_count == 1 and len(vm.requests) == 1
            assert vm.value("temp_var:rn_pair_err") == 0 and vm.value("temp_var:rn_pair_field") == 0
            assert vm.arrays["rn_buf"] == before[1]["rn_buf"] and vm.persistent["rn_len"] == before[0]["rn_len"]
            destinations = ("rn_cname", "rn_cadj") if kind == "country" else ("rn_pshort", "rn_plong")
            lengths = ("rn_cname_len", "rn_cadj_len") if kind == "country" else ("rn_pshort_len", "rn_plong_len")
            assert vm.arrays[destinations[0]] == [Decimal(84-i) for i in range(alen)]
            assert vm.arrays[destinations[1]] == [Decimal(1+i) for i in range(blen)]
            assert vm.persistent[lengths[0]] == alen and vm.persistent[lengths[1]] == blen
            for array, length in BUFFERS:
                if array not in destinations:
                    assert vm.arrays[array] == before[1][array] and vm.persistent[length] == before[0][length]
            assert own_flag not in vm.flags and vm.arrays[target] == [] and vm.persistent["rn_ip_epoch"] == 8
            if kind == "party":
                assert "rn_ip_party_group" not in vm.persistent
                params = dict((k, v) for k, _, v in vm.requests[0][0][2])
                assert params == {"ideology": "neutrality", "name": "".join(chars[f"RN_CH_{84-i}"] for i in range(alen)),
                                  "long_name": "".join(chars[f"RN_CH_{1+i}"] for i in range(blen))}
            else:
                assert vm.requests == [[("set_cosmetic_tag", "=", "RN1|" + "".join(chars[f"RN_CH_{84-i}"] for i in range(alen)) + "|" + "".join(chars[f"RN_CH_{1+i}"] for i in range(blen)) + "|")]]
            assertions += 1
        # These entries are deliberately not called from Apply or any GUI.
        # Explicit Open/Cancel is a separate lifecycle contract, not a rejection.
        vm = fresh()
        vm.enforce = False
        vm.flags.clear()
        before_buffers = {name: list(vm.arrays[name]) for name, _ in BUFFERS}
        vm.run("rn_inline_pair_open_" + kind)
        assert vm.arrays[target] == [Country("POL")] and own_flag in vm.flags
        assert vm.persistent["rn_ip_epoch"] == 8 and not vm.requests
        if kind == "party":
            assert vm.persistent["rn_ip_party_group"] == 4
        vm.run("rn_inline_pair_cancel_" + kind)
        assert vm.arrays[target] == [] and own_flag not in vm.flags and vm.persistent["rn_ip_epoch"] == 9
        assert {name: vm.arrays[name] for name, _ in BUFFERS} == before_buffers and not vm.requests
        lifecycle_cases += 1
        for other in ("rn_open", "rn_input", "rn_ip_leader_open", "rn_ip_country_open", "rn_ip_party_neutrality_open"):
            vm = fresh()
            vm.enforce = False
            vm.flags = {other}
            before = vm.state()
            vm.run("rn_inline_pair_open_" + kind)
            assert vm.state() == before and not vm.requests, ("Open failed exclusion", kind, other)
            lifecycle_cases += 1
    vm = ApplyVM(effects, locs, chars, "party")
    for prefix, array, length in (("PS", "rn_pshort", "rn_pshort_len"), ("PL", "rn_plong", "rn_plong_len")):
        vm.persistent[length] = Decimal(32)
        for slot in range(32):
            for code in range(1, 85):
                vm.arrays[array] = [Decimal(code)] * 32
                assert vm.localized(f"RN_{prefix}_{slot}") == chars[f"RN_CH_{code}"]
                loc_checks += 1
            vm.persistent[length] = Decimal(slot)
            assert vm.localized(f"RN_{prefix}_{slot}") == "", ("length suppression failed", prefix, slot)
            vm.persistent[length] = Decimal(32)
            loc_checks += 1
    # Removing the second guard must trip the write barrier before any write.
    mutated = copy.deepcopy(effects)
    seen = 0
    def remove_late_guard(nodes):
        nonlocal seen
        for i in range(len(nodes) - 1, -1, -1):
            key, _, value = nodes[i]
            if key in ("if", "else_if", "else"):
                remove_late_guard(value)
            elif key == "rn_inline_pair_guard_country":
                seen += 1
                if seen == 1:  # Reverse walk encounters the nested late call first.
                    del nodes[i]
    remove_late_guard(mutated["rn_inline_pair_apply_country"])
    assert seen == 2
    vm = ApplyVM(mutated, locs, chars, "country")
    try:
        vm.run("rn_inline_pair_apply_country")
    except AssertionError as exc:
        assert "write before late guard" in str(exc), str(exc)
    else:
        raise AssertionError("missing late-guard mutation survived")
    report = {"scope": "Limited offline source-model only; setter requests recorded, no engine/rename/capability/GUI runtime proof",
              "rejection_invariance_cases": rejection_cases, "successful_source_request_cases": assertions,
              "future_lifecycle_source_cases": lifecycle_cases, "party_slot_localisation_checks": loc_checks,
              "missing_late_guard_mutation": "rejected before first persistent write",
              "both_payloads_before_writes": True, "late_full_guard_before_writes": True,
              "legacy_buffer_untouched": True, "activated": False, "findings": [],
              "files": {str(p.relative_to(REPO)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [APPLY, PARTY_LOC, HERE/'generate.py', HERE/'check.py', HERE/'README.md', HERE/'contract.json',
                                  SHARED/'scripted_effects/rn_inline_pair_payload.txt', SHARED/'scripted_effects/rn_inline_payload.txt',
                                  REPO/'mod/common/scripted_effects/rename_anything_generated_effects.txt',
                                  REPO/'mod/common/scripted_triggers/rename_anything_triggers.txt',
                                  REPO/'mod/localisation/english/rename_anything_chars_l_english.yml']}}
    (HERE / "static-review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Offline Apply source-model PASS: {rejection_cases} rejections, {assertions} emitted requests, {lifecycle_cases} lifecycle cases, {loc_checks} slot checks; late-guard mutation rejected. No runtime claim.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
