import asyncio
import uuid
from datetime import datetime, timezone
import redis.asyncio as redis_async
from models.task import Task, TaskStatus

async def main():
    print("🚀 Bắt đầu giả lập hệ thống (End-to-End Test)...")
    
    # Kết nối đến Redis trong Docker
    redis = await redis_async.from_url("redis://:Admin@123456@redis-ai:6379", decode_responses=True)
    
    trace_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    
    demo_task = Task(
        task_id=task_id,
        trace_id=trace_id,
        goal="Tính tổng của 234 và 987 bằng công cụ math_calculator",
        status=TaskStatus.PENDING,
        autonomy_tier=4,
        execution_mode="BALANCED",
        budget_limit=0.5,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    task_json = demo_task.json()
    
    print(f"📦 Đang đẩy Nhiệm vụ {task_id} vào Redis Queue [ai_task_queue]")
    await redis.lpush("ai_task_queue", task_json)
    
    print("👀 Chờ 2 giây để Control Plane nhận task...")
    await asyncio.sleep(2)
        
    await redis.close()
    print("✅ Đã đẩy task thành công! Hãy kiểm tra logs của ai-control-plane.")

if __name__ == "__main__":
    asyncio.run(main())
