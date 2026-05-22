import os
import sys
import json
import asyncio
import httpx

# Đảm bảo nạp được core engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from core.utils.engine import engine

# =================================================================
# 🔍 JKAI ZENITH: LOGIC NHÀ NGHIÊN CỨU ĐỘC LẬP (AUTONOMOUS RESEARCHER)
# Model được xác định bởi rule_hardware.md (Markdown-as-Authority)
# =================================================================

async def _search_web(query: str):
    """Tìm kiếm nhanh qua Tavily API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tavily.com/search", json={
                "api_key": api_key, "query": query, "search_depth": "advanced"
            })
            return resp.json().get("results", [])[:3]
    except Exception as e:
        print(f"[JKAI-RESEARCH] Tavily error: {e}")
        return []

async def _deep_read(url: str, objective: str):
    """Đọc sâu một trang web qua Jina.ai (không cần Browser Agent)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            if resp.status_code == 200:
                return resp.text[:4000]
    except Exception as e:
        print(f"[JKAI-RESEARCH] Read error for {url}: {e}")
    return None

async def conduct_research(topic: str, task_id: str = None):
    """
    Quy trình nghiên cứu đa tầng:
    1. Search để lấy các nguồn uy tín.
    2. Đọc sâu từng nguồn.
    3. Dùng engine (role PLANNER) để tổng hợp báo cáo chuyên sâu.
    """
    engine.publish_mission_log("RESEARCH_START", f"🔍 [RESEARCH]: Bắt đầu nhiệm vụ tầm soát tri thức: `{topic}`", task_id)

    # Bước 1: Tìm kiếm sơ bộ
    engine.publish_mission_log("RESEARCH_SEARCH", f"📡 [TAVILY]: Đang trinh sát Internet để tìm nguồn dữ liệu...", task_id)
    sources = await _search_web(topic)
    raw_content = []

    # Bước 2: Đọc sâu từng nguồn
    for source in sources:
        url = source.get("url", "")
        engine.publish_mission_log("RESEARCH_READ", f"📄 [RESEARCH]: Đang thấu thị nội dung từ: `{url}`", task_id)
        content = await _deep_read(url, topic)
        if content:
            raw_content.append(f"[Nguồn: {url}]\n{content}")

    if not raw_content:
        # Fallback: Nếu không lấy được web content, dùng AI để phân tích câu hỏi
        raw_content = [f"Không tìm thấy nguồn web cho chủ đề: {topic}. Hãy trả lời dựa trên kiến thức nội bộ."]

    combined = "\n\n---\n\n".join(raw_content)

    synthesis_prompt = f"""Bạn là Nhà Nghiên cứu Độc lập của Tập đoàn JKAI Zenith.
Dựa trên thông tin từ các nguồn sau về chủ đề "{topic}", hãy tổng hợp thành một báo cáo ngắn gọn, chuyên sâu và có cấu trúc rõ ràng (Bối cảnh, Phân tích, Kết luận, Đề xuất).

THÔNG TIN:
{combined[:5000]}

BÁO CÁO NGHIÊN CỨU:"""

    # Bước 3: Tổng hợp qua engine (role PLANNER = tư duy chiến lược)
    engine.publish_mission_log("RESEARCH_SYNTHESIS", f"🧠 [PLANNER]: Đang đúc kết báo cáo nghiên cứu chuyên sâu...", task_id)
    # Model được lấy từ rule_hardware.md — không hardcode
    synthesis = await engine.call_chat(
        messages=[{"role": "user", "content": synthesis_prompt}],
        role="PLANNER",
        task_id=task_id
    )

    if isinstance(synthesis, dict) and "error" in synthesis:
        return {"status": "error", "msg": f"Lỗi kết nối engine: {synthesis['error']}"}

    # Lưu kết quả vào Vault
    from core.config import settings
    safe_name = topic.replace(" ", "_")[:30]
    output_path = os.path.join(settings.INTELLIGENCE_DIR, "vault", f"RESEARCH_{safe_name}.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# BÁO CÁO NGHIÊN CỨU: {topic}\n\n{synthesis}")

    msg = f"Đã hoàn thành nghiên cứu qua {len(raw_content)} nguồn. Báo cáo đã lưu vào Vault."
    engine.publish_mission_log("MISSION_RESULT", synthesis, task_id)
    return {
        "status": "success",
        "topic": topic,
        "sources_read": len(raw_content),
        "report": synthesis,
        "output_file": output_path,
        "msg": msg
    }

if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Kiến trúc Microservices AI hiện đại 2026"
    res = asyncio.run(conduct_research(topic))
    print(json.dumps(res, indent=2, ensure_ascii=True))
