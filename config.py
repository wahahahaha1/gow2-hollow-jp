"""設定ファイル (config.ini) の読み込み。

各スクリプトはここから入出力先とツールの場所を取得する。
パスの直書きはこのモジュールと config.ini に集約されている。

    from config import CFG
    print(CFG.plan)          # 対応表の出力先
    print(CFG.vgmstream)     # vgmstream-cli.exe の場所

config.ini が無い、必要な項目が空、という場合は起動時に日本語で理由を出して止まる。
"""
import configparser
import os
import sys


def _utf8_stdio():
    """日本語の出力が cp932 で化けないようにする。

    Windows の既定コンソールは cp932 で、日本語のエラーメッセージがそのままでは
    読めない文字列になる。このモジュールは全スクリプトが読み込むので、
    ここで一度だけ直しておく。バッチ経由なら gow2jp.bat が環境変数でも同じことをする。
    """
    for st in (sys.stdout, sys.stderr):
        try:
            if st is not None and getattr(st, "encoding", "").lower() not in ("utf-8", "utf8"):
                st.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_utf8_stdio()

HERE = os.path.dirname(os.path.abspath(__file__))
INI = os.path.join(HERE, "config.ini")
EXAMPLE = os.path.join(HERE, "config.ini.example")


class ConfigError(SystemExit):
    """設定の不備。トレースバックではなく理由を表示して終了する。"""
    def __init__(self, message):
        super().__init__(f"\n[設定エラー] {message}\n")


def _read_ini(path):
    """config.ini を文字コードを見分けて読む。

    利用者がどのエディタで保存するかは選べない。メモ帳の既定は UTF-8 だが
    「UTF-8 (BOM付き)」も選べるし、サクラエディタや秀丸は Shift-JIS が既定。
    UTF-8 決め打ちで読むと、Shift-JIS で保存された時点で UnicodeDecodeError の
    トレースバックになって、利用者には何が悪いのか分からない。

    openal.py が BaseEngine.ini を utf-8 → latin-1 で読み分けているのと同じ考え方。
    こちらは日本語のコメントを正しく読む必要があるので受け皿は cp932 にする。
    """
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ConfigError(
        f"config.ini の文字コードが読めません。\n"
        f"  {path}\n"
        f"UTF-8 か Shift-JIS で保存し直してください。"
    )


def _clean(v):
    """設定値の前後を整える。

    エクスプローラの「パスのコピー」は `"C:\\Games\\..."` と引用符付きで貼られる。
    README は「コピーしたまま貼り付けて構いません」と案内しているので、
    引用符が付いていても通るようにしておく。
    """
    return v.strip().strip('"').strip()


class Config:
    def __init__(self, path=INI):
        if not os.path.exists(path):
            raise ConfigError(
                f"config.ini が見つかりません。\n"
                f"  {EXAMPLE}\n"
                f"を config.ini という名前でコピーし、自分の環境に合わせて書き換えてください。"
            )
        cp = configparser.ConfigParser(inline_comment_prefixes=(";",))
        try:
            cp.read_string(_read_ini(path), source=path)
        except configparser.Error as e:
            raise ConfigError(
                f"config.ini の書き方に誤りがあります。\n"
                f"  {path}\n"
                f"  {e}\n"
                f"`=` の右側だけを書き換えて、`[paths]` などの行は消さないでください。"
            )
        self._cp = cp

        # --- 利用者が指定するもの ---
        self.hollow   = self._req("paths", "hollow")
        self.jpn_only = self._req("paths", "jpn_only")
        self.work     = self._req("paths", "work")

        self.decompress = self._req("tools", "decompress")
        self.umodel     = self._req("tools", "umodel")
        self.vgmstream  = self._req("tools", "vgmstream")
        self.ffmpeg     = self._req("tools", "ffmpeg")

        self.quality = self._cp.get("convert", "quality", fallback="3").strip()
        self.rate    = int(self._cp.get("convert", "rate", fallback="22050").strip())

        # --- 上記から導かれるもの（利用者は設定しない） ---
        j = os.path.join
        self.sounds_int = j(self.hollow, "GearGame", "Content", "Sounds", "INT")
        self.movies     = j(self.hollow, "GearGame", "Movies")

        self.dec        = self._opt("dec", j(self.work, "dec_jpn"))
        self.snd        = self._opt("snd", j(self.work, "snd_jpn"))
        self.ogg        = j(self.work, "jp_ogg")
        self.upk_out    = j(self.work, "upk_jp")
        # 無改造の Sounds\INT の置き場所。指定が無ければ work の下を使う。
        self.original   = self._opt("original", j(self.work, "original_Sounds_INT"))
        self.plan       = j(self.work, "plan.json")
        self.manifest   = j(self.work, "jp_ogg_manifest.json")

    def _opt(self, key, default):
        """[paths] の任意項目。空なら既定値（work の下）を使う。"""
        return _clean(self._cp.get("paths", key, fallback="")) or default

    def _req(self, section, key):
        try:
            v = _clean(self._cp.get(section, key))
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ConfigError(f"config.ini に [{section}] の {key} がありません。")
        if not v:
            raise ConfigError(f"config.ini の [{section}] {key} が空です。")
        return v

    def need_tool(self, path, name):
        """ツールを起動する直前に呼ぶ。無ければ理由を出して止まる。"""
        if not os.path.exists(path):
            raise ConfigError(
                f"{name} が見つかりません。\n"
                f"  設定値: {path}\n"
                f"config.ini の [tools] を確認してください。"
            )
        return path

    def need_dir(self, path, what):
        if not os.path.isdir(path):
            raise ConfigError(f"{what} が見つかりません。\n  設定値: {path}")
        return path

    def ensure(self, path):
        """出力先を作って返す。"""
        os.makedirs(path, exist_ok=True)
        return path


CFG = Config()

if __name__ == "__main__":
    print("読み込んだ設定:\n")
    for k in ("hollow", "sounds_int", "movies", "jpn_only", "work",
              "dec", "snd", "ogg", "upk_out", "original", "plan", "manifest",
              "decompress", "umodel", "vgmstream", "ffmpeg", "quality", "rate"):
        v = getattr(CFG, k)
        mark = ""
        if k in ("decompress", "umodel", "vgmstream", "ffmpeg"):
            mark = "  " + ("OK" if os.path.exists(v) else "← 見つからない")
        elif k in ("hollow", "sounds_int", "jpn_only"):
            mark = "  " + ("OK" if os.path.isdir(v) else "← 見つからない")
        print(f"  {k:<12} {v}{mark}")
