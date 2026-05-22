import os
import sys
import json
import asyncio
import httpx
import re

# 🌐 [PATH-ALIGNMENT]: Đảm bảo kết nối với Lõi Engine
try:
    from core.utils.engine import engine
except ImportError:
    pass

# =================================================================
# 🛰️ JKAI ZENITH: ĐẶC VỤ TRINH SÁT CHIẾN LƯỢC (STRATEGIC RECON v2.0)
# Kết hợp Tư duy Đệ quy và Vệ tinh Thị giác (ai-browser).
# =================================================================

class SearchBrowseAgent:
    def __init__(self, task_id: str = "search_browse"):
        self.task_id = task_id
        self.browser_url = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000/browse")
        self.history = []

    def _log(self, msg: str):
        try:
            from core.utils.engine import engine
            engine.publish_mission_log("SEARCH_BROWSE", f"📡 [SEARCH-BROWSE]: {msg}", self.task_id)
        except ImportError:
            print(f"📡 [SEARCH-BROWSE]: {msg}")

    async def _call_browser(self, objective: str, url: str):
        """Triệu hồi Vệ tinh Thị giác."""
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(self.browser_url, json={"objective": objective, "url": url})
                return resp.json().get("analysis", resp.json().get("output", "Không tìm thấy dữ liệu thị giác."))
        except Exception as e:
            return f"Lỗi Vệ tinh: {e}"

    async def execute(self, goal: str):
        self._log(f"Khởi động Giao thức SearchBrowse: `{goal}`")
        
        current_context = ""
        iteration = 0
        max_iterations = 4 # Nâng giới hạn để tìm kiếm sâu hơn

        from core.utils.engine import engine

        while iteration < max_iterations:
            iteration += 1
            self._log(f"Vòng tư duy thứ {iteration}/{max_iterations}...")

            # 🧠 [NEURAL-ANALYSIS]: Hỏi Planner xem bước tiếp theo nên làm gì
            analysis_prompt = f"""Bạn là Đặc vụ SearchBrowse Tối cao của JKAI Zenith. 
Mục tiêu của Master: {goal}
Dữ liệu đã thu thập được: {current_context}

Hãy phân tích xem chúng ta đã đủ thông tin chưa. 
Nếu CHƯA ĐỦ, hãy quyết định hành động tiếp theo trên web. Bạn phải cung cấp 'objective' (nhiệm vụ cần làm trên trang web) và 'url' (địa chỉ trang web cần truy cập).
(Ví dụ: url="https://www.google.com", objective="Tìm kiếm giá Bitcoin mới nhất")
Nếu ĐÃ ĐỦ, hãy bắt đầu bằng từ 'COMPLETE' trong action và viết báo cáo tổng hợp.

Yêu cầu trả về JSON chuẩn xác: {{"thought": "suy nghĩ của bạn", "action": "SEARCH/FINALIZE", "url": "...", "objective": "...", "report": "báo cáo nếu đã đủ thông tin"}}"""

            decision = await engine.call_chat(
                messages=[{"role": "user", "content": analysis_prompt}],
                role="PLANNER",
                task_id=self.task_id,
                json_mode=True
            )

            # Parse JSON decision
            try:
                if isinstance(decision, str):
                    match = re.search(r'\{.*\}', decision, re.DOTALL)
                    if match:
                        decision = json.loads(match.group())
                    else:
                        decision = {"action": "SEARCH", "objective": goal, "url": "https://www.google.com"}
            except:
                self._log("⚠️ Lỗi phân tích tư duy. Tự động kết thúc.")
                break

            if "COMPLETE" in decision.get("action", "") or decision.get("report"):
                self._log("✅ [SEARCH-BROWSE]: Nhiệm vụ hoàn tất. Đang đúc kết báo cáo.")
                return decision.get("report", "Nhiệm vụ trinh sát hoàn thành.")

            # 🚀 [ACTION]: Triệu hồi Browser
            obj = decision.get("objective", goal)
            url = decision.get("url", "https://www.google.com")
            self._log(f"👁️ Đang trinh sát thị giác tại [{url}]: `{obj}`")
            
            observation = await self._call_browser(obj, url)
            
            # Cập nhật context
            current_context += f"\n--- Step {iteration} (URL: {url}) observation ---\n{observation}\n"
            self.history.append({"step": iteration, "url": url, "objective": obj, "observation": str(observation)[:500] + "..."})

        return "Nhiệm vụ kết thúc sau khi đạt giới hạn vòng lặp."

async def run_search_browse(goal: str, task_id: str = "search_browse", trace_id: str = "sys"):
    agent = SearchBrowseAgent(task_id)
    result = await agent.execute(goal)
    return {"status": "success", "report": result}

if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else "Tìm hiểu về tình hình AI năm 2026"
    asyncio.run(run_search_browse(goal))
