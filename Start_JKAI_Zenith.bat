@echo off
color 0A
title [JKAI ZENITH - AMG BOOTSTRAP]
echo ==============================================================================
echo   JKAI ZENITH: STARTING INFRASTRUCTURE ^& AMG v2 DECISION ENGINE
echo ==============================================================================
cd /d "D:\Docker\JKAI"

:: 1. Infrastructure Bootstrap (Ollama dual-engine & Docker)
powershell -ExecutionPolicy Bypass -File "D:\Docker\JKAI\Zenith_Guardian.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Infrastructure bootstrap failed. Stopping.
    pause
    exit /b %ERRORLEVEL%
)

:: 2. AMG v2 Boot Orchestrator (Discovery, Decision, & Lifecycle)
echo [INFO] Running AMG v2 Boot Orchestrator...
python -m core.runtime.amg_boot --mode FAST
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] AMG v2 Boot Orchestration failed. Stopping.
    pause
    exit /b %ERRORLEVEL%
)

echo ==============================================================================
echo   JKAI ZENITH BOOT COMPLETE — ENGINE READY
echo ==============================================================================
