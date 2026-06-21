# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/RESEARCH/AUTONOMOUS_WEB_RECON/logic.py
# - Role: Autonomous Multi-Step Web Research Agent
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0 (OpenHands Inspired)
# [WORKING PRINCIPLES]:
# 1. Self-correcting loop for complex research objectives.
# 2. Uses CloakBrowser Satellite for stealth navigation.
# 3. Reports every 'Thought-Action-Observation' triplet to the Event-Stream.
# -----------------------------------------------------------------------------
import os
import httpx
import json
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    objective = params.get("objective", "")
    url = params.get("url", "https://www.google.com")
    task_id = params.get("task_id", "recon_" + str(int(time.time())))
    trace_id = params.get("trace_id", "trace_" + str(int(time.time())))

    from core.utils.engine import engine

    engine.publish_mission_log(
        "RECON", 
        f"🚀 [TRINH SÁT TỰ TRỊ]: Bắt đầu nhiệm vụ trinh sát mục tiêu: `{objective}`", 
        task_id, trace_id
    )

    # 📡 [SATELLITE-LINK]: Gọi ai-browser service
    browser_url = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000/browse")
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Gửi yêu cầu tới Browser Satellite
            # Note: Browser Satellite đã tích hợp autonomous agent bên trong (browser-use)
            payload = {
                "objective": objective,
                "url": url,
                "headless": True
            }
            
            start_time = time.time()
            resp = await client.post(browser_url, json=payload)
            duration = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                analysis = data.get("analysis", "")
                screenshot = data.get("screenshot", "")
                
                # 🥋 [JUJUTSU-TRACKING]: Ghi lại quỹ đạo
                try:
                    from intelligence.skills.CORE.skill_agentic_jujutsu.logic import track_trajectory
                    await track_trajectory(
                        action=f"Reconnaissance on {url}",
                        state_before={"objective": objective},
                        state_after={"analysis": analysis, "duration": f"{duration:.2f}s"},
                        agent="AutonomousWebRecon"
                    )
                except Exception as e:
                    logger.warning(f"Jujutsu tracking failed: {e}")

                engine.publish_mission_log(
                    "RECON", 
                    f"✅ [HOÀN TẤT]: Trinh sát hoàn tất sau {duration:.2f}s.\n\n**Kết quả phân tích:**\n{analysis}", 
                    task_id, trace_id
                )
                
                return {
                    "status": "success",
                    "objective": objective,
                    "analysis": analysis,
                    "screenshot": screenshot,
                    "duration": duration
                }
            else:
                error_msg = f"Browser Satellite returned error: {resp.status_code}"
                engine.publish_mission_log("ERROR", f"❌ [TRINH SÁT THẤT BẠI]: {error_msg}", task_id, trace_id)
                return {"status": "error", "msg": error_msg}
                
    except Exception as e:
        engine.publish_mission_log("ERROR", f"❌ [TRINH SÁT LỖI HỆ THỐNG]: {str(e)}", task_id, trace_id)
        return {"status": "error", "msg": str(e)}

async def search_and_analyze(query: str, task_id: str = "sys", trace_id: str = "sys") -> Dict[str, Any]:
    """Hàm wrapper cho Dispatcher gọi trực tiếp."""
    return await execute({"objective": query, "task_id": task_id, "trace_id": trace_id})
