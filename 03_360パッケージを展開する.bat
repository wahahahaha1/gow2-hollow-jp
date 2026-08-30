@echo off
cd /d "%~dp0."
echo 360版パッケージの圧縮を展開します。decompress.exe を 1 本ずつ呼びます。
echo 本数が多いので数分かかります。
echo.
call "%~dp0gow2jp.bat" decompress
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
