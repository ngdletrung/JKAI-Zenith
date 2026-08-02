import asyncio
import httpx
import json

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/receptionist", json={
            "goal": "tìm cho tôi 5 tin tức mới nhất về trung quốc",
            "task_id": "test_123",
            "mode": "fast"
        })
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
