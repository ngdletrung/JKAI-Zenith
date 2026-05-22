import httpx
import asyncio
import os

async def purge_ollama():
    url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧹 [PURGE] Đang rà soát các model đang nạp...")
        try:
            resp = await client.get(f"{url}/api/ps")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    name = m["name"]
                    print(f"♻️ [PURGE] Đang giải phóng: {name}")
                    # Gửi yêu cầu với keep_alive = 0 để giải phóng ngay lập tức
                    await client.post(f"{url}/api/chat", json={
                        "model": name,
                        "messages": [],
                        "keep_alive": 0
                    })
            print("✨ [PURGE] VRAM đã được thanh lọc!")
        except Exception as e:
            print(f"❌ [PURGE-ERR] {e}")

if __name__ == "__main__":
    asyncio.run(purge_ollama())
