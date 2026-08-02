import httpx
import os

# 🎯 GIAO THỨC KẾT NỐI HOST (UNIFIED BRIDGE)
HOST_URL = "http://host.docker.internal:9998"
AKAI_TOKEN = os.getenv("AKAI_SATELLITE_TOKEN", "AKAI_PRIME_SUPER_SECRET_999")

async def host_speak(text: str):
    """Phát âm thanh qua loa máy tính Host"""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{HOST_URL}/speak",
            json={"text": text},
            headers={"X-AKAI-TOKEN": AKAI_TOKEN}
        )
        return res.json()

async def host_screenshot():
    """Chụp ảnh màn hình Host"""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{HOST_URL}/screenshot",
            headers={"X-AKAI-TOKEN": AKAI_TOKEN}
        )
        return res.json()

async def host_execute(command: str, shell: str = "powershell"):
    """Thực thi lệnh trực tiếp trên Host"""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{HOST_URL}/terminal",
            json={"command": command, "shell": shell},
            headers={"X-AKAI-TOKEN": AKAI_TOKEN}
        )
        return res.json()

async def host_click(x: int, y: int, clicks: int = 1):
    """Click chuột trên màn hình Host"""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{HOST_URL}/click",
            json={"x": x, "y": y, "clicks": clicks},
            headers={"X-AKAI-TOKEN": AKAI_TOKEN}
        )
        return res.json()
