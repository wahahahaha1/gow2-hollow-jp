@echo off
cd /d "%~dp0."
echo 360側の音声と PC側の音声の対応表を作ります。
echo.
call "%~dp0gow2jp.bat" plan
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
