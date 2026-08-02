@echo off
color 0B
title [JKAI ZENITH - AMG DIAGNOSTIC BOOT]
echo ==============================================================================
echo   JKAI ZENITH: AMG v2 DIAGNOSTIC BOOT
echo ==============================================================================
cd /d "D:\Docker\JKAI"

:: 1. Infrastructure Bootstrap
powershell -ExecutionPolicy Bypass -File "D:\Docker\JKAI\Zenith_Guardian.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Infrastructure bootstrap failed. Stopping.
    pause
    exit /b %ERRORLEVEL%
)

:: 2. AMG v2 Diagnostic Boot
python -m core.runtime.amg_boot --mode FAST --diagnostic

pause
