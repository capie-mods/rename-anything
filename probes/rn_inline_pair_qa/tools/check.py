"""Offline contract tests for the actual Pdx source; NOT an HOI4 interpreter.

The deliberately small evaluator exercises temp-copy/control-flow behavior under
documented arithmetic assumptions. Real parser, missing-temp and array behavior
must still pass the fixture in a fresh game process. Unknown syntax fails here.
"""
from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).resolve().parents[1]
REPO = FIXTURE.parents[1]
SHARED = REPO / "probes/rn_in_place_ui/common/scripted_effects"
SINGLE_SHA = "cd171d6203bd66dc7905c7c3d0e1a2750c4b8eabab45f0540d75d3af2ce10800"
SUFFIXES = ["ok", "len", *map(str, range(32))]
BUFFERS = [("rn_buf", "rn_len"), ("rn_cname", "rn_cname_len"),
           ("rn_cadj", "rn_cadj_len"), ("rn_pshort", "rn_pshort_len"),
           ("rn_plong", "rn_plong_len")]


def parse(source):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|#[^\n]*|[{}=<>]|[^\s{}=<>]+', source)
    tokens = [t for t in tokens if not t.startswith("#")]
    at = 0

    def block(nested=False):
        nonlocal at
        result = []
        while at < len(tokens) and tokens[at] != "}":
            key, op = tokens[at:at + 2]
            assert op in ("=", "<", ">"), (key, op)
            at += 2
            if tokens[at] == "{":
                at += 1
                value = block(True)
            else:
                value = tokens[at].strip('"')
                at += 1
            result.append((key, op, value))
        if nested:
            assert at < len(tokens) and tokens[at] == "}", "unclosed block"
            at += 1
        return result

    result = block()
    assert at == len(tokens), "unexpected closing brace"
    return result


class VM:
    def __init__(self, effects, temp=None, persistent=None, arrays=None):
        self.effects = effects
        self.temp = dict(temp or {})
        self.persistent = dict(persistent or {})
        self.arrays = copy.deepcopy(arrays or {})
        self.logs = []

    def value(self, token):
        try:
            return Decimal(token)
        except Exception:
            pass
        if token.startswith("temp_var:"):
            return self.temp.get(token[9:], Decimal(0))
        if "^" in token:
            name, index = token.split("^", 1)
            items = self.arrays.get(name, [])
            if index == "num":
                return Decimal(len(items))
            pos = int(self.value(index))
            return items[pos] if 0 <= pos < len(items) else Decimal(0)
        return self.temp.get(token, self.persistent.get(token, Decimal(0)))

    def condition(self, nodes):
        values = []
        for key, _, value in nodes:
            if key in ("AND", "limit"):
                answer = self.condition(value)
            elif key == "NOT":
                answer = not self.condition(value)
            elif key == "OR":
                answer = any(self.condition([node]) for node in value)
            elif key == "check_variable":
                assert len(value) == 1
                left, op, right = value[0]
                a, b = self.value(left), self.value(right)
                answer = {"=": a == b, "<": a < b, ">": a > b}[op]
            elif key == "has_variable":
                answer = value in self.persistent
            else:
                raise AssertionError(("unsupported condition", key))
            values.append(answer)
        return all(values)

    def run(self, name):
        assert name in self.effects, ("unknown effect", name)
        self.execute(self.effects[name])

    def execute(self, nodes):
        branch_taken = None
        for key, _, value in nodes:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    branch_taken = False
                assert branch_taken is not None
                limit = next((v for k, _, v in value if k == "limit"), [])
                take = not branch_taken and (key == "else" or self.condition(limit))
                if take:
                    self.execute([n for n in value if n[0] != "limit"])
                    branch_taken = True
                continue
            branch_taken = None
            if key in ("set_temp_variable", "add_to_temp_variable"):
                assert len(value) == 1 and value[0][1] == "="
                name, _, source = value[0]
                prior = self.temp.get(name, Decimal(0)) if key.startswith("add") else Decimal(0)
                self.temp[name] = prior + self.value(source)
            elif key == "round_temp_variable":
                self.temp[value] = self.value("temp_var:" + value).to_integral_value(rounding=ROUND_HALF_UP)
            elif key == "clear_array":
                self.arrays[value] = []
            elif key == "add_to_array":
                name, _, source = value[0]
                self.arrays.setdefault(name, []).append(self.value(source))
            elif key == "for_each_loop":
                params = {k: v for k, _, v in value if k in ("array", "value", "index")}
                body = [n for n in value if n[0] not in params]
                for i, item in enumerate(list(self.arrays.get(params["array"], []))):
                    self.temp[params["value"]] = item
                    if "index" in params:
                        self.temp[params["index"]] = Decimal(i)
                    self.execute(body)
            elif key == "log":
                self.logs.append(re.sub(r"\[\?([^]|]+)(?:\|[^]]+)?\]",
                                        lambda m: str(self.value(m[1])), value))
            elif key in self.effects and value == "yes":
                self.run(key)
            else:
                raise AssertionError(("unsupported effect", key))


def payload(prefix, count, first):
    result = {prefix + s: Decimal(0) for s in SUFFIXES}
    result.update({prefix + "ok": Decimal(1), prefix + "len": Decimal(count)})
    for i in range(count):
        result[prefix + str(i)] = Decimal(first + i if first == 1 else first - i)
    return result


def check_pair(effects, a, b, want):
    temp = {**a, **b}
    vm = VM(effects, temp, {"rn_len": Decimal(2)}, {"rn_buf": [Decimal(7), Decimal(84)]})
    before = (dict(vm.persistent), copy.deepcopy(vm.arrays))
    vm.run("rn_inline_pair_validate")
    observed = tuple(int(vm.value("temp_var:" + k)) for k in
                     ("rn_pair_err", "rn_pair_field", "rn_pair_bad"))
    assert observed == want, (observed, want)
    for key, value in temp.items():
        assert vm.temp.get(key) == value, ("command value changed", key, value, vm.temp.get(key))
    assert (vm.persistent, vm.arrays) == before, "persistent state changed"


def load_effects():
    paths = [FIXTURE / "common/scripted_effects" / name for name in
             ("rn_inline_payload.txt", "rn_inline_pair_payload.txt", "rn_prq_diagnostics.txt")]
    missing = [str(p.relative_to(REPO)) for p in paths if not p.exists()]
    assert not missing, "missing implementation: " + ", ".join(missing)
    effects = {}
    for path in paths:
        for key, op, value in parse(path.read_text(encoding="utf-8-sig")):
            assert op == "=" and isinstance(value, list) and key not in effects, key
            effects[key] = value
    return effects, paths


def pure_audit(effects, name, seen=None):
    seen = seen or set()
    if name in seen:
        return
    seen.add(name)
    allowed = {"if", "else_if", "else", "limit", "set_temp_variable",
               "add_to_temp_variable", "round_temp_variable"}

    def walk(nodes):
        for key, _, value in nodes:
            if key == "limit":
                continue
            if key in effects:
                pure_audit(effects, key, seen)
            else:
                assert key in allowed, ("persistent/unknown command in pure validator", key)
                if key in ("if", "else_if", "else"):
                    walk(value)
    walk(effects[name])


def qa_write_audit(effects, name, seen=None):
    """Only QA-owned array snapshots may be persistent writes in a button graph."""
    seen = seen or set()
    if name in seen:
        return
    seen.add(name)

    def walk(nodes):
        for key, _, value in nodes:
            if key == "limit":
                continue
            if key in effects:
                qa_write_audit(effects, key, seen)
            elif key in ("if", "else_if", "else"):
                walk(value)
            elif key == "for_each_loop":
                walk([n for n in value if n[0] not in ("array", "value", "index")])
            elif key == "clear_array":
                assert value in {f"rn_prq_bak{i}" for i in range(5)}, ("foreign array clear", value)
            elif key == "add_to_array":
                assert len(value) == 1 and value[0][0] in {f"rn_prq_bak{i}" for i in range(5)}, ("foreign array write", value)
            else:
                assert key in ("set_temp_variable", "add_to_temp_variable", "round_temp_variable", "log"), ("non-temp QA command", key)
    walk(effects[name])


def main():
    effects, paths = load_effects()
    assert paths[0].read_bytes() == (SHARED / paths[0].name).read_bytes(), "single helper drift"
    assert hashlib.sha256(paths[0].read_bytes()).hexdigest() == SINGLE_SHA, "unreviewed single helper"
    assert paths[1].read_bytes() == (SHARED / paths[1].name).read_bytes(), "pair copy drift"
    pure_audit(effects, "rn_inline_pair_validate")
    count = 0
    for acount, bcount in [(1, 32), (32, 1), (1, 1), (32, 32)]:
        check_pair(effects, payload("rn_native_", acount, 84),
                   payload("rn_nativeb_", bcount, 1), (0, 0, -1))
        count += 1
    changes = [("ok", "0", 1, -1), ("ok", "2", 1, -1),
               ("len", "0", 4, -1), ("len", "33", 4, -1),
               ("len", "1.5", 4, -1), ("len", "1.00001", 4, -1),
               ("len", "31.99999", 4, -1), ("0", "0", 5, 0),
               ("0", "85", 5, 0), ("0", "1.5", 5, 0),
               ("0", "1.00001", 5, 0), ("0", "83.99999", 5, 0),
               ("31", "0", 5, 31), ("31", "85", 5, 31)]
    for field in (1, 2):
        for suffix, value, err, bad in changes:
            a, b = payload("rn_native_", 32, 84), payload("rn_nativeb_", 32, 1)
            target, prefix = (a, "rn_native_") if field == 1 else (b, "rn_nativeb_")
            target[prefix + suffix] = Decimal(value)
            check_pair(effects, a, b, (err, field, bad))
            count += 1
        for suffix, value in [("1", "1"), ("31", "1"), ("31", "0.00001")]:
            a, b = payload("rn_native_", 1, 84), payload("rn_nativeb_", 1, 1)
            target, prefix = (a, "rn_native_") if field == 1 else (b, "rn_nativeb_")
            target[prefix + suffix] = Decimal(value)
            check_pair(effects, a, b, (6, field, int(suffix)))
            count += 1
        a, b = payload("rn_native_", 32, 84), payload("rn_nativeb_", 1, 1)
        del (a if field == 1 else b)[("rn_native_" if field == 1 else "rn_nativeb_") + "ok"]
        check_pair(effects, a, b, (1, field, -1))
        count += 1
    a, b = payload("rn_native_", 1, 84), payload("rn_nativeb_", 32, 1)
    a["rn_native_ok"] = b["rn_nativeb_ok"] = Decimal(0)
    check_pair(effects, a, b, (1, 1, -1))
    count += 1
    groups = json.loads((FIXTURE / "contract.json").read_text(encoding="utf-8"))["qa_groups"]
    fixture_cases = 0
    for group, expected_ids in groups.items():
        qa_write_audit(effects, group)
        # Mixed present/absent scalar lengths and distinct nonempty arrays catch
        # an accidental write, zeroing, truncation or stale snapshot comparison.
        persistent = {"rn_len": Decimal(3), "rn_cname_len": Decimal(2), "rn_plong_len": Decimal(0)}
        arrays = {name: [Decimal(7 + i), Decimal(84 - i)] for i, (name, _) in enumerate(BUFFERS)}
        vm = VM(effects, persistent=persistent, arrays=arrays)
        vm.run(group)
        actual_ids = []
        for line in vm.logs:
            assert " FAIL " not in line, line
            m = re.fullmatch(r"RN_PRQ case=(\d+) PASS err=\d+ field=\d+ bad=-?\d+ adiff=0 bdiff=0 pdiff=0", line)
            assert m, ("unexpected/unguarded log", line)
            actual_ids.append(int(m[1]))
        assert actual_ids == expected_ids, (group, actual_ids, expected_ids)
        assert vm.persistent == persistent, ("fixture changed persistent scalar", group)
        assert {k: v for k, v in vm.arrays.items() if not k.startswith("rn_prq_")} == arrays
        fixture_cases += len(actual_ids)
    # Prove independent command preservation catches a lost restore at slot31.
    mutated = copy.deepcopy(effects)
    found = False
    def break_restore(nodes):
        nonlocal found
        for i, (key, op, value) in enumerate(nodes):
            if key == "set_temp_variable" and value == [("rn_native_31", "=", "temp_var:rn_paira_31")]:
                nodes[i] = (key, op, [("rn_native_31", "=", "0")])
                found = True
            elif key in ("if", "else_if", "else"):
                break_restore(value)
    break_restore(mutated["rn_inline_pair_validate"])
    assert found
    try:
        check_pair(mutated, payload("rn_native_", 32, 84), payload("rn_nativeb_", 1, 1), (0, 0, -1))
    except AssertionError as exc:
        assert "command value changed" in str(exc), str(exc)
    else:
        raise AssertionError("lost-restore mutation survived")
    vm = VM(mutated)
    vm.run("rn_prq_valid")
    assert any("case=2 FAIL" in line and "adiff=1" in line for line in vm.logs), "QA failed to observe lost restore"
    sg = parse((FIXTURE / "common/scripted_guis/rn_prq_gui.txt").read_text(encoding="utf-8"))
    models = dict((k, v) for k, _, v in sg[0][2])
    assert set(models) == {"rn_prq_gui"}, "unexpected GUI model"
    model = dict((k, v) for k, _, v in models["rn_prq_gui"])
    assert model["context_type"] == "player_context" and model["ai_enabled"] == [("always", "=", "no")]
    buttons = dict((k, v) for k, _, v in model["effects"])
    triggers = dict((k, v) for k, _, v in model["triggers"])
    assert set(buttons) == {name + "_click" for name in groups}
    for selector, body in buttons.items():
        assert len(body) == 1 and body[0][0] == "if"
        limit = dict((k, v) for k, _, v in body[0][2])["limit"]
        assert limit == triggers[selector + "_enabled"], ("effect/enable guard mismatch", selector)
        assert ("tag", "=", "POL") in limit and ("is_ai", "=", "no") in limit
        for flag in ("rn_input", "rn_open"):
            assert ("NOT", "=", [("has_country_flag", "=", flag)]) in limit
        call = [n for n in body[0][2] if n[0] != "limit"]
        assert call == [(selector.removesuffix("_click"), "=", "yes")]
    contract = json.loads((FIXTURE / "contract.json").read_text(encoding="utf-8"))
    assert len(contract["inputs"]) == 68 and len(set(contract["inputs"])) == 68
    assert max(contract["key_ascii_byte_lengths"].values()) <= 15
    locs = []
    for language in ("english", "polish"):
        loc = (FIXTURE / f"localisation/{language}/rn_prq_l_{language}.yml").read_bytes()
        assert loc.startswith(b"\xef\xbb\xbf"), "missing localisation BOM"
        locs.append(set(re.findall(r"^ (RN_PRQ_\w+):", loc.decode("utf-8-sig"), re.M)))
    assert locs[0] == locs[1] and len(locs[0]) == 8
    report = {
        "scope": "Offline limited source-model and static contract checks; NOT HOI4 runtime acceptance",
        "pair_inputs": count, "qa_comparisons": fixture_cases,
        "lost_slot31_restore_mutation": "rejected by direct tests and QA FAIL/adiff=1",
        "pure_validator_persistent_writes": False,
        "qa_persistent_writes": "only5 private rn_prq_bak arrays; cleared after each comparison",
        "real_buffers_written": [], "native_transport": False,
        "epoch_or_capability_guard_tested": False, "activated": False,
        "files": {str(p.relative_to(REPO)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(FIXTURE.rglob('*')) if p.is_file() and p.name != "static-review.json" and '__pycache__' not in p.parts},
        "shared_pair_sha256": hashlib.sha256((SHARED / "rn_inline_pair_payload.txt").read_bytes()).hexdigest(),
        "findings": [],
        "runtime_pending": ["parser", "explicit temp aliases and restoration", "fractional boundaries",
                            "missing marker fresh-command semantics", "all39 conditional comparison logs", "buffer snapshots"],
    }
    (FIXTURE / "static-review.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Offline source-model PASS: {count} pair inputs, {fixture_cases} QA comparisons; lost-restore mutation rejected.")
    print("Not an HOI4 parser/runtime result; no fixture activation or game changes.")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print("FAIL:", exc, file=sys.stderr)
        sys.exit(1)
