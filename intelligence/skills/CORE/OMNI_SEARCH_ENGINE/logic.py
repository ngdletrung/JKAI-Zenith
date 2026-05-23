import os
import json
import logging
import asyncio
import httpx

logger = logging.getLogger("JKAI.OmniSearch")

class OmniSearchEngine:
    """
    Skill: omni_search
    Bộ máy tìm kiếm hợp nhất với chiến lược Fallback:
    1. Tavily API (Nhanh, chuyên dụng)
    2. Cloud LLM (Gemini/ChatGPT native search)
    3. AI-Browse (Mở trình duyệt vật lý)
    """
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        
    async def omni_search(self, query: str, mode: str = "fast", **kwargs) -> dict:
        """
        Tìm kiếm Internet an toàn với cơ chế chống lỗi (Quota Exceeded, Timeout).
        """
        logger.info(f"🔍 [OMNI-SEARCH]: Bắt đầu tìm kiếm: '{query}'")
        
        # Thác 1: TAVILY
        if self.tavily_api_key:
            try:
                logger.info("🌊 [OMNI-FALLBACK-1]: Thử dùng Tavily API...")
                tavily_result = await self._search_tavily(query, mode)
                if tavily_result and len(tavily_result.get("results", [])) > 0:
                    logger.info("✅ [OMNI-SEARCH]: Tavily thành công.")
                    return {"status": "success", "source": "tavily", "output": tavily_result}
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                    logger.warning("⚠️ [OMNI-SEARCH]: Tavily hết Quota/Token. Chuyển Fallback.")
                else:
                    logger.warning(f"⚠️ [OMNI-SEARCH]: Tavily lỗi ({e}). Chuyển Fallback.")
        else:
            logger.info("⚠️ [OMNI-SEARCH]: Không tìm thấy TAVILY_API_KEY.")

        # Thác 2: CLOUD LLM (Gemini/OpenAI Native Search)
        try:
            logger.info("☁️ [OMNI-FALLBACK-2]: Thử dùng Cloud LLM Search...")
            cloud_result = await self._search_cloud_llm(query)
            if cloud_result:
                logger.info("✅ [OMNI-SEARCH]: Cloud LLM thành công.")
                return {"status": "success", "source": "cloud_llm", "output": {"content": cloud_result}}
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str:
                logger.warning("⚠️ [OMNI-SEARCH]: Cloud LLM hết Quota/Token. Chuyển Fallback.")
            else:
                logger.warning(f"⚠️ [OMNI-SEARCH]: Cloud LLM lỗi ({e}). Chuyển Fallback.")

        # Thác 3: BROWSER AUTOMATION (ai-browse)
        try:
            logger.info("🌐 [OMNI-FALLBACK-3]: Thử dùng AI-Browse (Vật lý)...")
            from core.utils.registry import registry
            executor_url = registry.get_service_url("executor")
            browse_result = await self._search_browse(query, executor_url)
            if browse_result:
                logger.info("✅ [OMNI-SEARCH]: AI-Browse thành công.")
                return {"status": "success", "source": "ai_browse", "output": {"content": browse_result}}
        except Exception as e:
            logger.error(f"❌ [OMNI-SEARCH]: AI-Browse lỗi ({e}).")

        # Thất bại toàn tập
        return {
            "status": "error", 
            "msg": "Tất cả các nguồn tìm kiếm (Tavily, Cloud LLM, Browser) đều thất bại hoặc hết Quota."
        }

    async def _search_tavily(self, query: str, mode: str) -> dict:
        search_depth = "advanced" if mode == "deep" else "basic"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "max_results": 5
                }
            )
            if resp.status_code == 429:
                raise Exception("429 Quota Exceeded")
            resp.raise_for_status()
            return resp.json()

    async def _search_cloud_llm(self, query: str) -> str:
        """
        Dùng engine.py để hỏi Cloud LLM có kết nối Internet (nếu được hỗ trợ).
        """
        from core.utils.engine import engine
        prompt = (
            f"Vui lòng tìm kiếm trên Internet thông tin mới nhất về: '{query}'. "
            "Trả lời ngắn gọn, chi tiết và chứa các thông tin thời sự/thực tế."
        )
        # Ép dùng is_cloud nếu có thể (engine.call_chat tự động xử lý fallback config)
        answer = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER", # Hoặc role RESEARCHER có kết nối mạng
            task_id="omni_search_internal",
            trace_id="system"
        )
        if isinstance(answer, dict) and "answer" in answer:
            return answer["answer"]
        return str(answer)

    async def _search_browse(self, query: str, executor_url: str) -> str:
        """
        Sử dụng skill mở trình duyệt vật lý để cạo dữ liệu Google.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{executor_url}/tool",
                json={
                    "tool": "ai_browse",
                    "kwargs": {
                        "url": f"https://duckduckgo.com/html/?q={query}",
                        "action": "extract_text"
                    }
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    # Lấy text thô từ browser
                    return str(data.get("output", ""))[:3000]
        raise Exception("Browser automation failed")
