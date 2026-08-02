import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import pyautogui
import mss
import mss.tools
import os
import time
import subprocess
from typing import Optional

app = FastAPI(title="AKAI Host Satellite - FULL ACCESS")

# MÃ BÍ MẬT - Xác thực từ Docker
AKAI_SECRET_TOKEN = os.getenv("AKAI_SATELLITE_TOKEN", "AKAI_PRIME_SUPER_SECRET_999")

@app.middleware("http")
async def verify_akai_token(request: Request, call_next):
    if request.url.path == "/status":
        return await call_next(request)
    token = request.headers.get("X-AKAI-TOKEN")
    if token != AKAI_SECRET_TOKEN:
        return uvicorn.responses.JSONResponse(
            content={"error": "⚠️ TRUY CẬP TRÁI PHÉP: Sai mã bí mật."},
            status_code=403
        )
    return await call_next(request)

# Thư mục lưu snapshot
SCREENSHOT_DIR = "akai_host_snapshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class ClickAction(BaseModel):
    x: int
    y: int
    clicks: int = 1

class TypeAction(BaseModel):
    text: str

class FileAction(BaseModel):
    path: str
    content: Optional[str] = None
    action: str  # read, write, delete, list

class TerminalAction(BaseModel):
    command: str
    shell: str = "powershell"

@app.get("/status")
def status():
    return {"status": "online", "access_level": "FULL_ADMIN", "message": "AKAI is now the Overlord of this system."}

@app.get("/screenshot")
def take_screenshot():
    try:
        with mss.mss() as sct:
            filename = f"host_snap_{int(time.time())}.png"
            output = os.path.join(SCREENSHOT_DIR, filename)
            sct.shot(output=output)
            return {"status": "success", "file_path": os.path.abspath(output)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/click")
def click_desktop(action: ClickAction):
    pyautogui.click(x=action.x, y=action.y, clicks=action.clicks)
    return {"status": "success"}

@app.post("/type")
def type_text(action: TypeAction):
    pyautogui.typewrite(action.text)
    return {"status": "success"}

@app.post("/file")
def manage_file(action: FileAction):
    """Quyền truy cập file trực tiếp trên toàn bộ ổ đĩa"""
    try:
        path = os.path.abspath(action.path)
        if action.action == "read":
            with open(path, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        elif action.action == "write":
            with open(path, "w", encoding="utf-8") as f:
                f.write(action.content)
            return {"status": "success", "msg": f"File written to {path}"}
        elif action.action == "delete":
            os.remove(path)
            return {"status": "success", "msg": f"File deleted: {path}"}
        elif action.action == "list":
            return {"files": os.listdir(path)}
        else:
            return {"error": "Invalid action"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speak")
def speak_text(action: TypeAction):
    """Phát âm thanh qua loa máy tính Windows"""
    try:
        # Sử dụng PowerShell để phát giọng nói (không cần cài thêm thư viện)
        cmd = f"Add-Type -AssemblyName System.speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{action.text}')"
        subprocess.run(["powershell", "-Command", cmd], timeout=30)
        return {"status": "success", "msg": f"Spoken: {action.text}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/terminal")
def execute_terminal(action: TerminalAction):
    """Quyền thực thi Terminal/PowerShell trực tiếp trên Windows"""
    try:
        result = subprocess.run(
            [action.shell, "-Command" if action.shell == "powershell" else "/c", action.command],
            capture_output=True, text=True, timeout=30
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("👑 AKAI Host Satellite - FULL ACCESS MODE ACTIVE")
    print("🚀 Listening on http://0.0.0.0:9997")
    uvicorn.run(app, host="0.0.0.0", port=9997)
