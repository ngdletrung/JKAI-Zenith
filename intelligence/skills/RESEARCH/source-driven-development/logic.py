import logging
import time
from core.utils.engine import engine
from intelligence.skills.RESEARCH.SEARCH_WEB_GLOBAL.logic import search_web

log = logging.getLogger("SOURCE_DRIVEN_DEVELOPMENT")

async def run_source_driven_development(query: str, task_id: str = "sys", trace_id: str = "system") -> dict:
    """
    Sovereign Source-Driven Development: Validates code patterns against official documentation.
    """
    engine.publish_mission_log(
        "SOURCE_DRIVEN", f"📚 [SOURCE-DRIVEN]: Tra cứu tài liệu chính thức cho từ khóa: `{query}`...", task_id, trace_id
    )
    t0 = time.time()
    
    # Force search official docs
    search_query = f"official documentation {query}"
    try:
        res = await search_web(query=search_query, task_id=task_id, trace_id=trace_id)
        status = res.get("status", "error")
        content = res.get("answer", "Không tìm thấy tài liệu hướng dẫn.")
    except Exception as e:
        status = "error"
        content = f"Lỗi tra cứu tài liệu: {e}"
        
    latency = (time.time() - t0) * 1000
    
    return {
        "status": status,
        "content": content,
        "latency_ms": latency
    }
