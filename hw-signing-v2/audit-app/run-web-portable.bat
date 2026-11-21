@echo off
rem Teacher Audit (HW Signing) - PORTABLE web front end.
rem Everything runs from this folder: the bundled Python in
rem runtime\python, ffmpeg / ffprobe / yt-dlp in runtime\bin.
rem No installation, no venv, no setup downloads. Copy the whole
rem folder to a new computer or a USB drive and run this file.
rem
rem This file uses labels and goto, never parenthesised blocks, on
rem purpose: a typical Windows PATH contains an NVIDIA entry under
rem "Program Files (x86)", and expanding %PATH% inside a ( ... )
rem block ends the block at the ")" of "(x86)" - cmd then fails with
rem "\NVIDIA was unexpected at this time." At top level the same
rem expansion is harmless. For the same reason %errorlevel% is never
rem tested inside a block; "if errorlevel" is evaluated at run time.

cd /d "%~dp0"
set "PATH=%~dp0runtime\bin;%PATH%"

if exist "runtime\python\python.exe" goto start_app
echo Bundled Python not found: runtime\python\python.exe
echo This copy of the folder is incomplete. Copy the whole
echo teacher-audit folder again, including the runtime folder.
pause
exit /b 1

:start_app
echo Starting Teacher Audit (portable) at http://127.0.0.1:8766
echo Keep this window open while you work. Close it to stop the app.
start "" http://127.0.0.1:8766
"runtime\python\python.exe" web.py --port 8766
pause
