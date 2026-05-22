import asyncio
import sys
import os
import httpx
from pathlib import Path

# Thêm đường dẫn để import các module core
sys.path.append(os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N"))

# Găm cứng biến môi trường cho Host Windows
os.environ["OLLAMA_HOST"] = "http://localhost:11434"

from intelligence.skills.skill_dongbotrithuc.logic import JKAI_Assimilator

async def check_ollama():
    print("[CHECK] Dang kiem tra ket noi den Ollama...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            print(f"[CHECK] OK! Ollama dang song. Version: {resp.status_code}")
            return True
    except Exception as e:
        print(f"[CHECK] LOI! Khong the ket noi den Ollama tai localhost:11434: {e}")
        return False

async def main():
    if not await check_ollama():
        return
        
    print("[TARGETED-SYNC] KICH HOAT GIAO THUC TAN CONG TRONG TIEP...")
    assimilator = JKAI_Assimilator()
    
    # Chỉnh hướng Assimilator vào thẳng thư mục skills
    target_path = Path(os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N") + "/intelligence/archive/import_dump/everything-claude-code-main/skills")
    assimilator.import_dir = target_path
    
    print(f"[TARGET] Dang tan cong vao: {target_path}")
    
    # Chạy quy trình Tổng tiến công (B1-B4)
    await assimilator.run_general_offensive()
    print("[SYNC-COMPLETE] Chien dich ket thuc. Master hay kiem tra bao cao thua Master!")

if __name__ == "__main__":
    asyncio.run(main())
