"""GoW2 日本語音声移植ツール — 入口。

    gow2jp <サブコマンド> [引数...]

番号付きのバッチファイルはここを呼んでいる。引数なしで実行すると一覧が出る。
入出力の場所は config.ini に集約してあるので、どのサブコマンドも引数を省ける。
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 日本語の出力が cp932 で化けないようにする。
# 各スクリプトも config.py 経由で同じことをするが、ここでも先に直しておく。
for _st in (sys.stdout, sys.stderr):
    try:
        if _st is not None and getattr(_st, "encoding", "").lower() not in ("utf-8", "utf8"):
            _st.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

# サブコマンド -> (手順番号, 実行するスクリプト, 説明)
STEPS = [
    ("doctor",     "0", "doctor.py",     "環境が揃っているか確認する（最初に実行する）"),
    ("backup",     "2", "backup.py",     "無改造の音声パッケージを控える"),
    ("decompress", "3", "decompress.py", "360パッケージの圧縮を展開する"),
    ("extract",    "4", "extract.py",    "360パッケージから音声(XMA)を書き出す"),
    ("plan",       "5", "plan.py",       "360側とPC側の対応表を作る"),
    ("convert",    "6", "convert.py",    "XMA を Ogg Vorbis にする"),
    ("inject",     "7", "inject.py",     "パッケージを組み立てる（ゲームには書き込まない）"),
    ("verify",     "8", "checkbulk.py",  "組み立てたものを検査する（省略不可）"),
    ("deploy",     "9", "deploy.py",     "ゲームに置く／剥がす（--install / --uninstall）"),
    ("openal",     "",  "openal.py",     "音が出ないときの音声デバイス設定（--apply / --restore）"),
    ("config",     "",  "config.py",     "読み込んだ設定を表示する"),
    ("bik",        "",  "bik.py",        "カットシーンの組み替え（付録・現状では効果なし）"),
]
TABLE = {name: (step, tool, desc) for name, step, tool, desc in STEPS}


def usage():
    print(__doc__.strip())
    print("\nサブコマンド:\n")
    print("  手順の番号は README.md の手順番号。\n")
    print("  手順  名前          内容")
    print("  ----  ------------  " + "-" * 46)
    for name, step, _tool, desc in STEPS:
        print(f"  {step:>4}  {name:<12}  {desc}")
    print("\n手順1（ISO を展開して日本語パッケージを集める）は利用者の作業なので、ここには無い。")
    print("詳しくは README.md を読むこと。")
    ini = os.path.join(HERE, "config.ini")
    print(f"\n設定: {ini}" + ("" if os.path.exists(ini) else "  ← まだ無い"))


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        usage()
        return 0
    name = argv[0]
    if name not in TABLE:
        print(f"知らないサブコマンドです: {name}\n")
        usage()
        return 2
    _step, tool, _desc = TABLE[name]
    path = os.path.join(HERE, tool)
    sys.argv = [path] + argv[1:]
    print(f"$ {tool} " + " ".join(argv[1:]), flush=True)
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit as e:
        # SystemExit には理由が載っていることがある（設定の不備など）。
        # ここで出さないと、利用者の画面には何も表示されないまま終わる。
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        print(e.code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
