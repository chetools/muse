@echo off
rem Teacher Audit (HW Signing) - web front end.
rem Standard library only: no packages to install. If no Python is
rem present, uv provides one (uv venv downloads a managed Python).
rem
rem This file uses labels and goto, never parenthesised blocks, on
rem purpose: a typical Windows PATH contains an NVIDIA entry under
rem "Program Files (x86)", and expanding %PATH% inside a ( ... )
rem block ends the block at the ")" of "(x86)" - cmd then fails with
rem "\NVIDIA was unexpected at this time." At top level the same
rem expansion is harmless. For the same reason %errorlevel% is never
rem tested inside a block; "if errorlevel" is evaluated at run time.
rem
rem The browser is opened by the program itself, once its
rem server is answering (v37) - opening it from here raced
rem the server start and landed on a cannot-connect page.
rem Since v69 the program opens Chrome when Chrome is
rem installed, with a dedicated profile stored in this
rem folder (browser-profile), and the default browser
rem otherwise: the video wall runs more reliably in Chrome
rem under sustained many-video playback, and the dedicated
rem profile keeps the teacher's own browser profile - its
rem extensions and settings - out of the app window.

cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto start_app

where uv >nul 2>nul
if not errorlevel 1 goto create_venv

echo Installing uv...
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

:create_venv
echo Setting up for first use: creating .venv with uv...
uv venv .venv
if not errorlevel 1 goto start_app
echo.
echo uv could not create the virtual environment. See the messages above.
pause
exit /b 1

:start_app
echo Starting Teacher Audit at http://127.0.0.1:8766
echo The browser opens by itself once the app is ready
echo (Chrome, with its own profile, when it is installed).
echo Keep this window open while you work. Close it to stop the app.
".venv\Scripts\python.exe" web.py --port 8766
pause
