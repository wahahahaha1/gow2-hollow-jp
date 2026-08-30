@echo off
rem GoW2 日本語音声移植ツール - 入口
rem
rem 同梱の Python があればそれを使う。無ければ PC に入っている Python を探す。
rem
rem このファイルは cp932 (Shift-JIS) で保存すること。chcp は使わない。
rem Python 側の日本語出力は PYTHONUTF8 と config.py が受け持つ。

setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "HERE=%~dp0"

if exist "%HERE%python\python.exe" (
    "%HERE%python\python.exe" "%HERE%gow2jp.py" %*
    goto :done
)

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%HERE%gow2jp.py" %*
    goto :done
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%HERE%gow2jp.py" %*
    goto :done
)

echo Python が見つかりません。
echo.
echo Python 同梱版の配布物を使うか、https://www.python.org/ から
echo Python 3 を入れてください。インストール時に
echo "Add python.exe to PATH" にチェックを入れること。
exit /b 1

:done
endlocal
exit /b %ERRORLEVEL%
