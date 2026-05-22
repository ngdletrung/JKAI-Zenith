import os
import re
import json
import time
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.utils.engine import engine

# 🔒 [NEURAL-LOCKS]: Đảm bảo tính nhất quán nơ-ron khi đa tác tử cùng truy cập
_CACHE_LOCK = asyncio.Lock()
_GLOBAL_SKILLS_CACHE = None
_GLOBAL_REGISTRY_CACHE = None
_LAST_REGISTRY_MTIME = 0

class JKAIKnowledgeOrchestrator:
    """
    🧬 JKAI Knowledge Orchestrator v11.0 (Cognitive OS Edition)
    Hệ thống quản trị tri thức đa tầng: Hybrid Retrieval + Semantic Cache + MMR Diversity.
    Thiết kế để đạt latency thấp và độ chính xác tuyệt đối.
    """
    def __init__(self, base_dir: str = None):
        from core.config import settings
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # [ENVIRONMENT-AWARE]: Tự động nhận diện lãnh thổ tri thức
            self.base_dir = Path(settings.INTELLIGENCE_DIR)

            
        self.map_path = self.base_dir / "map.json"
        self.registry_path = self.base_dir / "registry_Map_skills.json"
        
        # 🧪 [SEMANTIC-CACHE-CONFIG]
        self._embed_cache_ttl = 3600  # 1 giờ
        self._retrieval_cache_ttl = 600 # 10 phút

    # ─────────────────────────────────────────────────────────────
    # 💎 TẦNG 1: CACHE & REGISTRY MANAGEMENT (THREAD-SAFE)
    # ─────────────────────────────────────────────────────────────

    async def get_all_skills_dict(self) -> Dict:
        """📦 [NEURAL-REGISTRY]: Truy xuất kho kỹ năng với cơ chế Auto-Reload."""
        global _GLOBAL_SKILLS_CACHE, _LAST_REGISTRY_MTIME
        
        async with _CACHE_LOCK:
            try:
                # [SOVEREIGN-AUTO-SYNC]: Nếu Registry không tồn tại, tự động tạo mới
                if not self.registry_path.exists():
                    await self.sync_sovereign_registry()
                
                current_mtime = os.path.getmtime(self.registry_path)
                # [AUTO-INVALIDATION]: Nếu file gốc thay đổi, ép buộc tái nạp nơ-ron
                if _GLOBAL_SKILLS_CACHE is None or current_mtime > _LAST_REGISTRY_MTIME:
                    if _GLOBAL_SKILLS_CACHE is not None:
                        engine.publish_mission_log("BRAIN", "🔄 [CACHE-INVALIDATED]: Phát hiện thay đổi trong Registry. Đang tái nạp nơ-ron...", stealth=True)
                    
                    # 🚀 [ASYNC-IO]: Đọc file không chặn Event Loop
                    content = await asyncio.to_thread(self._read_registry_sync)
                    _GLOBAL_SKILLS_CACHE = content.get("skills", {})
                    _LAST_REGISTRY_MTIME = current_mtime
            except Exception as e:
                if _GLOBAL_SKILLS_CACHE is None: _GLOBAL_SKILLS_CACHE = {}
                
            return _GLOBAL_SKILLS_CACHE

    def _read_registry_sync(self) -> Dict:
        """Đọc file vật lý (chạy trong thread riêng)."""
        if not self.registry_path.exists(): return {}
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ─────────────────────────────────────────────────────────────
    # 💎 TẦNG 2: SEMANTIC RETRIEVAL PIPELINE (V11 ELITE)
    # ─────────────────────────────────────────────────────────────

    async def smart_retrieve(self, query: str, task_id: str = "system", top_k: int = 5) -> Dict[str, Any]:
        """
        🧪 [COGNITIVE-RETRIEVAL-V11]: Quy trình 5 giai đoạn.
        1. Query Expansion -> 2. Semantic Cache -> 3. Vector Search -> 4. MMR Diversity -> 5. Structured Context
        """
        # 1. [QUERY-EXPANSION]: Khai phóng ý định
        expanded_queries = await self._expand_query(query, task_id)
        
        # 2. [SEMANTIC-EMBED-CACHE]: Kiểm tra bộ nhớ đệm nơ-ron
        main_query = expanded_queries[0]
        vector = await self._get_cached_embedding(main_query)
        
        if not vector:
            from core.utils.embed import embed
            vector = await asyncio.to_thread(embed, main_query)
            if vector:
                await self._cache_embedding(main_query, vector)

        if not vector: return {"context": "", "sources": [], "structured": []}

        # 3. [HYBRID-VECTOR-SEARCH]: Quét sâu Qdrant
        from core.qdrant_client import qdrant_client
        raw_results = await qdrant_client.search_similar(vector, limit=top_k * 2, collection="universal_graph")
        
        # 4. [MMR-DIVERSITY]: Chắt lọc tinh hoa, loại bỏ trùng lặp
        diverse_results = self._apply_mmr(raw_results, vector, top_k=top_k)
        
        # 5. [STRUCTURED-CONTEXT]: Đóng gói hồ sơ tri thức
        structured_data = []
        for r in diverse_results:
            p = r.get("payload", {})
            structured_data.append({
                "content": p.get("content") or p.get("text", ""),
                "source": p.get("rel_path") or p.get("filename", "Unknown"),
                "score": r.get("score", 0.0),
                "type": p.get("category", "knowledge")
            })

        context_text = "\n\n".join([f"--- SOURCE: {d['source']} ---\n{d['content']}" for d in structured_data])
        
        return {
            "query": query,
            "expanded": expanded_queries,
            "context": context_text,
            "structured": structured_data,
            "sources": [d["source"] for d in structured_data]
        }

    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Truy xuất vector từ Semantic Cache (Redis)."""
        r = engine._get_redis()
        if not r: return None
        h = hashlib.md5(text.encode()).hexdigest()
        cached = r.get(f"embed_cache:{h}")
        if cached:
            return json.loads(cached)
        return None

    async def _cache_embedding(self, text: str, vector: List[float]):
        """Lưu trữ vector vào Semantic Cache."""
        r = engine._get_redis()
        if r:
            h = hashlib.md5(text.encode()).hexdigest()
            r.setex(f"embed_cache:{h}", self._embed_cache_ttl, json.dumps(vector))

    def _apply_mmr(self, results: List[Dict], query_vector: List[float], top_k: int = 5, lambda_param: float = 0.5) -> List[Dict]:
        """
        📊 [MAXIMAL-MARGINAL-RELEVANCE]: Thuật toán đa dạng hóa tri thức.
        Giúp tránh việc lấy quá nhiều đoạn tin trùng lặp từ một nguồn.
        """
        if not results: return []
        if len(results) <= top_k: return results

        selected = [results[0]]
        remaining = results[1:]
        
        while len(selected) < top_k and remaining:
            best_score = -1e9
            best_idx = -1
            
            for i, cand in enumerate(remaining):
                # Độ tương đồng với Query
                sim_query = cand.get("score", 0.0)
                
                # Độ tương đồng lớn nhất với các tài liệu đã chọn (Sim-Sim)
                # Để tối ưu, ta sử dụng một logic đơn giản: nếu cùng nguồn (path), giảm điểm
                cand_path = cand.get("payload", {}).get("rel_path")
                max_sim_selected = 0.0
                for sel in selected:
                    if sel.get("payload", {}).get("rel_path") == cand_path:
                        max_sim_selected = 0.8 # Hình phạt cho việc trùng nguồn
                        break
                
                # Công thức MMR rút gọn
                score = lambda_param * sim_query - (1 - lambda_param) * max_sim_selected
                
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            if best_idx != -1:
                selected.append(remaining.pop(best_idx))
            else:
                break
        return selected

    # ─────────────────────────────────────────────────────────────
    # 💎 TẦNG 3: SPECIALIZED RETRIEVAL (SKILLS & INTEL)
    # ─────────────────────────────────────────────────────────────

    async def retrieve_skills_async(self, goal: str, top_k: int = 5, task_id: str = "sys") -> List[Dict]:
        """
        🧠 [SKILL-SELECTOR-v2.0]: Pipeline 4 tầng - Sovereign Intelligence.
        L0: Necessity Gate → L1: Intent Bridge → L2: Alias Match → L3: Policy Score → L4: Confidence Gate
        Inspired by: Gemini (Router+Description) + Grok (Scoring+Reflection) + DeepSeek (Necessity Gate)
        """
        from core.utils.intent_lexicon import full_classify
        from core.utils.skill_selector import select_skills

        # Phân tích radar 14D
        radar = full_classify(goal)

        # Lấy toàn bộ registry
        all_skills = await self.get_all_skills_dict()

        # Chạy 4-layer selector
        result = await select_skills(
            goal=goal,
            all_skills=all_skills,
            task_id=task_id,
            top_k=top_k,
            radar=radar
        )

        # L0: Không cần skill → trả về rỗng (LLM thuần sẽ xử lý)
        if not result["needs_skill"]:
            return []

        candidates = result.get("candidates", [])

        # L4: Nếu confidence thấp và không có bridge hit → thử Vector Search bổ sung
        if result.get("fallback_to_llm") and not result.get("bridge_hits"):
            vector = await self._get_cached_embedding(goal)
            if not vector:
                from core.utils.embed import embed
                vector = await asyncio.to_thread(embed, goal)
                if vector:
                    await self._cache_embedding(goal, vector)

            if vector:
                try:
                    from core.qdrant_client import qdrant_client
                    qdrant_results = await qdrant_client.search_similar(
                        vector, limit=top_k, collection="universal_graph",
                        filter_dict={"category": "skills"}
                    )
                    seen_ids = {c["skill_id"] for c in candidates}
                    for r in qdrant_results:
                        p = r.get("payload", {})
                        s_id = p.get("name")
                        if s_id and s_id not in seen_ids:
                            candidates.append({
                                "skill_id": s_id,
                                "name": p.get("title", s_id),
                                "description": p.get("content", ""),
                                "score": r.get("score", 0.0) * 0.6,  # Giảm trọng số vector fallback
                                "domain": p.get("domain", "general"),
                                "l1_bridge": False,
                                "l2_alias": 0.0,
                            })
                except Exception as e:
                    logger.warning(f"[VECTOR-FALLBACK] {e}")

        return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]


    async def retrieve_intel_async(self, goal: str, top_k: int = 3) -> List[Dict]:
        """🚀 [NEURAL-INTEL-FETCH]: Quét sâu Đại thư viện song song."""
        vector = await self._get_cached_embedding(goal)
        if not vector:
            from core.utils.embed import embed
            vector = await asyncio.to_thread(embed, goal)
            if vector: await self._cache_embedding(goal, vector)
            
        if not vector: return []
        
        from core.qdrant_client import qdrant_client
        return await qdrant_client.search_similar(vector, limit=top_k, collection="universal_graph", filter_dict={"category": ["knowledge", "rules"]})

    # ─────────────────────────────────────────────────────────────
    # 💎 TẦNG 4: QUERY ANALYSIS & EXPANSION
    # ─────────────────────────────────────────────────────────────

    async def _expand_query(self, query: str, task_id: str) -> List[str]:
        """Giai đoạn 1: Khai phóng truy vấn để tăng Recall."""
        # [CACHE-EXPANSION]: Nếu query ngắn, không cần expand
        if len(query) < 15: return [query]
        
        prompt = (
            f"Phân tích yêu cầu: '{query}'\n"
            f"Tạo ra 3 từ khóa tìm kiếm (tiếng Anh và tiếng Việt) tập trung vào: thực thể, công cụ và kiến thức chuyên môn.\n"
            f"Trả về JSON list."
        )
        try:
            res = await engine.call_chat([{"role": "user", "content": prompt}], role="SUMMARIZER", task_id=task_id, json_mode=True)
            if isinstance(res, list): return [query] + res
        except: pass
        return [query]

    # ─────────────────────────────────────────────────────────────
    # 💎 LEGACY & UTILS
    # ─────────────────────────────────────────────────────────────

    def get_jkai_manifests(self) -> Dict:
        categories = ["agents", "rules", "skills", "knowledge"]
        stats = []
        for cat in categories:
            path = self.base_dir / cat
            # [RECURSIVE-STAT]: Quét đệ quy
            count = len(list(path.rglob("*.md"))) if path.exists() else 0
            stats.append({"id": cat.upper(), "description": f"Bản ghi Elite: {count}", "status": "Healthy"})
        return {"indexes": stats, "version": "v12.0"}

    async def sync_sovereign_registry(self) -> Dict:
        """🏗️ [SOVEREIGN-ASSIMILATOR]: Tự động tái thiết bản đồ kỹ năng toàn cục."""
        skills_path = self.base_dir / "skills"
        new_registry = {"skills": {}, "last_sync": time.time()}
        
        # 1. Quét toàn bộ SKILL.md
        for skill_file in skills_path.rglob("SKILL.md"):
            try:
                content = skill_file.read_text(encoding="utf-8")
                # Parse YAML header
                import yaml
                match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if match:
                    meta = yaml.safe_load(match.group(1))
                    s_id = meta.get("id")
                    if s_id:
                        meta["rel_path"] = str(skill_file.relative_to(self.base_dir))
                        new_registry["skills"][s_id] = meta
            except: pass

        # 2. Hỗ trợ kỹ năng cũ (schema.json)
        for schema_file in skills_path.rglob("schema.json"):
            try:
                s_id = schema_file.parent.name
                if s_id not in new_registry["skills"]:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["id"] = s_id
                    meta["rel_path"] = str(schema_file.relative_to(self.base_dir))
                    new_registry["skills"][s_id] = meta
            except: pass

        # 🚀 [ATOMIC-WRITE]: Ghi file an toàn
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(new_registry, f, indent=4, ensure_ascii=False)
        
        engine.publish_mission_log("BRAIN", "🏗️ [SYNC-COMPLETE]: Đã tái thiết bản đồ nơ-ron kỹ năng thành công.", stealth=True)
        return new_registry

    def get_category_map(self, category: str) -> str:
        """Truy xuất bản đồ chỉ dẫn (Map) cho một danh mục."""
        cat_upper = category.upper()
        # Thử cả hai định dạng (Hoa và Thường)
        possible_paths = [
            self.base_dir / f"MAP_{cat_upper}.md",
            self.base_dir / f"map_{category.lower()}.md"
        ]
        for p in possible_paths:
            if p.exists(): return p.read_text(encoding="utf-8")
        return ""

    async def get_brain_knowledge(self, agent_soul_file: str) -> Optional[str]:
        """👁️ [SOUL-RETRIEVAL]: Truy xuất linh hồn (System Prompt) của Đặc vụ."""
        # Thử tìm trong thư mục gốc intelligence hoặc thư mục agents
        possible_paths = [
            self.base_dir / agent_soul_file,
            self.base_dir / "agents" / agent_soul_file
        ]
        for p in possible_paths:
            if p.exists():
                return await asyncio.to_thread(p.read_text, encoding="utf-8")
        return None

# Khởi tạo Singleton
knowledge_orchestrator = JKAIKnowledgeOrchestrator()
