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

where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found. Install uv before building the desktop app.
    exit /b 1
)

call uv python install 3.12 --install-dir .python\runtime
if errorlevel 1 exit /b 1

for /f "delims=" %%P in ('where /r ".python\runtime" python.exe') do if not defined TOPJOBS_BASE_PYTHON set "TOPJOBS_BASE_PYTHON=%%P"
if not defined TOPJOBS_BASE_PYTHON (
    echo Could not find python.exe in the portable Python runtime.
    exit /b 1
)

set "TOPJOBS_PYTHON=%TOPJOBS_BASE_PYTHON%"
call uv pip install --python "%TOPJOBS_PYTHON%" --target .python\site-packages -r requirements.txt
if errorlevel 1 exit /b 1

call run_npm.bat install
if errorlevel 1 exit /b %errorlevel%

call run_npm.bat run tauri:build
exit /b %errorlevel%
