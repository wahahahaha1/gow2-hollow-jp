"""再構築したパッケージをゲームへ置く／剥がす。

    python deploy.py               何が置かれるかだけ表示する（既定。書き込まない）
    python deploy.py --install     実際に置く
    python deploy.py --uninstall   バックアップから元に戻す

**置く直前に、置くファイル全部へ整合性検査を掛ける。1件でも不一致があれば置かない。**
ゲームは起動時に BulkDataOffsetInFile == Ar.Tell() を検査していて、合わなければ
アサーションで落ちる。検査を通っていないものをゲームフォルダへ入れないための造り。

置いたものはツール本体の隣の installed.json に記録する。--uninstall はこれを見て戻す。
"""
import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CFG          # noqa: E402
from checkbulk import check     # noqa: E402

# 導入の記録は work の下に置かない。work は README で「消して構わない」と案内して
# いる場所で、控えごと消えると導入済みだと分からなくなる。その状態で backup.py を
# 走らせると、日本語版を「無改造の控え」として採取してしまう。ツール本体の隣なら残る。
HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = os.path.join(HERE, "installed.json")


def load_marker():
    if not os.path.exists(MARKER):
        return None
    try:
        with open(MARKER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def is_installed():
    m = load_marker()
    return bool(m and m.get("files"))


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sources():
    """置く候補。(名前, 置くファイル, 置き先, 元に戻すときのファイル) の並び。"""
    if not os.path.isdir(CFG.upk_out):
        raise SystemExit(
            f"\n置くものがありません。\n  {CFG.upk_out}\n"
            "手順7（07_パッケージを作る.bat）を先に実行してください。\n")
    out = []
    for f in sorted(os.listdir(CFG.upk_out)):
        if not f.lower().endswith(".upk"):
            continue
        out.append((f[:-4],
                    os.path.join(CFG.upk_out, f),
                    os.path.join(CFG.sounds_int, f),
                    os.path.join(CFG.original, f)))
    if not out:
        raise SystemExit(
            f"\n置くものがありません。\n  {CFG.upk_out} に .upk が1本もありません。\n"
            "手順7（07_パッケージを作る.bat）を先に実行してください。\n")
    return out


def check_backup(items):
    """置き先の一本ずつに、戻すためのバックアップがあるか確かめる。"""
    missing = [name for name, _s, _d, orig in items if not os.path.exists(orig)]
    if missing:
        raise SystemExit(
            "\n[中止] 元に戻すためのバックアップがありません。\n"
            f"  {CFG.original}\n"
            f"  足りないもの: {len(missing)} 本\n"
            "手順2（02_バックアップを取る.bat）を先に実行してください。\n")


def check_not_running(items):
    """ゲームが起動しているとファイルがロックされて書き換えられない。

    エラーダイアログが出たままでも掴まれる。書き込みモードで開けるかで判定する。
    """
    for _name, _src, dst, _orig in items:
        if not os.path.exists(dst):
            continue
        try:
            with open(dst, "ab"):
                pass
        except PermissionError:
            raise SystemExit(
                "\n[中止] ゲームがファイルを掴んでいます。\n"
                f"  {dst}\n"
                "ゲームを終了してからやり直してください。\n"
                "エラーダイアログが出たままでも掴まれます。\n")
        except OSError as e:
            raise SystemExit(f"\n[中止] 置き先に書き込めません: {dst}\n  {e}\n")


def verify_sources(items):
    """置く直前の整合性検査。1件でも不一致なら置かない。"""
    print("置く前に整合性を検査します。1件でも不一致があれば中止します。\n")
    bad = 0
    for name, src, _dst, _orig in items:
        bad += len(check(src))
    print(f"\n{len(items)} 本を検査。不一致 {bad} 件。")
    if bad:
        raise SystemExit(
            "\n[中止] 不一致があります。このまま置くとゲームが起動しなくなります。\n"
            "手順7（パッケージの作成）からやり直してください。\n")
    print("問題ありません。\n")


def dryrun(items):
    print(f"置き元: {CFG.upk_out}")
    print(f"置き先: {CFG.sounds_int}")
    print(f"控え  : {CFG.original}")
    print()
    total = 0
    for name, src, dst, orig in items:
        size = os.path.getsize(src)
        total += size
        state = "新規" if not os.path.exists(dst) else "上書き"
        back = "控えあり" if os.path.exists(orig) else "★控えなし"
        print(f"  {name:<40} {size/1048576:7.1f} MB  {state}  {back}")
    print(f"\n{len(items)} 本 / 合計 {total/1048576:.1f} MB")
    if is_installed():
        m = load_marker()
        print(f"\n※ すでに導入済みの記録があります（{m.get('installed_at', '不明')}）。"
              "上書きになります。")
    print("\nここまでは何も書き込んでいません。")


def install(items):
    check_backup(items)
    check_not_running(items)
    verify_sources(items)

    files = {}
    for name, src, dst, _orig in items:
        shutil.copy2(src, dst)
        files[os.path.basename(dst)] = {"size": os.path.getsize(dst), "sha256": sha256(dst)}
        print(f"  置いた  {name}")
    with open(MARKER, "w", encoding="utf-8") as f:
        json.dump({"installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "sounds_int": CFG.sounds_int,
                   "original": CFG.original,
                   "files": files}, f, ensure_ascii=False, indent=1)
    print(f"\n{len(files)} 本を置きました。")
    print(f"記録: {MARKER}")
    print("\n元に戻すときは 99_元に戻す.bat を実行してください。")


def uninstall():
    m = load_marker()
    names = sorted(m["files"]) if m and m.get("files") else None
    if names is None:
        # 記録が無くても、控えがあるなら戻せる。手で置いた場合や記録を消した場合。
        if not os.path.isdir(CFG.original):
            raise SystemExit(
                f"\n控えが見つかりません。\n  {CFG.original}\n"
                "このツールでは戻せません。ゲームを入れ直してください。\n")
        names = sorted(f for f in os.listdir(CFG.original) if f.lower().endswith(".upk"))
        print("導入の記録がありません。控えにあるものを全部書き戻します。\n")

    items = [(n[:-4], os.path.join(CFG.original, n), os.path.join(CFG.sounds_int, n), None)
             for n in names]
    missing = [n for n, src, _d, _o in items if not os.path.exists(src)]
    if missing:
        raise SystemExit(
            f"\n[中止] 控えが足りません（{len(missing)} 本）。\n  {CFG.original}\n"
            "このまま戻すと中途半端な状態になります。\n")
    # 置き先の側のロックを見る（items の dst が置き先）。
    check_not_running([(n, s, d, s) for n, s, d, _o in items])

    done = 0
    for name, src, dst, _o in items:
        shutil.copy2(src, dst)
        done += 1
        print(f"  戻した  {name}")
    if os.path.exists(MARKER):
        os.remove(MARKER)
    print(f"\n{done} 本を元に戻しました。")
    print("音声は英語に戻ります。")


def main(argv):
    if "--uninstall" in argv:
        return uninstall()
    items = sources()
    if "--install" in argv:
        return install(items)
    return dryrun(items)


if __name__ == "__main__":
    main(sys.argv[1:])
