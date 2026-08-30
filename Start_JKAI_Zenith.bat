@echo off
setlocal enabledelayedexpansion
color 0A
title [JKAI ZENITH - AMG BOOTSTRAP]
echo ==============================================================================
echo   JKAI ZENITH: PRE-FLIGHT CLEANUP ^& INFRASTRUCTURE BOOTSTRAP
echo ==============================================================================
cd /d "D:\Docker\JKAI"

:: ============================================================================
:: PHASE 0 — JKAI RESOURCE LIBERATION
:: Unload Ollama models + kill Docker + kill PowerShell cu de khoi dong sach.
:: ============================================================================
echo.
echo [PHASE 0] Dang giai phong tai nguyen JKAI cu...
echo ------------------------------------------------------------------------------

:: --- 0A. Unload Ollama models (VRAM/RAM) tren GPU instance (port 11434) ---
echo [0A] Unloading Ollama models tu GPU instance (port 11434)...
for /f "usebackq tokens=*" %%M in (`curl -s http://localhost:11434/api/ps 2^>nul ^| python -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]" 2^>nul`) do (
    echo    Unloading: %%M
    curl -s -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" -d "{\"model\":\"%%M\",\"keep_alive\":0,\"messages\":[]}" >nul 2>&1
)

:: --- 0B. Unload Ollama models (RAM) tren CPU instance (port 11435) ---
echo [0B] Unloading Ollama models tu CPU instance (port 11435)...
for /f "usebackq tokens=*" %%M in (`curl -s http://localhost:11435/api/ps 2^>nul ^| python -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin).get('models',[])]" 2^>nul`) do (
    echo    Unloading: %%M
    curl -s -X POST http://localhost:11435/api/chat -H "Content-Type: application/json" -d "{\"model\":\"%%M\",\"keep_alive\":0,\"messages\":[]}" >nul 2>&1
)
timeout /t 2 /nobreak >nul
echo    Ollama models: DONE.

:: --- 0C. Dung Docker containers (giai phong RAM container) ---
echo [0C] Dung tat ca Docker containers dang chay...
docker compose -f docker-compose.yml down --remove-orphans >nul 2>&1
echo    Docker containers: DA DUNG.

:: --- 0D. Kill tat ca tien trinh Ollama, llama-server va PowerShell runner cu ---
echo [0D] Kill sach tien trinh Ollama va PowerShell runner cu (11434, 11435)...
python -c "import psutil; [p.kill() for p in psutil.process_iter(['name','cmdline']) if any(k in (p.info.get('name') or '').lower() for k in ['ollama','llama-server']) or ('powershell' in (p.info.get('name') or '').lower() and any(k in ' '.join(p.info.get('cmdline') or []) for k in ['run_ollama','11434','11435','Zenith_Guardian']))]" >nul 2>&1
taskkill /F /IM ollama.exe >nul 2>&1
taskkill /F /IM llama-server.exe >nul 2>&1
echo    Tien trinh Ollama ^& PowerShell cu: DA KILL SACH.

echo.
echo [PHASE 0 COMPLETE] Tai nguyen JKAI da duoc giai phong sach.
echo ==============================================================================
timeout /t 2 /nobreak >nul

:: ============================================================================
:: PHASE 1 — INFRASTRUCTURE BOOTSTRAP (Ollama dual-engine + Docker core profile)
:: ============================================================================
echo.
echo [PHASE 1] Khoi dong Infrastructure (Ollama GPU+CPU + Docker --profile core)...
powershell -ExecutionPolicy Bypass -File "D:\Docker\JKAI\Zenith_Guardian.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Infrastructure bootstrap failed. Stopping.
    pause
    exit /b %ERRORLEVEL%
)

:: ============================================================================
:: PHASE 2 — AMG v2 BOOT ORCHESTRATOR
:: ============================================================================
echo.
echo [PHASE 2] Khoi dong AMG v2 Boot Orchestrator...
python -m core.runtime.amg_boot --mode FAST
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] AMG v2 Boot Orchestration failed. Stopping.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================================================
echo   JKAI ZENITH BOOT COMPLETE --- ENGINE READY
echo ==============================================================================
endlocal
