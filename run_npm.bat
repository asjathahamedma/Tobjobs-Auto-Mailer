@echo off
setlocal

if exist "%ProgramFiles%\nodejs\npm.cmd" (
    set "PATH=%USERPROFILE%\.cargo\bin;%ProgramFiles%\nodejs;%PATH%"
    call "%ProgramFiles%\nodejs\npm.cmd" %*
    exit /b %errorlevel%
)

call npm %*
