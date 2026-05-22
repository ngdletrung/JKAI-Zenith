import os
import httpx
import logging
import asyncio
from core.utils.engine import engine

logger = logging.getLogger("jkai.neural_eye")

async def capture_vision(url: str, task_id: str = "vision"):
    """
    👁️ [NEURAL-EYE] - Kích hoạt thị giác vệ tinh
    """
    browser_url = os.getenv("BROWSER_URL", "http://ai-browser:8000/screenshot")
    
    engine.publish_mission_log("EYE", f"👁️ [EYE-ACTIVATE]: Đang yêu cầu Vệ tinh chụp ảnh thực địa: {url}", task_id)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(browser_url, json={"url": url, "objective": "Visual Audit"})
            
            if resp.status_code == 200:
                data = resp.json()
                filename = data.get("filename")
                engine.publish_mission_log("EYE", f"✅ [EYE-SUCCESS]: Đã chụp ảnh thành công. Tệp tin: `{filename}`", task_id)
                
                # 📡 [QUANTUM-LEAP]: Triệu hồi Trí tuệ Thị giác (Vision Analysis)
                vision_url = browser_url.replace("/screenshot", "/vision")
                engine.publish_mission_log("EYE", "🧠 [EYE-ANALYSIS]: Đang tiến hành Audit thị giác thực địa...", task_id)
                
                prompt = "Analyze this interface. Is everything working correctly? Are there any errors, overlapping elements, or broken UI components? Focus on system stability."
                
                vision_resp = await client.post(vision_url, json={
                    "image_path": filename,
                    "prompt": prompt
                })
                
                analysis = "Mắt Thần không thể phân tích nội dung hình ảnh vào lúc này."
                if vision_resp.status_code == 200:
                    analysis = vision_resp.json().get("analysis", analysis)
                    engine.publish_mission_log("EYE", f"📊 [EYE-REPORT]: {analysis}", task_id)
                
                return {
                    "status": "success",
                    "image": filename,
                    "url": url,
                    "audit_report": analysis,
                    "msg": "Mắt Thần đã chụp ảnh và Audit thành công."
                }
            else:
                raise Exception(f"Satellite phản hồi lỗi: {resp.status_code}")
                
    except Exception as e:
        logger.error(f"[EYE-LOGIC-ERR] {e}")
        engine.publish_mission_log("EYE", f"❌ [EYE-FAIL]: Không thể kích hoạt thị giác: {e}", task_id)
        return {"status": "error", "msg": str(e)}

async def skill_neural_eye(**kwargs):
    url = kwargs.get("url", "http://host.docker.internal:9999")
    task_id = kwargs.get("task_id", "vision")
    return await capture_vision(url, task_id)
