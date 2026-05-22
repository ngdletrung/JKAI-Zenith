import os
import httpx
import logging

logger = logging.getLogger(__name__)

# =================================================================
# 👁️ JKAI ZENITH: LOGIC THIÊN NHÃN (VISUAL OBSERVATION)
# =================================================================

async def quan_sat_thi_giac(objective: str, url: str = "https://www.google.com", task_id: str = "sys", trace_id: str = "sys"):
    """
    Kích hoạt Thiên Nhãn (Browser Use) để quan sát và tương tác với trang web.
    """
    try:
        from core.utils.engine import engine
        engine.publish_mission_log("BROWSER_OPS", f"👁️ [JKAI-VISION] Đang triển khai Thiên Nhãn tới: `{url}`...", task_id, trace_id)
    except ImportError:
        pass
        
    browser_url = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000/browse")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(browser_url, json={
                "objective": objective,
                "url": url
            })
            
            if resp.status_code == 200:
                data = resp.json()
                analysis = data.get("analysis", "Không có kết quả phân tích.")
                screenshot = data.get("screenshot")
                
                res_msg = f"🔍 [KẾT QUẢ QUAN SÁT]:\n{analysis}"
                if screenshot:
                    res_msg += f"\n📸 [ẢNH CHỤP BẰNG CHỨNG]: /screenshots/{screenshot}"
                
                try:
                    engine.publish_mission_log("BROWSER_OPS", f"✅ [VISION-SUCCESS] Thu thập thành công.\n{res_msg}", task_id, trace_id)
                except: pass
                
                return {"status": "success", "results": res_msg, "data": data}
            else:
                try:
                    engine.publish_mission_log("BROWSER_ERR", f"❌ Lỗi vệ tinh browser: {resp.status_code}", task_id, trace_id)
                except: pass
                
                return {"status": "error", "msg": f"Lỗi vệ tinh browser: {resp.status_code}"}
                
    except Exception as e:
        logger.error(f"Sự cố Thiên Nhãn: {str(e)}")
        try:
            engine.publish_mission_log("BROWSER_ERR", f"❌ Sự cố Thiên Nhãn: {str(e)}", task_id, trace_id)
        except: pass
        
        return {"status": "error", "msg": f"Sự cố Thiên Nhãn: {str(e)}"}
