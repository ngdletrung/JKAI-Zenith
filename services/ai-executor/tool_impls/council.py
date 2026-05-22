import asyncio
import json
from core.utils.engine import engine

async def initiate_agentic_debate(topic: str, task_id: str = "council"):
    """
    🏛️ [SUPREME COUNCIL]: Triệu tập Hội đồng Trí tuệ để tranh biện đa chiều.
    """
    results = []
    
    # 🧠 BƯỚC 1: QUÂN SƯ (PLANNER) ĐƯA RA ĐỀ XUẤT SƠ BỘ
    planner_prompt = f"Mục tiêu: {topic}. Hãy đưa ra một bản phác thảo chiến lược sơ bộ."
    planner_task = asyncio.create_task(engine.call_chat(
        messages=[{"role": "user", "content": planner_prompt}],
        role="PLANNER",
        task_id=f"{task_id}_planner"
    ))
    
    # 🛠️ BƯỚC 2: CHIẾN BINH (EXECUTOR) CHUẨN BỊ CÔNG CỤ (CHẠY SONG SONG)
    executor_prompt = f"Với mục tiêu: {topic}, hãy liệt kê các công cụ (tools) cần thiết và kiểm tra tính khả thi kỹ thuật."
    executor_task = asyncio.create_task(engine.call_chat(
        messages=[{"role": "user", "content": executor_prompt}],
        role="EXECUTOR",
        task_id=f"{task_id}_executor"
    ))

    # Đợi cả hai cùng nghe và cùng nghĩ
    planner_res, executor_res = await asyncio.gather(planner_task, executor_task)
    
    # 🛡️ BƯỚC 3: PHẢN BIỆN (CRITIC) THẨM ĐỊNH TỔNG THỂ
    critic_prompt = f"""Hội đồng đang thảo luận về: {topic}
    - Đề xuất của Planner: {planner_res}
    - Ý kiến kỹ thuật của Executor: {executor_res}
    
    Hãy phản biện, tìm ra lỗ hổng và đưa ra kết luận tối thượng của Hội đồng."""
    
    critic_res = await engine.call_chat(
        messages=[{"role": "user", "content": critic_prompt}],
        role="CRITIC",
        task_id=f"{task_id}_critic"
    )
    
    return {
        "status": "success",
        "council_decision": critic_res,
        "details": {
            "planner_strategy": planner_res,
            "executor_feasibility": executor_res
        },
        "description": "🏛️ Hội đồng Trí tuệ đã thống nhất giải pháp tối thượng."
    }
