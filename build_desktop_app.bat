@echo off
setlocal
cd /d "%~dp0"

set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
    echo Visual Studio Build Tools were not found.
    echo Install them first, then run this build again.
    exit /b 1
)

call "%VCVARS%"
set "PATH=%ProgramFiles%\nodejs;%USERPROFILE%\.cargo\bin;%PATH%"

call run_npm.bat install
if errorlevel 1 exit /b %errorlevel%

call run_npm.bat run tauri:build
exit /b %errorlevel%
