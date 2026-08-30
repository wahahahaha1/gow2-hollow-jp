# 同梱している Python について

Python 不要版の配布物には、`python/` に CPython の Windows 用
embeddable package をそのまま展開して同梱している。

| | |
|---|---|
| バージョン | 3.13.15 |
| 入手元 | https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip |
| SHA256 | `d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf` |
| サイズ | 11,009,825 バイト |
| ライセンス | `python/LICENSE.txt`（PSF License Agreement） |

embeddable package は「アプリケーションに組み込んで配布する」用途のために
python.org が公式に用意しているもので、再頒布が認められている。
条件は著作権表示とライセンス本文を残すことで、`python/LICENSE.txt` がそれにあたる。
**このファイルを消さないこと。**

同梱物には OpenSSL（`libcrypto-3.dll` / `libssl-3.dll`）、SQLite（`sqlite3.dll`）、
Microsoft の VC ランタイム（`vcruntime140.dll` / `vcruntime140_1.dll`）が含まれる。
いずれも python.org が embeddable package に入れて配布しているものそのままで、
ライセンスは `python/LICENSE.txt` に記載がある。

## 作り直す場合

上記 URL の zip を落として、中身を `python/` に展開するだけでよい。
このリポジトリのスクリプトは標準ライブラリしか使わないので、pip でのインストールは要らない。

より新しい 3.13.x に差し替えても動くはずだが、差し替えたらこのファイルの
バージョンと SHA256 を更新すること。

なお、より厳密に検証したい場合は python.org が `.sigstore` 署名を公開している
（同 URL に `.sigstore` を付けたもの）。

## リポジトリには入れていない

`python/` は `.gitignore` で除外してある。
リポジトリはスクリプトだけを置き、Python 同梱版は Releases の zip として配布する。
