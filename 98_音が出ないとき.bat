@echo off
cd /d "%~dp0."
echo ゲームの音が「全部」鳴らないときに使います。
echo 日本語化とは別の話で、多くの人には必要ありません。
echo.
echo OpenAL32.dll を OpenAL Soft に差し替えている場合、ゲームの設定が
echo 出荷時の値のままだと音声デバイスの初期化に失敗して全部無音になります。
echo.
echo まず今どうなっているかを調べます。ここでは書き込みません。
echo.
call "%~dp0gow2jp.bat" openal
if not errorlevel 1 goto :nothing
echo.
echo ----------------------------------------------------------------
set /p ANSWER=直すなら y を入力して Enter (やめるなら何も入れずに Enter):
if /i not "%ANSWER%"=="y" goto :cancel
echo.
call "%~dp0gow2jp.bat" openal --apply
goto :done
:nothing
echo.
echo ----------------------------------------------------------------
echo 直すところはありません。このまま閉じてください。
goto :done
:cancel
echo.
echo 中止しました。設定は変えていません。
:done
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
