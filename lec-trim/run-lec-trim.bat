@echo off
rem Drag a folder of OBS clips onto this file, or run it in a folder of clips.
setlocal
set "HERE=%~dp0"
if "%~1"=="" goto run_here
"%HERE%lec-trim.exe" "%~1" --pause-at-end
goto :eof
:run_here
"%HERE%lec-trim.exe" . --pause-at-end
goto :eof
