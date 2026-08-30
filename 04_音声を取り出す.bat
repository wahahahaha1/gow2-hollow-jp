@echo off
cd /d "%~dp0."
echo 360版パッケージから音声を取り出します。umodel を 1 本ずつ呼びます。
echo 本数が多いので時間がかかります。
echo.
call "%~dp0gow2jp.bat" extract
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
