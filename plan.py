"""Build the full 360->PC mapping keyed on the object path recorded inside each
cooked 360 package: <PCPackage>.<Group>.<WaveName>."""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue3 import Package, waves
from config import CFG

# 引数を省くと config.ini の設定を使う
DEC   = sys.argv[1] if len(sys.argv) > 1 else CFG.dec
PCDIR = sys.argv[2] if len(sys.argv) > 2 else CFG.sounds_int
OUT   = sys.argv[3] if len(sys.argv) > 3 else CFG.plan

CFG.need_dir(DEC, "展開した360パッケージのフォルダ（手順3「360パッケージを展開する」を先に実行してください）")
CFG.need_dir(PCDIR, "Hollow の Sounds\\INT")
CFG.ensure(os.path.dirname(OUT) or ".")

pc_keys = {}
pc_names = {}
for f in sorted(os.listdir(PCDIR)):
    if not f.lower().endswith('.upk'): continue
    pk = Package(os.path.join(PCDIR, f)); base = f[:-4]
    d = {}
    for w in waves(pk):
        d.setdefault(pk.path_of(w['exp']).lower(), []).append(w['exp']['idx'])
    pc_keys[base.lower()] = d
    pc_names[base.lower()] = base
print(f"PC packages: {len(pc_keys)}  total keys: {sum(len(v) for v in pc_keys.values())}")

plan = collections.defaultdict(dict)   # pcpkg -> key -> (jpfile, wavename)
unmatched = collections.Counter(); conflicts = 0; total = 0
for f in sorted(os.listdir(DEC)):
    if not f.lower().endswith('.xxx'): continue
    jp = Package(os.path.join(DEC, f))
    for w in waves(jp):
        p = jp.path_of(w['exp']); parts = p.split('.')
        if len(parts) < 3: unmatched['no_group'] += 1; continue
        target, key = parts[0].lower(), '.'.join(parts[1:]).lower()
        total += 1
        if target not in pc_keys: unmatched[f'no_pkg:{target}'] += 1; continue
        if key not in pc_keys[target]: unmatched['no_key'] += 1; continue
        if key in plan[target]: conflicts += 1; continue
        plan[target][key] = (f, w['name'])

print(f"\n360 waves total: {total:,}")
print(f"matched: {sum(len(v) for v in plan.values()):,}   duplicate-source skipped: {conflicts:,}")
print(f"unmatched: {sum(unmatched.values())}")
for k, v in unmatched.most_common(8): print(f"   {k}: {v}")
print(f"\n=== per PC package ===")
for base in sorted(pc_keys):
    n = len(plan.get(base, {})); tot = len(pc_keys[base])
    print(f"  {pc_names[base]:<32} {n:>5} / {tot:>5}  ({100*n/tot if tot else 0:5.1f}%)")
json.dump({pc_names[k]: {kk: list(vv) for kk, vv in v.items()} for k, v in plan.items()},
          open(OUT, 'w'), indent=0)
print(f"\nplan written to {OUT}")
