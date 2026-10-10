#!/usr/bin/env python3
"""Rename Anything - static cross-reference checks (run after tools/gen.py).

Checks: loc keys used by the .gui exist (english), sprites exist (mod or vanilla), scripted loc
references are defined, scripted-loc localization keys exist, scripted effects are defined,
every button has a _click effect and vice versa, GUI targets, brace balance,
loc file format (BOM, header), equal locale key sets and language-independent character tables.
This is a static check, not a substitute for the game parser or multiplayer testing.
Exit code 1 on any finding.
"""
import glob
import os
import re
import sys

G = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mod")
os.chdir(MOD)
bad = []
rd = lambda f: open(f, encoding="utf-8").read()
if not os.path.isdir(os.path.join(G, "history", "states")):
    sys.exit(f"game directory is missing history/states: {G}")
gui = rd("interface/rename_anything.gui")
loc = {}
for f in glob.glob("localisation/english/*.yml"):
    for l in open(f, encoding="utf-8-sig"):
        m = re.match(r' (\S+?):\d? "(.*)"\s*$', l)
        if m:
            loc[m.group(1)] = m.group(2)
locale_tables = {}
char_tables = {}
for f in sorted(glob.glob("localisation/*/*.yml")):
    lang = os.path.basename(os.path.dirname(f))
    table = locale_tables.setdefault(lang, {})
    chars = char_tables.setdefault(lang, {})
    for line in open(f, encoding="utf-8-sig"):
        m = re.match(r' (\S+?):\d? "(.*)"\s*$', line)
        if m:
            key, value = m.groups()
            if key in table:
                bad.append(f"duplicate loc key {lang}: {key}")
            table[key] = value
            if "_chars_l_" in os.path.basename(f):
                chars[key] = value
for lang, table in sorted(locale_tables.items()):
    bad += [f"missing loc key {lang}: {k}" for k in sorted(loc.keys() - table.keys())]
    bad += [f"unexpected loc key {lang}: {k}" for k in sorted(table.keys() - loc.keys())]
    reference = char_tables.get("english", {})
    bad += [f"language-dependent character table {lang}: {k}"
            for k in sorted(reference.keys() | char_tables[lang].keys())
            if reference.get(k) != char_tables[lang].get(k)]
keys = set(re.findall(r'(?:buttonText|text|pdx_tooltip)\s*=\s*"([^"]+)"', gui))
bad += [f"missing loc key {k}" for k in sorted(keys) if not k.startswith("[") and k not in loc]
sprites = set(re.findall(r'(?:spriteType|quadTextureSprite)\s*=\s*"([^"]+)"', gui))
gfx = rd("interface/rename_anything.gfx")
van = "".join(open(f, encoding="utf-8", errors="replace").read() for f in glob.glob(os.path.join(G, "interface", "*.gfx")))
bad += [f"missing sprite {s}" for s in sorted(sprites) if f'"{s}"' not in gfx and f'"{s}"' not in van]
for tex in re.findall(r'texturefile = "([^"]+)"', gfx):
    if not os.path.exists(tex):
        bad.append(f"missing texture {tex}")
sl = rd("common/scripted_localisation/rename_anything_scripted_loc.txt")
defs = set(re.findall(r"name = (\S+)", sl))
eff = rd("common/scripted_effects/rename_anything_generated_effects.txt")
refs = set()
for v in [v for table in locale_tables.values() for v in table.values()] + [gui, eff]:
    refs |= set(re.findall(r"\[ROOT\.(RN_\w+)\]", v))
bad += [f"undefined scripted loc {r}" for r in sorted(refs - defs)]
vk = set()
for f in glob.glob(os.path.join(G, "localisation", "english", "*.yml")):
    for l in open(f, encoding="utf-8-sig", errors="replace"):
        m = re.match(r"\s*(VICTORY_POINTS_\d+):", l)
        if m:
            vk.add(m.group(1))
bad += [f"missing loc for scripted loc key {k}" for k in sorted(set(re.findall(r"localization_key = (\S+)", sl))) if k not in loc and k not in vk]
allfx = rd("common/scripted_effects/rename_anything_effects.txt") + eff
trig = rd("common/scripted_triggers/rename_anything_triggers.txt")
fxdefs = set(re.findall(r"^(rn_\w+) = \{", allfx + trig, re.M))
sg = rd("common/scripted_guis/rename_anything_scripted_gui.txt")
used = set(re.findall(r"\b(rn_\w+) = yes", sg + allfx + sl))
bad += [f"undefined effect/trigger {u}" for u in sorted(used - fxdefs)]
btns = set(re.findall(r'buttonType = \{\s*name = "([^"]+)"', gui))
clicks = set(re.findall(r"(\w+)_click = \{", sg))
bad += [f"button without effect {b}" for b in sorted(btns - clicks)]
bad += [f"effect without button {c}" for c in sorted(clicks - btns)]
names = set(re.findall(r'name = "([^"]+)"', gui))
bad += [f"trigger for unknown element {v}" for v in sorted(set(re.findall(r"(\w+)_visible = \{", sg)) - names)]
bad += [f"enabled trigger for unknown button {v}"
        for v in sorted(set(re.findall(r"(\w+)_click_enabled = \{", sg)) - btns)]
bad += [f"scripted GUI for unknown window {v}"
        for v in sorted(set(re.findall(r'window_name = "([^"]+)"', sg)) - names)]
for f in glob.glob("common/**/*.txt", recursive=True) + glob.glob("interface/*.gui") + glob.glob("interface/*.gfx"):
    t = re.sub(r"#[^\n]*", "", re.sub(r'"[^"\n]*"', '""', rd(f)))
    d = 0
    for ch in t:
        d += (ch == "{") - (ch == "}")
        if d < 0:
            break
    if d:
        bad.append(f"brace imbalance {f}")
for f in glob.glob("localisation/*/*.yml"):
    b = open(f, "rb").read()
    lang = f.replace("\\", "/").split("_l_")[-1][:-4]
    if b[:3] != b"\xef\xbb\xbf":
        bad.append(f"no BOM {f}")
    lines = b[3:].decode("utf-8").split("\n")
    if lines[0] != f"l_{lang}:":
        bad.append(f"bad header {f}")
    for l in lines[1:]:
        if l.strip() and not l.strip().startswith("#") and not re.match(r'^ [A-Za-z0-9_.]+:\d? ".*"$', l):
            bad.append(f"bad loc line {f}: {l[:60]}")
for b_ in bad:
    print(b_)
print(f"{len(bad)} findings")
sys.exit(1 if bad else 0)
