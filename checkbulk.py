"""Simulate the engine's check: BulkDataOffsetInFile must equal the archive
position immediately after the 16-byte bulk header."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ue3 import Package, Ar, walk_props

def check(path, limit=6):
    pk = Package(path); bad = []; total = 0
    for e in pk.exports:
        if pk.classname(e) != 'SoundNodeWave': continue
        end, props, _ = walk_props(pk, e)
        a = Ar(pk.d, pk.be, e['off'] + end)
        for i in range(4):
            fl = a.u32(); c = a.i32(); sz = a.i32(); off = a.i32()
            total += 1
            if off != a.p:
                bad.append((e['name'], i, off, a.p, off - a.p, sz))
            a.p += sz
    print(f"{os.path.basename(path)}: blocks={total}  mismatches={len(bad)}")
    for b in bad[:limit]:
        print(f"    {b[0][:38]:<40} slot{b[1]} stated={b[2]:>10,} actual={b[3]:>10,} diff={b[4]:>+8,} size={b[5]:,}")
    return bad

if __name__ == '__main__':
    import glob
    from config import CFG
    # 引数を省くと config.ini の upk 出力先を全部検査する
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(CFG.upk_out, "*.upk")))
    if not targets:
        raise SystemExit(f"検査対象がありません。\n  {CFG.upk_out}\n手順7（07_パッケージを作る.bat）を先に実行してください。")
    total_bad = 0
    for p in targets:
        total_bad += len(check(p))
        print()
    print(f"{len(targets)} 本を検査。不一致 {total_bad} 件。"
          + ("  導入して問題ありません。" if total_bad == 0 else "  ★導入しないでください。"))
