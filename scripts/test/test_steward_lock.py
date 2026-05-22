import httpx
import asyncio
import json

async def test_steward():
    url = "http://localhost:8000/gpu/request" # Gọi qua localhost vì chạy từ host hoặc mapping port
    
    print("🚀 [TEST] Requesting GPU for OLLAMA...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json={
                "service": "ollama",
                "model": "gemma4:e2b"
            }, timeout=10.0)
            print(f"✅ Response: {resp.status_code} - {resp.json()}")
            
            print("\n🚀 [TEST] Requesting GPU for STABLE-DIFFUSION (Should trigger swap)...")
            resp = await client.post(url, json={
                "service": "stable-diffusion",
                "model": "v1.5"
            }, timeout=30.0)
            print(f"✅ Response: {resp.status_code} - {resp.json()}")

    except Exception as e:
        print(f"❌ [TEST] Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_steward())
