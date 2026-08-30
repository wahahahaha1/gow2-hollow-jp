"""OpenAL の音声デバイス設定を見る・直す。

    python openal.py            今どうなっているかを見る（書き込まない）
    python openal.py --apply    DeviceName を DLL に合った値へ直す
    python openal.py --restore  直す前の状態に戻す

**この工程は多くの人には必要ない。** Hollow は出荷時、同梱の純正 OpenAL ルーターと
`DeviceName=Generic Software` の対で成立している。触る必要があるのは、
`Binaries\\OpenAL32.dll` を OpenAL Soft に差し替えた場合だけ。

OpenAL Soft 1.25.2 は `Generic Software` / `Generic Hardware` という旧来の別名を
廃止しているので、差し替えたまま出荷時の設定で起動すると `alcOpenDevice` が失敗する。
ゲーム側にフォールバックが無いため、音声デバイスごと初期化に失敗して
**効果音・BGM・セリフが全部無音になる。** 日本語化とは無関係に起きる。

書き換え先は `Engine\\Config\\BaseEngine.ini`。生成される `GearGame\\Config\\GearEngine.ini`
を直しても、UE3 が起動時に生成元のタイムスタンプと突き合わせて作り直すので消える。
直すなら生成元を直すこと。
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DLL の素性を見分けるための目印。実物から確認した文字列。
#   OpenAL Soft 1.25.2      … "OpenAL Soft" を含む
#   Hollow 同梱の純正ルーター … "Generic Software" / "Generic Hardware" / "Creative" を含む
SOFT_MARK = b"OpenAL Soft"
ROUTER_MARKS = (b"Generic Software", b"Generic Hardware")

WANT = {"soft": "OpenAL Soft", "router": "Generic Software"}

BACKUP_SUFFIX = ".gow2jp.bak"


def base_engine_ini(hollow):
    return os.path.join(hollow, "Engine", "Config", "BaseEngine.ini")


def gear_engine_ini(hollow):
    return os.path.join(hollow, "GearGame", "Config", "GearEngine.ini")


def dll_kind(path):
    """OpenAL32.dll の素性を返す。'soft' / 'router' / 'unknown' / None（無い）。"""
    if not os.path.exists(path):
        return None
    try:
        d = open(path, "rb").read()
    except OSError:
        return "unknown"
    if SOFT_MARK in d:
        return "soft"
    if any(m in d for m in ROUTER_MARKS):
        return "router"
    return "unknown"


def read_device_name(path):
    """ini から DeviceName の値と行番号を取る。(値, 行番号) or (None, None)。"""
    if not os.path.exists(path):
        return None, None
    text, _enc = _read_text(path)
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*DeviceName\s*=\s*(.*?)\s*$", line)
        if m:
            return m.group(1), i
    return None, None


def current_device_name(hollow):
    """実際に効く設定値を返す。(値, どのファイルから読んだか)。"""
    base = base_engine_ini(hollow)
    val, _ln = read_device_name(base)
    return val, base


def is_consistent(kind, name):
    """DLL の素性と DeviceName が噛み合っているか。

    空文字は「既定のデバイスを開く」でどちらでも通るので、噛み合っている扱いにする。
    """
    if name is None:
        return False
    if name == "":
        return True
    if kind == "soft":
        # OpenAL Soft は旧来の別名を受け付けない。
        return name not in ("Generic Software", "Generic Hardware")
    if kind == "router":
        # 純正ルーターは "OpenAL Soft" という名前のデバイスを知らない。
        return name != "OpenAL Soft"
    return True


def _read_text(path):
    """ini をバイトのまま読んで、書き戻せる文字コードとともに返す。

    他人の環境では UTF-8 とは限らない。`errors="replace"` で読んで書き戻すと、
    読めなかったバイトが別の文字に化けて、触っていない行まで壊してしまう。
    latin-1 はどんなバイト列でも往復できるので、UTF-8 で読めないときの受け皿にする。
    改行変換も掛けない（CRLF の ini を LF に変えてしまわないため）。
    """
    raw = open(path, "rb").read()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"


def _set_device_name(path, value):
    """DeviceName の行だけを書き換える。他の行には触らない。"""
    text, enc = _read_text(path)
    # 読むのは最初の1行だけ（read_device_name）なので、書くのも1行だけにする。
    new, n = re.subn(r"(?m)^(\s*DeviceName\s*=).*$",
                     lambda m: m.group(1) + value, text, count=1)
    if n == 0:
        raise SystemExit(f"DeviceName の行が {path} に見つかりません。書き換えを中止しました。")
    open(path, "wb").write(new.encode(enc))
    return n


def show(hollow):
    base = base_engine_ini(hollow)
    dll = os.path.join(hollow, "Binaries", "OpenAL32.dll")
    kind = dll_kind(dll)
    name, _ln = read_device_name(base)
    label = {"soft": "OpenAL Soft（差し替えられている）",
             "router": "純正ルーター（出荷時のまま）",
             "unknown": "判別できない",
             None: "ファイルが無い"}[kind]
    shown = f'"{name}"' if name else ("（空＝既定のデバイス）" if name == "" else "（記述なし）")
    print(f"OpenAL32.dll : {label}")
    print(f"  {dll}")
    print(f"DeviceName   : {shown}")
    print(f"  {base}")
    gear = gear_engine_ini(hollow)
    gname, _gl = read_device_name(gear)
    if gname is not None:
        print(f"（参考）生成された GearEngine.ini の DeviceName: \"{gname}\"")
        print("  こちらを直しても起動時に作り直されて消える。直すのは上の BaseEngine.ini。")
    print()
    if kind in ("soft", "router"):
        if is_consistent(kind, name):
            print("噛み合っています。この工程は必要ありません。")
            return 0
        print("★ 噛み合っていません。このままだとゲームの音が全部鳴りません。")
        print(f"   正しい値: DeviceName={WANT[kind]}")
        print("   直すには --apply を付けて実行してください。")
        return 1
    print("素性が判別できないので、自動では直せません。")
    return 1


def apply(hollow):
    base = base_engine_ini(hollow)
    dll = os.path.join(hollow, "Binaries", "OpenAL32.dll")
    kind = dll_kind(dll)
    if kind not in ("soft", "router"):
        raise SystemExit("OpenAL32.dll の素性が判別できないので、書き換えは行いません。")
    name, _ln = read_device_name(base)
    want = WANT[kind]
    if name == want:
        print(f"すでに DeviceName={want} です。何もしませんでした。")
        return 0
    backup = base + BACKUP_SUFFIX
    if not os.path.exists(backup):
        shutil.copy2(base, backup)
        print(f"元のファイルを控えました: {backup}")
    _set_device_name(base, want)
    print(f"DeviceName を {want} にしました。")
    print(f"  {base}")
    print("\nこの設定は次回以降読まれます。")
    print("生成された GearGame\\Config\\GearEngine.ini は起動時に作り直されるので、触らなくて構いません。")
    return 0


def restore(hollow):
    base = base_engine_ini(hollow)
    backup = base + BACKUP_SUFFIX
    if not os.path.exists(backup):
        print("控えがありません。このツールでは書き換えていないので、戻すものもありません。")
        return 0
    shutil.copy2(backup, base)
    os.remove(backup)
    name, _ln = read_device_name(base)
    print(f"元に戻しました。DeviceName=\"{name}\"")
    print(f"  {base}")
    return 0


def main(argv):
    from config import CFG
    hollow = CFG.need_dir(CFG.hollow, "Hollow のインストール先")
    if "--apply" in argv:
        return apply(hollow)
    if "--restore" in argv:
        return restore(hollow)
    return show(hollow)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
