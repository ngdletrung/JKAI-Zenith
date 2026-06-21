# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/RESEARCH/AUTONOMOUS_RESEARCHER/logic.py
# - Role: Core Cognitive Logic for AUTONOMOUS_RESEARCHER
# - Status: Optimized | Version: Zenith v9.9 thieu Master
# -----------------------------------------------------------------------------
import os
import sys
import json
import asyncio
import httpx
import logging
from typing import Optional, List, Dict, Any

# Dam bao nap duoc cac module tu core (Di len 5 cap tu intelligence/skills/RESEARCH/AUTONOMOUS_RESEARCHER/logic.py)
SYS_PATH_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if SYS_PATH_DIR not in sys.path:
    sys.path.append(SYS_PATH_DIR)

from core.utils.engine import engine
from core.utils import report_formatter as rf

log = logging.getLogger("JKAI.AutonomousResearcher")


def _clean_query(query: Any) -> str:
    if not query:
        return ""
    if isinstance(query, dict):
        for key in ["query", "q", "extracted_params", "description", "value"]:
            if val := query.get(key):
                return _clean_query(val)
        if len(query) == 1:
            return _clean_query(list(query.values())[0])
        return json.dumps(query)
    if isinstance(query, list):
        if len(query) > 0:
            return _clean_query(query[0])
        return ""
    if isinstance(query, str):
        query_str = query.strip()
        if query_str.startswith("{") and query_str.endswith("}"):
            try:
                parsed = json.loads(query_str)
                return _clean_query(parsed)
            except Exception:
                pass
        return query_str
    return str(query)


async def _search_web(query: str) -> List[Dict[str, Any]]:
    """Tim kiem nhanh qua SEARCH_WEB_GLOBAL (da toi uu hoa BM25-CP & FactVerifier)."""
    try:
        from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import SEARCH_WEB_GLOBAL
        res = await SEARCH_WEB_GLOBAL(query)
        if res.get("status") == "success":
            return res.get("results", [])
    except Exception as e:
        log.error(f"[JKAI-RESEARCH] SEARCH_WEB_GLOBAL error: {e}")
    
    # Fallback to raw Tavily search if import fails or returns error
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    query = _clean_query(query)
    if not query:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.tavily.com/search", json={
                "api_key": api_key, "query": query, "search_depth": "advanced"
            })
            resp.raise_for_status()
            return resp.json().get("results", [])[:3]
    except Exception as e:
        log.error(f"[JKAI-RESEARCH] Tavily fallback error: {e}")
        return []


async def _deep_read(url: str, objective: str) -> Optional[str]:
    """
    Doc sau mot trang web qua Crawl4AI (uu tien hang dau) hoac Jina.ai (du phong),
    phan manh phan cap va xep hang BM25-CP de loc ra cac doan van ban chat luong nhat thieu Master.
    """
    # 1. Dung Crawl4AI de cao du lieu thuan va tu do thieu Master
    try:
        from intelligence.skills.CORE.duyet_browse_zenith.logic import ai_browse
        browse_res = await ai_browse(url=url, action="extract_text")
        if browse_res.get("status") == "success" and browse_res.get("output"):
            full_text = browse_res["output"]
            try:
                from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import chunk_and_rank_segments
                ranked_content = chunk_and_rank_segments(objective, full_text, chunk_size=800, max_segments=4)
                if ranked_content:
                    return ranked_content
            except Exception as ex:
                log.error(f"[JKAI-RESEARCH] Chunk/Rank error with Crawl4AI content: {ex}")
            return full_text[:4000]
    except Exception as e:
        log.error(f"[JKAI-RESEARCH] Crawl4AI extraction failed in researcher: {e}")

    # 2. Du phong: Doc qua Jina.ai
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            if resp.status_code == 200:
                full_text = resp.text
                if not full_text:
                    return None
                    
                # Ap dung chunk_and_rank_segments de lay top 4 doan van ban toi uu nhat thua Master
                try:
                    from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import chunk_and_rank_segments
                    ranked_content = chunk_and_rank_segments(objective, full_text, chunk_size=800, max_segments=4)
                    if ranked_content:
                        return ranked_content
                except Exception as ex:
                    log.error(f"[JKAI-RESEARCH] Chunk/Rank error, using fallback slice: {ex}")
                
                return full_text[:4000]
    except Exception as e:
        log.error(f"[JKAI-RESEARCH] Read error for {url}: {e}")
    return None


async def conduct_research(topic: str, task_id: str = None) -> Dict[str, Any]:
    """
    Quy trình nghien cuu da tang thong minh thua Master:
    1. Goi sieu tim kiem SEARCH_WEB_GLOBAL de thu thap nguon tin da duoc xep hang.
    2. Doc sau va chat loc cac phan doan qua BM25-CP doi voi tung trang web.
    3. Su dung FactVerifier doi chieu cheo de phat hien bat dong thuan va xung dot ky thuat.
    4. Gui bao cao hoan chinh duoc gan chan trang trich dan chi tiet toi LLM PLANNER.
    """
    engine.publish_mission_log("RESEARCH_START", f"🔍 [RESEARCH]: Bắt đầu nhiệm vụ tầm soát tri thức: `{topic}`", task_id)

    # Buoc 1: Tim kiem so bo
    engine.publish_mission_log("RESEARCH_SEARCH", f"📡 [TAVILY]: Đang trinh sát Internet để tìm nguồn dữ liệu...", task_id)
    sources = await _search_web(topic)
    raw_content = []
    candidates = []

    # Buoc 2: Doc sau tung nguon
    for source in sources:
        url = source.get("url", "")
        if not url or "ranked.internal" in url:
            continue
        engine.publish_mission_log("RESEARCH_READ", f"📄 [RESEARCH]: Đang thấu thị nội dung từ: `{url}`", task_id)
        content = await _deep_read(url, topic)
        if content:
            raw_content.append(f"[Nguồn: {url}]\n{content}")
            candidates.append({"url": url, "content": content})

    if not raw_content:
        raw_content = [f"Không tìm thấy nguồn web cho chủ đề: {topic}. Hãy trả lời dựa trên kiến thức nội bộ."]

    combined = "\n\n---\n\n".join(raw_content)

    # Buoc 3: Dong thuan va Doi chieu cheo (FactVerifier) thua Master
    contradiction_footer = ""
    try:
        from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import FactVerifier
        if candidates:
            verifier = FactVerifier()
            v_data = verifier.verify_and_detect_contradictions(candidates)
            if v_data["contradiction_warnings"]:
                warn_msg = "⚠️ [FACT-CONFLICTS] Phát hiện mâu thuẫn kỹ thuật giữa các trang web:\n" + "\n".join(v_data["contradiction_warnings"][:3])
                engine.publish_mission_log("RESEARCH_WARN", warn_msg, task_id)
                contradiction_footer = rf.build([
                    rf.section("Canh bao mau thuan ky thuat phat hien tu cac nguon tin (FactVerifier)", 3),
                    rf.bullet(v_data["contradiction_warnings"][:5]),
                ])
    except Exception as e:
        log.error(f"[JKAI-RESEARCH] FactVerifier error: {e}")

    # Dinh kem danh sach trich dan Perplexity-style thua Master
    seen_urls = set()
    citation_items = []
    idx = 1
    for s in sources:
        url = s.get("url")
        if not url or url in seen_urls or "ranked.internal" in url:
            continue
        seen_urls.add(url)
        title = s.get("title") or "Nguồn tin"
        if len(title) > 60:
            title = title[:57] + "..."
        citation_items.append(f"**[{idx}]** [{title}]({url})")
        idx += 1
    citations_footer = rf.build([
        rf.section("Nguon trich dan thong tin", 3),
        rf.bullet(citation_items),
    ]) if citation_items else ""

    synthesis_prompt = f"""Bạn là Nhà Nghiên cứu Độc lập của Tập đoàn JKAI Zenith.
Dựa trên thông tin từ các nguồn sau về chủ đề "{topic}", hãy tổng hợp thành một báo cáo ngắn gọn, chuyên sâu và có cấu trúc rõ ràng (Bối cảnh, Phân tích, Kết luận, Đề xuất).
Trình bày kết quả theo format chuẩn: dùng ## cho section header, bảng markdown (| cột1 | cột2 |) cho dữ liệu, --- cho separator, gạch đầu dòng cho danh sách.

THÔNG TIN:
{combined[:6000]}

BÁO CÁO NGHIÊN CỨU:"""

    # Buoc 4: Tong hop qua engine (role PLANNER = tu duy chien luoc)
    engine.publish_mission_log("RESEARCH_SYNTHESIS", f"🧠 [PLANNER]: Đang đúc kết báo cáo nghiên cứu chuyên sâu...", task_id)
    synthesis = await engine.call_chat(
        messages=[{"role": "user", "content": synthesis_prompt}],
        role="PLANNER",
        task_id=task_id
    )

    if isinstance(synthesis, dict) and "error" in synthesis:
        return {"status": "error", "msg": f"Lỗi kết nối engine: {synthesis['error']}"}

    synthesis_rich = str(synthesis).strip()
    report_parts = [synthesis_rich]
    if contradiction_footer:
        report_parts.append(contradiction_footer)
    if citations_footer:
        report_parts.append(citations_footer)
    final_report = rf.build(report_parts)

    # Luu ket qua vao Vault
    from core.config import settings
    safe_name = topic.replace(" ", "_")[:30]
    output_path = os.path.join(settings.INTELLIGENCE_DIR, "vault", f"RESEARCH_{safe_name}.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rf.build([
            rf.header(f"BAO CAO NGHIEN CUU: {topic}"),
            final_report,
        ]))

    msg = f"Đã hoàn thành nghiên cứu qua {len(raw_content)} nguồn. Báo cáo đã lưu vào Vault."
    engine.publish_mission_log("MISSION_RESULT", final_report, task_id)
    return {
        "status": "success",
        "topic": topic,
        "sources_read": len(raw_content),
        "report": synthesis_rich,
        "output_file": output_path,
        "msg": msg
    }


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "Kiến trúc Microservices AI hiện đại 2026"
    res = asyncio.run(conduct_research(topic))
    print(json.dumps(res, indent=2, ensure_ascii=True))
