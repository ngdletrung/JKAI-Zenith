import asyncio
import json
from core.utils.engine import engine

async def initiate_agentic_debate(topic: str, task_id: str = "council"):
    """
    🏛️ [SUPREME COUNCIL]: Triệu tập Hội đồng Trí tuệ để tranh biện đa chiều.
    """
    # 🧠 BƯỚC 1: QUÂN SƯ (PLANNER) & CHIẾN BINH (EXECUTOR) CÙNG NGHE VÀ CÙNG NGHĨ
    # Chúng ta khởi chạy song song để tối ưu hóa thời gian
    
    planner_prompt = f"Mục tiêu chiến lược: {topic}. Hãy đưa ra bản phác thảo các bước cần thực hiện."
    executor_prompt = f"Mục tiêu kỹ thuật: {topic}. Hãy kiểm tra các công cụ cần thiết và dự báo rủi ro thực thi."

    # Planner chạy trên CPU (DeepSeek), Executor chạy trên GPU (Gemma 2) -> SONG SONG TUYỆT ĐỐI!
    planner_task = asyncio.create_task(engine.call_chat(
        messages=[{"role": "user", "content": planner_prompt}],
        role="PLANNER",
        task_id=f"{task_id}_planner"
    ))
    
    executor_task = asyncio.create_task(engine.call_chat(
        messages=[{"role": "user", "content": executor_prompt}],
        role="EXECUTOR",
        task_id=f"{task_id}_executor"
    ))

    # Đợi cả hai cùng báo cáo kết quả họp
    planner_res, executor_res = await asyncio.gather(planner_task, executor_task)
    
    # 🛡️ BƯỚC 2: PHẢN BIỆN (CRITIC) TỔNG HỢP & QUYẾT ĐỊNH TỐI THƯỢNG
    critic_prompt = f"""HỘI ĐỒNG ĐANG HỌP BÀN VỀ: {topic}
    
    1. Ý KIẾN QUÂN SƯ (PLANNER):
    {planner_res}
    
    2. Ý KIẾN CHIẾN BINH (EXECUTOR):
    {executor_res}
    
    Dựa trên hai luồng tư duy trên, hãy đưa ra bản KẾ HOẠCH HÀNH ĐỘNG CUỐI CÙNG (Final Decision) tối ưu nhất, an toàn nhất cho hệ thống."""
    
    critic_res = await engine.call_chat(
        messages=[{"role": "user", "content": critic_prompt}],
        role="CRITIC",
        task_id=f"{task_id}_critic"
    )
    
    return {
        "status": "success",
        "answer": critic_res,
        "council_details": {
            "strategy": planner_res,
            "feasibility": executor_res
        },
        "description": "🏛️ Hội đồng Trí tuệ đã thống nhất phương án tác chiến."
    }
