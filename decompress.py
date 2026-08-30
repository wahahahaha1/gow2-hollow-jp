"""360版パッケージの圧縮を展開する（手順3）。

    python decompress.py           まだ展開していないものを展開する
    python decompress.py --force   展開済みのものもやり直す

360版のパッケージは LZX で丸ごと圧縮されていて、そのままでは中身を読めない。
gildor 氏の decompress.exe を1本ずつ呼んで、config.ini の `dec`
（既定 `work\\dec_jpn`）へ展開する。手順5（対応表）はここを読む。

**暗号は関わらない。** LZX 圧縮を解くだけで、復号処理は一切していない。
中断しても、次に実行すれば済んでいる分は飛ばす。
"""
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG      # noqa: E402

TIMEOUT = 300   # 1本あたり。大きいパッケージでも数秒で終わる


def main(argv):
    force = "--force" in argv
    exe = CFG.need_tool(CFG.decompress, "decompress.exe")
    CFG.need_dir(CFG.jpn_only, "日本語音声パッケージのフォルダ")
    out = CFG.ensure(CFG.dec)

    src = sorted(glob.glob(os.path.join(CFG.jpn_only, "*.xxx")))
    if not src:
        raise SystemExit(
            f"\n*.xxx が1本もありません。\n  {CFG.jpn_only}\n"
            "展開した ISO の GearGame\\CookedXenon から *_LOC_jpn.xxx を集めて、\n"
            "その場所を config.ini の [paths] jpn_only に書いてください。\n")

    print(f"展開元: {CFG.jpn_only}  ({len(src)} 本)")
    print(f"展開先: {out}\n")

    done = skip = 0
    fails = []
    for i, s in enumerate(src, 1):
        name = os.path.basename(s)
        dst = os.path.join(out, name)
        if os.path.exists(dst) and not force:
            skip += 1
            continue
        try:
            r = subprocess.run([exe, f"-out={out}", s], capture_output=True, timeout=TIMEOUT)
        except (OSError, subprocess.SubprocessError) as e:
            fails.append((name, str(e)))
            continue
        if not os.path.exists(dst):
            msg = (r.stdout + r.stderr).decode("utf-8", "replace").strip().splitlines()
            fails.append((name, msg[-1] if msg else f"終了コード {r.returncode}"))
            continue
        done += 1
        if done % 50 == 0:
            print(f"  {i}/{len(src)}  展開 {done} / 済み {skip} / 失敗 {len(fails)}", flush=True)

    print(f"\n展開 {done} / 済みで飛ばした {skip} / 失敗 {len(fails)}")
    have = len(glob.glob(os.path.join(out, "*.xxx")))
    print(f"{out} に {have} 本あります。")
    if fails:
        print("\n失敗したもの:")
        for name, why in fails[:15]:
            print(f"  {name}  {why}")
        if len(fails) > 15:
            print(f"  ...ほか {len(fails) - 15} 本")
        print("\n失敗したぶんの音声は英語のまま残ります。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
