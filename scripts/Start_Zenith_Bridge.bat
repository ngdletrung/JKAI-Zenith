@echo off
title [ JKAI ZENITH: HOST BRIDGE ACTIVATOR ]
color 0B

echo ========================================================
echo   [ JKAI ZENITH: KICH HOAT CAU NOI VAT LY ]
echo   He thong dang ket noi Neural Bridge voi Windows...
echo ========================================================
echo.

:: 1. Kiem tra va cai dat thu vien
echo [1/2] Dang kiem tra cac linh kien thiet yeu...
python -m pip install pyautogui mss uvicorn fastapi pydantic requests --user
if %errorlevel% neq 0 (
    echo [!] LOI: Khong the cai dat thu vien. Vui long kiem tra ket noi mang.
    pause
    exit /b
)
echo [+] Linh kien da san sang.
echo.

:: 2. Khoi dong Bridge
echo [2/2] Dang thong mach vơi Host...
echo.
echo --------------------------------------------------------
echo   ZENITH IS NOW WATCHING AND LISTENING... 💎🫡
echo   Dia chi: http://localhost:9998
echo   (Vui long khong dong cua so nay khi dang su dung AI)
echo --------------------------------------------------------
echo.

python host_bridge.py

pause
