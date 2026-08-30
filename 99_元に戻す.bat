@echo off
cd /d "%~dp0."
echo 日本語化する前の状態に戻します。
echo 控えておいた音声パッケージを書き戻し、音声設定も元に戻します。
echo.
echo ゲームは終了しておいてください。起動していると書き換えられません。
echo.
set /p ANSWER=戻してよければ y を入力して Enter (やめるなら何も入れずに Enter):
if /i not "%ANSWER%"=="y" goto :cancel
echo.
call "%~dp0gow2jp.bat" deploy --uninstall
if errorlevel 1 goto :failed
echo.
call "%~dp0gow2jp.bat" openal --restore
goto :done
:failed
echo.
echo ----------------------------------------------------------------
echo 音声パッケージを戻せませんでした。上に出ている理由を読んでください。
echo 音声設定 (DeviceName) にはまだ触っていません。
goto :done
:cancel
echo.
echo 中止しました。何も変更していません。
:done
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
