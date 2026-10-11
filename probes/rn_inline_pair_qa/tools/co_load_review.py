"""Read-only inventories of the three explicit QA packages; writes only own report."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from check import FIXTURE, REPO, load_effects, parse, qa_write_audit

PACKAGES = {"mod": REPO / "mod", "transport_qa": REPO / "probes/rn_inline_leader_transport_qa",
            "pair_qa": FIXTURE}


def children(nodes, key):
    return [value for name, _, value in nodes if name == key]


def inventory(root):
    symbols = {key: {} for key in ("effects", "scripted_triggers", "scripted_localisation", "sg_models",
                                  "sg_callbacks", "gui_roots", "gui_controls", "sprites", "localisation")}
    hashes = {}

    def add(category, symbol, path):
        symbols[category].setdefault(symbol, []).append(path)

    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.parts[-2] == "tools":
            continue
        rel = path.relative_to(root).as_posix()
        if not rel.startswith(("common/", "interface/", "localisation/")):
            continue
        hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        source = path.read_text(encoding="utf-8-sig")
        if rel.startswith("localisation/"):
            language = re.search(r"^l_(\w+):", source, re.M)[1]
            for name in re.findall(r"^\s+([A-Za-z_][\w.-]*):", source, re.M):
                add("localisation", language + ":" + name, rel)
            continue
        nodes = parse(source)
        if rel.startswith("common/scripted_effects/"):
            for name, _, _ in nodes:
                add("effects", name, rel)
        elif rel.startswith("common/scripted_triggers/"):
            for name, _, _ in nodes:
                add("scripted_triggers", name, rel)
        elif rel.startswith("common/scripted_localisation/"):
            for _, _, body in nodes:
                for name in children(body, "name"):
                    add("scripted_localisation", name, rel)
        elif rel.startswith("common/scripted_guis/"):
            for _, _, models in nodes:
                for name, _, body in models:
                    add("sg_models", name, rel)
                    for callbacks in children(body, "effects") + children(body, "triggers"):
                        for selector, _, _ in callbacks:
                            # Callback keys are local to their SG model. Main mod
                            # intentionally reuses close selectors across models.
                            add("sg_callbacks", name + "::" + selector, rel)
        elif rel.startswith("interface/"):
            def widgets(items, parent=""):
                for kind, _, body in items:
                    if not isinstance(body, list):
                        continue
                    names = children(body, "name")
                    current = parent
                    if names:
                        current = parent + "/" + names[0] if parent else names[0]
                        category = "sprites" if kind == "spriteType" else "gui_controls" if parent else "gui_roots"
                        add(category, current, rel + "#" + kind)
                    widgets([n for n in body if isinstance(n[2], list)], current)
            for _, _, body in nodes:
                widgets(body)
    return {"symbols": symbols, "files_sha256": hashes,
            "counts": {category: len(names) for category, names in symbols.items()}}


def persistent_writes(nodes):
    targets = set()
    for key, _, value in nodes:
        if key in ("set_variable", "add_to_variable", "subtract_from_variable", "multiply_variable",
                   "divide_variable", "add_to_array", "remove_from_array"):
            targets.add(value[0][0])
        elif key in ("clear_variable", "clear_array", "set_country_flag", "clr_country_flag"):
            targets.add(value)
        elif isinstance(value, list):
            targets |= persistent_writes(value)
    return targets


def main():
    data = {name: inventory(root) for name, root in PACKAGES.items()}
    collisions = []
    package_names = list(PACKAGES)
    for i, left in enumerate(package_names):
        for right in package_names[i + 1:]:
            for category in data[left]["symbols"]:
                names = sorted(set(data[left]["symbols"][category]) & set(data[right]["symbols"][category]))
                if names:
                    collisions.append({"packages": [left, right], "category": category, "names": names})
            paths = sorted(set(data[left]["files_sha256"]) & set(data[right]["files_sha256"]))
            if paths:
                collisions.append({"packages": [left, right], "category": "virtual_file_path", "names": paths})
    assert not collisions, collisions
    for name, package in data.items():
        for category, names in package["symbols"].items():
            assert not {symbol: places for symbol, places in names.items() if len(places) > 1}, (name, category, "duplicate symbol")
    effects, _ = load_effects()
    groups = json.loads((FIXTURE / "contract.json").read_text(encoding="utf-8"))["qa_groups"]
    for group in groups:
        qa_write_audit(effects, group)
    transport_writes = set()
    transport_nodes = []
    for path in (PACKAGES["transport_qa"] / "common").rglob('*.txt'):
        nodes = parse(path.read_text(encoding="utf-8-sig"))
        transport_nodes.extend(nodes)
        transport_writes |= persistent_writes(nodes)
    main_writes = set()
    for path in (PACKAGES["mod"] / "common").rglob('*.txt'):
        main_writes |= persistent_writes(parse(path.read_text(encoding="utf-8-sig")))
    pair_reachable_writes = {f"rn_prq_bak{i}" for i in range(5)}
    assert not pair_reachable_writes & (transport_writes | main_writes)
    assert not any(name.startswith(("rn_native", "rn_pair", "rn_prq")) for name in transport_writes)
    assert "rn_inline_payload.txt" not in {Path(p).name for p in data["transport_qa"]["files_sha256"]}
    apply = next(v for k, _, v in transport_nodes if k == "rn_inline_leader_apply")
    assert {key for key, _, _ in apply} <= {"if", "else"}
    branch = children(apply, "if")[0]
    assert {key for key, _, _ in branch} <= {"limit", "log"}, "transport Apply mutated state"
    assert {key for key, _, _ in children(apply, "else")[0]} == {"log"}
    native_path = REPO / "plugin/probes/inline_leader_bridge.cpp"
    native = native_path.read_text(encoding="utf-8")
    assert "rn_prq_" not in native, "pair unexpectedly present in native bridge"
    assert 'return name_equals(model_name,"rn_ip_leader_gui") && name_equals(selector,"rn_ip_leader_apply_click");' in native
    report = {
        "scope": "Exact source inventories and reachable pair-button write audit; no activation/runtime proof",
        "packages": data, "cross_package_collisions": collisions,
        "transport_all_declared_persistent_write_targets": sorted(transport_writes),
        "pair_button_reachable_persistent_writes": sorted(pair_reachable_writes),
        "shared_write_targets": [], "transport_apply_effect": "if/limit/log + else/log only",
        "pair_buttons_model": "rn_prq_gui; synthetic temp values only in their own SG command",
        "native_bridge_pair_whitelist": False,
        "native_source_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
        "allowed_exact_combination": ["mod/", "probes/rn_inline_leader_transport_qa/", "probes/rn_inline_pair_qa/"],
        "limitations": ["Root review before freshprocess activation", "No leader rename Apply", "Pair does not inject records into editor model",
                        "Native transport and pure pair semantics must be observed separately", "Fresh command temp lifetime remains runtime requirement"],
        "findings": [],
    }
    target = FIXTURE / "co-load-review.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, package in data.items():
        print(name, package["counts"])
    print("No symbol/path collision or shared reachable persistent writes; exact transport+pair QA co-load source review PASS.")


if __name__ == "__main__":
    main()
