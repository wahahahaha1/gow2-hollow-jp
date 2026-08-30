"""無改造の音声パッケージを控えておく（手順2）。

    python backup.py           控えを取る
    python backup.py --check   何をするかだけ表示する（書き込まない）

ゲームの `GearGame\\Content\\Sounds\\INT` にある .upk を、config.ini の `original`
（既定 `work\\original_Sounds_INT`）へ複製する。**ここが inject.py の入力**になり、
99_元に戻す.bat の戻し元にもなる。これが無いと元に戻せない。

すでに控えてあるファイルは**絶対に上書きしない。** 一度日本語化したあとに
もう一度これを実行しても、日本語版で控えを潰してしまうことがないようにするため。
"""
import glob
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG      # noqa: E402
import deploy               # noqa: E402

PC_UPK = 45     # Hollow の Sounds\INT にある .upk の本数


def main(argv):
    dry = "--check" in argv
    CFG.need_dir(CFG.sounds_int, "Hollow の Sounds\\INT")

    if deploy.is_installed():
        raise SystemExit(
            "\n[中止] すでに日本語化を導入した記録があります。\n"
            f"  {deploy.MARKER}\n"
            "今の Sounds\\INT は日本語版なので、ここで控えを取ると\n"
            "「無改造の控え」ではなくなってしまいます。\n"
            "取り直したいときは、先に 99_元に戻す.bat で戻してください。\n")

    src = sorted(glob.glob(os.path.join(CFG.sounds_int, "*.upk")))
    if not src:
        raise SystemExit(f"\n.upk が1本もありません。\n  {CFG.sounds_int}\n")
    if len(src) != PC_UPK:
        print(f"※ {len(src)} 本あります（{PC_UPK} 本のはず）。版が違うかもしれません。\n")

    print(f"控え元: {CFG.sounds_int}")
    print(f"控え先: {CFG.original}")
    print()

    copy, skip = [], []
    for s in src:
        d = os.path.join(CFG.original, os.path.basename(s))
        (skip if os.path.exists(d) else copy).append((s, d))

    if skip:
        print(f"すでに控えてあるもの: {len(skip)} 本（触りません）")
    if not copy:
        print("新しく控えるものはありません。")
        print(f"\n控えは {len(skip)} 本そろっています。")
        return 0

    total = sum(os.path.getsize(s) for s, _d in copy)
    print(f"新しく控えるもの    : {len(copy)} 本 / {total/1048576:.1f} MB")
    if dry:
        print("\n--check なので何も書き込んでいません。")
        return 0

    CFG.ensure(CFG.original)
    free = shutil.disk_usage(CFG.original).free
    if free < total * 1.05:
        raise SystemExit(
            f"\n[中止] 空き容量が足りません。\n"
            f"  必要 {total/1048576:.1f} MB / 空き {free/1048576:.1f} MB\n"
            f"  {CFG.original}\n")

    print()
    for i, (s, d) in enumerate(copy, 1):
        shutil.copy2(s, d)
        print(f"  [{i:>2}/{len(copy)}] {os.path.basename(s)}")

    have = len(glob.glob(os.path.join(CFG.original, "*.upk")))
    print(f"\n控えました。合計 {have} 本。")
    if have != len(src):
        print(f"※ 控え {have} 本と元 {len(src)} 本の数が合っていません。確認してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
