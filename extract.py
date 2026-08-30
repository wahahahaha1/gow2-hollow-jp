"""360版パッケージから音声（XMA）を書き出す（手順4）。

    python extract.py           まだ書き出していないものを書き出す
    python extract.py --force   書き出し済みのものもやり直す

umodel (UE Viewer) を1本ずつ呼んで、config.ini の `snd`（既定 `work\\snd_jpn`）へ
`<パッケージ名>\\SoundNodeWave\\<音声名>.xma` の形で書き出す。手順6（Ogg 変換）はここを読む。

umodel の注意が2つある。

* **引数なしで起動すると GUI が開く。** 閉じるまで戻ってこないので、
  素性の確認などで引数を省いて呼んではいけない。
* **ワイルドカードを受け付けない。** 1本ずつ回すしかない。

中断しても、次に実行すれば済んでいる分は飛ばす。
"""
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG      # noqa: E402

TIMEOUT = 600   # 1本あたり


def extracted_count(snd, base):
    d = os.path.join(snd, base, "SoundNodeWave")
    if not os.path.isdir(d):
        return 0
    return len(glob.glob(os.path.join(d, "*.xma")))


def main(argv):
    force = "--force" in argv
    exe = CFG.need_tool(CFG.umodel, "umodel")
    CFG.need_dir(CFG.jpn_only, "日本語音声パッケージのフォルダ")
    snd = CFG.ensure(CFG.snd)

    src = sorted(glob.glob(os.path.join(CFG.jpn_only, "*_LOC_jpn.xxx")))
    if not src:
        raise SystemExit(
            f"\n*_LOC_jpn.xxx が1本もありません。\n  {CFG.jpn_only}\n"
            "英語版 (*_LOC_int.xxx) ではなく日本語版を集めてください。\n")

    print(f"読み元: {CFG.jpn_only}  ({len(src)} 本)")
    print(f"書き先: {snd}\n")

    done = skip = 0
    empty = []
    fails = []
    for i, s in enumerate(src, 1):
        base = os.path.basename(s)[:-4]
        if extracted_count(snd, base) and not force:
            skip += 1
            continue
        try:
            r = subprocess.run(
                [exe, "-export", "-sounds", f"-path={CFG.jpn_only}", f"-out={snd}", base],
                capture_output=True, timeout=TIMEOUT)
        except (OSError, subprocess.SubprocessError) as e:
            fails.append((base, str(e)))
            continue
        n = extracted_count(snd, base)
        if n == 0:
            # 音声を持たないパッケージもあるので、失敗とは言い切れない。
            msg = (r.stdout + r.stderr).decode("utf-8", "replace").strip().splitlines()
            empty.append((base, msg[-1] if msg else f"終了コード {r.returncode}"))
            continue
        done += 1
        if done % 25 == 0:
            print(f"  {i}/{len(src)}  書き出し {done} / 済み {skip} / 音声なし {len(empty)}",
                  flush=True)

    dirs = [d for d in os.listdir(snd) if os.path.isdir(os.path.join(snd, d))] \
        if os.path.isdir(snd) else []
    total = sum(extracted_count(snd, d) for d in dirs)
    print(f"\n書き出し {done} / 済みで飛ばした {skip} / 音声なし {len(empty)} / 失敗 {len(fails)}")
    print(f"{snd} に {len(dirs)} パッケージ・{total:,} 音声あります。")
    if empty:
        print("\n音声が1本も取れなかったパッケージ（音声を含まないものなら正常）:")
        for name, why in empty[:10]:
            print(f"  {name}  {why}")
        if len(empty) > 10:
            print(f"  ...ほか {len(empty) - 10} 本")
    if fails:
        print("\n起動できなかったもの:")
        for name, why in fails[:10]:
            print(f"  {name}  {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
