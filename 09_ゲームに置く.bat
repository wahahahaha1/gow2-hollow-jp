@echo off
cd /d "%~dp0."
echo ここではじめてゲームのフォルダに書き込みます。
echo 先に「何が置かれるか」だけを表示します。
echo.
echo ゲームは終了しておいてください。起動していると書き換えられません。
echo.
call "%~dp0gow2jp.bat" deploy
if errorlevel 1 goto :stopped
echo.
echo ----------------------------------------------------------------
set /p ANSWER=上の内容でよければ y を入力して Enter (やめるなら何も入れずに Enter):
if /i not "%ANSWER%"=="y" goto :cancel
echo.
call "%~dp0gow2jp.bat" deploy --install
goto :done
:cancel
echo.
echo 中止しました。ゲームには何も置いていません。
goto :done
:stopped
echo.
echo 先に進めません。上の内容を直してからやり直してください。
:done
echo.
echo ----------------------------------------------------------------
echo 終わりました。このウィンドウは閉じて構いません。
pause
