"""作業を始める前に、環境が揃っているかをまとめて確認する。

    python doctor.py

手順の途中で止まる原因を先に潰すためのもの。展開と変換に1〜2時間かかるので、
走り出す前にここで引っかかりを見つける。**ゲームフォルダには一切書き込まない。読むだけ。**
"""
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 日本語の出力が cp932 で化けないようにする。config.py も同じことをするが、
# doctor は「設定が読めない」場合でも動く必要があり、config を読み込む前から
# 印字するので、ここで先に直しておく。
for _st in (sys.stdout, sys.stderr):
    try:
        if _st is not None and getattr(_st, "encoding", "").lower() not in ("utf-8", "utf8"):
            _st.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

NEED_GB = 3     # 展開・XMA・Ogg・再構築した .upk・バックアップの合計に余裕を見た値
PC_UPK = 45     # Hollow の Sounds\INT にある .upk の本数
JPN_XXX = 391   # ISO から集める *_LOC_jpn.xxx の本数

results = []


def rec(level, name, detail):
    results.append((level, name, detail))
    mark = {"OK": " OK ", "WARN": "注意", "NG": " NG "}[level]
    print(f"[{mark}] {name}\n         {detail}")


def check_python():
    v = sys.version_info
    s = f"{v.major}.{v.minor}.{v.micro} ({sys.executable})"
    if v < (3, 10):
        rec("NG", "Python", f"3.10 以上が必要です。今は {s}")
    else:
        rec("OK", "Python", s)


def check_modules():
    try:
        import ue3  # noqa: F401
        rec("OK", "ツール本体", "読み込めました")
    except Exception as e:
        rec("NG", "ツール本体", f"{type(e).__name__}: {e}")


def load_config():
    """config.ini を読む。不備があれば理由をそのまま出して None を返す。

    config.py は読み込んだ時点で設定を検査して SystemExit を投げる作りなので、
    ここで捕まえないと doctor 自身が落ちて何も表示できなくなる。
    """
    try:
        import config
        rec("OK", "設定ファイル", config.INI)
        return config.CFG
    except SystemExit as e:
        rec("NG", "設定ファイル", str(e).strip().replace("\n", "\n         "))
        return None
    except Exception as e:
        rec("NG", "設定ファイル", f"{type(e).__name__}: {e}")
        return None


def check_hollow(cfg):
    if not os.path.isdir(cfg.hollow):
        rec("NG", "Hollow のインストール先",
            f"見つかりません: {cfg.hollow}\n"
            f"         config.ini の [paths] hollow を確認してください")
        return False
    if not os.path.isdir(os.path.join(cfg.hollow, "GearGame")):
        rec("NG", "Hollow のインストール先",
            f"GearGame フォルダがありません。ゲームのフォルダに見えません: {cfg.hollow}")
        return False
    rec("OK", "Hollow のインストール先", cfg.hollow)

    n = len(glob.glob(os.path.join(cfg.sounds_int, "*.upk")))
    if n == 0:
        rec("NG", "差し替え先の音声パッケージ", f"{cfg.sounds_int} に .upk がありません")
    elif n != PC_UPK:
        rec("WARN", "差し替え先の音声パッケージ",
            f"{n} 本（{PC_UPK} 本のはず）。版が違うかもしれません\n"
            f"         {cfg.sounds_int}")
    else:
        rec("OK", "差し替え先の音声パッケージ", f"{n} 本 ({cfg.sounds_int})")
    return True


def check_backup(cfg):
    """手順2（バックアップ）が済んでいるか。inject.py はここを入力にする。"""
    n = len(glob.glob(os.path.join(cfg.original, "*.upk"))) if os.path.isdir(cfg.original) else 0
    if n == 0:
        rec("WARN", "無改造のバックアップ",
            f"まだありません。手順2（02_バックアップを取る.bat）で作られます\n"
            f"         置き場所: {cfg.original}")
    elif n != PC_UPK:
        rec("WARN", "無改造のバックアップ",
            f"{n} 本しかありません（{PC_UPK} 本のはず）: {cfg.original}\n"
            f"         手順2 をもう一度実行してください")
    else:
        rec("OK", "無改造のバックアップ", f"{n} 本 ({cfg.original})")


def check_installed(cfg):
    """すでに日本語化を置いてあるか。入れ直しのときに効く。"""
    import deploy
    m = deploy.load_marker()
    if not (m and m.get("files")):
        return
    rec("WARN", "導入済みの記録",
        f"{len(m['files'])} 本が {m.get('installed_at', '日時不明')} に置かれています。\n"
        f"         入れ直すなら 99_元に戻す.bat で先に戻してください")


def check_jpn(cfg):
    if not os.path.isdir(cfg.jpn_only):
        rec("NG", "日本語音声パッケージ",
            f"見つかりません: {cfg.jpn_only}\n"
            f"         展開した ISO の GearGame\\CookedXenon から *_LOC_jpn.xxx を集めて、\n"
            f"         その場所を config.ini の [paths] jpn_only に書いてください")
        return
    n = len(glob.glob(os.path.join(cfg.jpn_only, "*_LOC_jpn.xxx")))
    if n == 0:
        rec("NG", "日本語音声パッケージ",
            f"{cfg.jpn_only} に *_LOC_jpn.xxx がありません。\n"
            f"         英語版 (*_LOC_int.xxx) ではなく日本語版を集めてください")
    elif n < JPN_XXX * 0.9:
        rec("WARN", "日本語音声パッケージ",
            f"{n} 本（{JPN_XXX} 本前後のはず）。足りないぶんは英語のまま残ります")
    else:
        rec("OK", "日本語音声パッケージ", f"{n} 本 ({cfg.jpn_only})")


def check_tool(label, path, hint):
    if path and os.path.exists(path):
        rec("OK", label, path)
        return path
    rec("NG", label,
        f"見つかりません: {path}\n"
        f"         config.ini の [tools] を確認してください\n"
        f"         {hint}")
    return None


def check_decompress(cfg):
    check_tool("decompress（手順3）", cfg.decompress, "入手先: https://www.gildor.org/downloads")


def check_umodel(cfg):
    """umodel は存在だけ見る。

    引数なしで起動すると GUI が開き、閉じるまで戻ってこない。素性を確かめるために
    走らせてはいけない（手順4 の注意と同じ話）。
    """
    check_tool("umodel（手順4）", cfg.umodel,
               "入手先: https://www.gildor.org/en/projects/umodel")


def check_vgmstream(cfg):
    p = check_tool("vgmstream（手順6）", cfg.vgmstream, "入手先: https://vgmstream.org/")
    if not p:
        return
    try:
        r = subprocess.run([p, "-h"], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        rec("NG", "vgmstream の動作", f"起動できません: {e}")
        return
    blob = (r.stdout + r.stderr).decode("utf-8", "replace").lower()
    if "vgmstream" not in blob:
        rec("NG", "vgmstream の素性",
            f"{p} は vgmstream ではないようです。同名の別のものを指しています")
    else:
        rec("OK", "vgmstream の素性", "確認できました")


def check_ffmpeg(cfg):
    p = check_tool("ffmpeg（手順6）", cfg.ffmpeg, "入手先: https://ffmpeg.org/download.html")
    if not p:
        return
    try:
        r = subprocess.run([p, "-hide_banner", "-encoders"], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        rec("NG", "ffmpeg の動作", f"起動できません: {e}")
        return
    if b"libvorbis" not in r.stdout:
        rec("NG", "ffmpeg の libvorbis",
            "この ffmpeg は libvorbis を持っていません。Ogg に変換できないので別のビルドが要ります")
    else:
        rec("OK", "ffmpeg の libvorbis", "利用できます")


def check_space(cfg):
    probe = cfg.work
    while probe and not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    try:
        free = shutil.disk_usage(probe).free / (1 << 30)
    except OSError as e:
        rec("WARN", "空き容量", f"{probe} を確認できません: {e}")
        return
    detail = f"{free:.1f} GB 空き（作業フォルダ {cfg.work}）"
    rec("OK" if free >= NEED_GB else "NG", "空き容量",
        detail if free >= NEED_GB else detail + f" / 約 {NEED_GB} GB 必要です")


def check_openal(cfg):
    """OpenAL32.dll と DeviceName が噛み合っているかを見る。

    出荷時は純正ルーターと Generic Software の対で成立している。OpenAL Soft に
    差し替えた場合だけ DeviceName=OpenAL Soft が要る。食い違うとゲームの音が
    全部無音になるので、そのときだけ警告する。純正のままの人には何も言わない。
    """
    import openal
    dll = os.path.join(cfg.hollow, "Binaries", "OpenAL32.dll")
    kind = openal.dll_kind(dll)
    if kind is None:
        rec("WARN", "OpenAL", f"{dll} がありません。ゲームの導入が壊れているかもしれません")
        return
    name, src = openal.current_device_name(cfg.hollow)
    label = {"soft": "OpenAL Soft", "router": "純正ルーター", "unknown": "判別できない DLL"}[kind]
    shown = f'"{name}"' if name else "（空・既定のデバイス）"
    if kind == "unknown":
        rec("WARN", "OpenAL", f"OpenAL32.dll の素性が判別できません。DeviceName は {shown}")
        return
    if openal.is_consistent(kind, name):
        rec("OK", "OpenAL", f"{label} ＋ DeviceName={shown}")
    else:
        rec("WARN", "OpenAL",
            f"{label} なのに DeviceName={shown} になっています。\n"
            f"         この組み合わせではゲームの音が全部鳴りません（日本語化とは無関係）。\n"
            f"         98_音が出ないとき.bat で直せます\n"
            f"         {src}")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"ツール: {here}")
    print("-" * 70)
    check_python()
    check_modules()
    cfg = load_config()
    if cfg:
        if check_hollow(cfg):
            check_backup(cfg)
            check_installed(cfg)
            check_openal(cfg)
        check_jpn(cfg)
        check_decompress(cfg)
        check_umodel(cfg)
        check_vgmstream(cfg)
        check_ffmpeg(cfg)
        check_space(cfg)
    else:
        print("\n設定が読めないので、これ以降の検査は飛ばします。")

    ng = [r for r in results if r[0] == "NG"]
    warn = [r for r in results if r[0] == "WARN"]
    print("-" * 70)
    print(f"OK {len(results) - len(ng) - len(warn)} / 注意 {len(warn)} / NG {len(ng)}")
    if ng:
        print("\nこのままでは手順の途中で止まります。上の NG を直してください:")
        for _lv, name, _d in ng:
            print(f"  - {name}")
        return 1
    if warn:
        print("\n注意はありますが、手順を始められます。")
    else:
        print("\n問題ありません。手順2から始められます。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
