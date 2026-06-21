import os
import sys
import json
import asyncio
import httpx
import re

# 🌐 [PATH-ALIGNMENT]: Đảm bảo kết nối với Lõi Engine
try:
    from core.utils.engine import engine
    from core.kernel.synthesis_engine import synthesis_engine
except ImportError:
    pass

# =================================================================
# 🛰️ JKAI ZENITH: ĐẶC VỤ TRINH SÁT CHIẾN LƯỢC (STRATEGIC RECON v3.0)
# Kết hợp Tư duy Đệ quy (Recursive) và Khám phá Đa nhánh (Multi-branch).
# =================================================================

class SearchBrowseAgent:
    def __init__(self, task_id: str = "search_browse"):
        self.task_id = task_id
        self.browser_url = os.getenv("AI_BROWSER_URL", "http://ai-browser:8000/browse")
        self.breadth = 3 # Số nhánh song song
        self.depth = 2   # Độ sâu đệ quy
        self.collected_data = []

    def _log(self, msg: str):
        try:
            from core.utils.engine import engine
            engine.publish_mission_log("SEARCH_BROWSE", f"📡 [RECURSIVE-RECON]: {msg}", self.task_id)
        except ImportError:
            print(f"📡 [RECURSIVE-RECON]: {msg}")

    async def _call_browser(self, objective: str, url: str):
        """Triệu hồi Vệ tinh Thị giác."""
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(self.browser_url, json={"objective": objective, "url": url})
                data = resp.json().get("analysis", resp.json().get("output", "Không tìm thấy dữ liệu."))
                self.collected_data.append(f"Source: {url}\nObjective: {objective}\nData: {data}")
                return data
        except Exception as e:
            return f"Lỗi Vệ tinh: {e}"

    async def generate_sub_queries(self, goal: str, context: str = ""):
        """🧠 [NEURAL-PLANNING]: Tạo các câu hỏi phụ để mở rộng bề ngang nghiên cứu."""
        prompt = f"""Bạn là Kiến trúc sư Nghiên cứu của JKAI Zenith.
Mục tiêu chính: {goal}
Ngữ cảnh hiện tại: {context}

Hãy tạo ra tối đa {self.breadth} câu hỏi phụ (sub-queries) để đào sâu vào các khía cạnh khác nhau của mục tiêu này.
Yêu cầu trả về JSON: {{"queries": ["query1", "query2", "query3"]}}"""

        response = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            task_id=self.task_id,
            json_mode=True
        )
        
        try:
            if isinstance(response, str):
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    response = json.loads(match.group())
            return response.get("queries", [goal])
        except Exception:
            return [goal]

    async def _recursive_explore(self, query: str, current_depth: int):
        """🌲 [DEPTH-DIVE]: Khám phá đệ quy theo chiều sâu."""
        if current_depth > self.depth:
            return

        self._log(f"Đang đào sâu tầng {current_depth} cho query: `{query}`")
        
        # 1. Tìm kiếm và phân tích trang web đầu tiên tìm được
        # Ở bản này ta giả định gọi browser với query đó, browser sẽ tự tìm link phù hợp
        observation = await self._call_browser(f"Nghiên cứu sâu về: {query}", "https://www.google.com")
        
        # 2. Nếu còn độ sâu, sinh query con từ kết quả vừa tìm được và tiếp tục
        if current_depth < self.depth:
            sub_queries = await self.generate_sub_queries(query, str(observation)[:1000])
            tasks = [self._recursive_explore(q, current_depth + 1) for q in sub_queries]
            await asyncio.gather(*tasks)

    async def execute(self, goal: str):
        self._log(f"🚀 Kích hoạt Giao thức Nghiên cứu Đệ quy: `{goal}`")
        
        # Bước 1: Sinh các nhánh nghiên cứu ban đầu (Breadth)
        initial_queries = await self.generate_sub_queries(goal)
        self._log(f"Phân tách mục tiêu thành {len(initial_queries)} nhánh nghiên cứu.")
        
        # Bước 2: Thực thi song song các nhánh (Depth)
        tasks = [self._recursive_explore(q, 1) for q in initial_queries]
        await asyncio.gather(*tasks)
        
        # Bước 3: Tổng hợp (Synthesis)
        self._log("🧬 Đang tổng hợp dữ liệu từ tất cả các nhánh...")
        report = await synthesis_engine.synthesize(goal, self.collected_data)
        
        return report

async def run_search_browse(goal: str, task_id: str = "search_browse", trace_id: str = "sys"):
    agent = SearchBrowseAgent(task_id)
    result = await agent.execute(goal)
    return {"status": "success", "report": result}

if __name__ == "__main__":
    goal = sys.argv[1] if len(sys.argv) > 1 else "Kiến trúc OpenHands AI"
    asyncio.run(run_search_browse(goal))
