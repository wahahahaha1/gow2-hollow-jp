@echo off
cd /d "%~dp0."
echo 取り出した音声を Ogg Vorbis に変換します。10-20 分ほどかかります。
echo 中断しても、もう一度実行すれば続きから進みます。
echo.
call "%~dp0gow2jp.bat" convert
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
