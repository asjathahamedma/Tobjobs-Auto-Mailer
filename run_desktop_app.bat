@echo off
setlocal
cd /d "%~dp0"

set "APP_EXE_A=src-tauri\target\release\topjobs-auto-mailer-shell.exe"
set "APP_EXE_B=src-tauri\target\release\TopJobs Auto Mailer.exe"

if exist "%APP_EXE_A%" (
    start "" "%APP_EXE_A%" %*
    exit /b 0
)

if exist "%APP_EXE_B%" (
    start "" "%APP_EXE_B%" %*
    exit /b 0
)

set "LOCAL_NODE=%ProgramFiles%\nodejs"
if exist "%LOCAL_NODE%\npm.cmd" (
    set "PATH=%USERPROFILE%\.cargo\bin;%LOCAL_NODE%;%PATH%"
    call "%LOCAL_NODE%\npm.cmd" run tauri:dev -- %*
    exit /b %errorlevel%
)

call npm run tauri:dev -- %*
