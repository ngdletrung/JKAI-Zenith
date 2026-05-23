import asyncio
import httpx
import json

async def main():
    print("🚀 Đang gửi Lệnh Tối Cao tới JKAI Zenith...")
    url = "http://127.0.0.1:8001/plan"
    payload = {
        "goal": "Chạy file d:\\Docker\\N8N\\scripts\\test\\buggy_test.py. Nếu có lỗi xảy ra khi chạy (VD: IndexError), hãy kích hoạt Giao thức Self-Healing: Dùng tool xem lỗi, sửa file bằng quyền hệ thống và chạy lại cho đến khi thành công.",
        "task_id": "test_self_healing_01"
    }
    
    try:
        async with httpx.AsyncClient(timeout=1200) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                print("✅ JKAI đã tiếp nhận mệnh lệnh và sinh ra Plan:")
                plan = resp.json()
                print(json.dumps(plan, indent=2, ensure_ascii=False))
            else:
                print(f"❌ Lỗi: {resp.status_code}")
                print(resp.text)
    except Exception as e:
        print(f"❌ Không kết nối được tới AI Brain: {e}")

if __name__ == "__main__":
    asyncio.run(main())
