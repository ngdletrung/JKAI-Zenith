import asyncio
import json
from core.utils.engine import engine

async def initiate_agentic_debate(topic: str, task_id: str = "council"):
    """
    🏛️ [JUDICIAL COUNCIL]: Triệu tập Hội đồng Phán quyết để tranh biện đối lập.
    """
    # 🧠 BƯỚC 1: ARCHITECT PHÁC THẢO BLUEPRINT
    architect_prompt = f"""
    Mục tiêu chiến lược: {topic}. 
    Hãy đưa ra bản BLUEPRINT thực thi tối ưu nhất.
    Chú ý: Bản kế hoạch này sẽ bị AUDITOR thẩm định cực kỳ khắt khe.
    """
    
    architect_res = await engine.call_chat(
        messages=[{"role": "user", "content": architect_prompt}],
        role="ARCHITECT",
        task_id=f"{task_id}_architect_v1"
    )

    # 🛡️ BƯỚC 2: AUDITOR TẤN CÔNG (THE SIEGE)
    # Sử dụng 10 câu hỏi Mental OS để tìm điểm gãy
    auditor_prompt = f"""
    DƯỚI ĐÂY LÀ KẾ HOẠCH CỦA ARCHITECT:
    {architect_res}
    
    Nhiệm vụ của bạn (AUDITOR): 
    Sử dụng 10 câu hỏi MENTAL OS (Tại sao làm? Vấn đề thật? Đơn giản nhất? Bottleneck? Điểm gãy? Rollback? Scalability? Metric? Core Value? Maintainability?) 
    để tìm ra ít nhất 3 ĐIỂM YẾU CHÍ MẠNG.
    """
    
    auditor_res = await engine.call_chat(
        messages=[{"role": "user", "content": auditor_prompt}],
        role="AUDITOR",
        task_id=f"{task_id}_auditor"
    )

    # ⚔️ BƯỚC 3: ARCHITECT GIẢI TRÌNH & GIA CỐ (FORTIFICATION)
    final_refinement_prompt = f"""
    AUDITOR ĐÃ CHỈ RA CÁC LỖ HỔNG SAU:
    {auditor_res}
    
    Dựa trên các phản biện này, hãy hoàn thiện BẢN KẾ HOẠCH HÀNH ĐỘNG CUỐI CÙNG.
    Giải trình rõ các điểm Auditor đã nêu và đưa ra giải pháp khắc phục.
    """
    
    final_plan = await engine.call_chat(
        messages=[{"role": "user", "content": final_refinement_prompt}],
        role="ARCHITECT",
        task_id=f"{task_id}_final"
    )
    
    return {
        "status": "success",
        "answer": final_plan,
        "judicial_report": {
            "draft_blueprint": architect_res,
            "auditor_critique": auditor_res
        },
        "description": "🏛️ Hội đồng Phán quyết đã hoàn thành vòng lặp Judicial. Kế hoạch đã được gia cố."
    }
