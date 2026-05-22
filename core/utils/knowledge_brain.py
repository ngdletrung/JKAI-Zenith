import os
import json
import logging
import asyncio
import time
import uuid
from typing import List, Dict, Any, Optional

from core.qdrant_client import qdrant_client
from core.utils.engine import engine
from core.config import settings

logger = logging.getLogger('KnowledgeBrain')

class KnowledgeBrain:
    """
    JKAI ZENITH: KNOWLEDGE BRAIN CORE v4.3
    The central intelligence layer for unified knowledge retrieval and synthesis.
    Now with Multi-Collection Sovereign Territory.
    """
    def __init__(self):
        # 🏰 [COLLECTION-REGISTRY]: Lãnh thổ nơ-ron chuyên biệt
        self.collections = {
            "SKILLS": "jkai_skills",      # Procedural Memory
            "MEMORY": "jkai_memory",      # Episodic Memory
            "DOCS": "jkai_docs",          # RAG / Knowledge Base
            "TASKS": "jkai_tasks",        # Task History
            "REFLECTIONS": "jkai_reflections", # Self-Improvement
            "UNIVERSAL": "universal_graph" # Legacy / Mixed
        }
        self.default_collection = self.collections["DOCS"]
        self.summarizer_role = "SUMMARIZER"
        self.embedder_role = "EMBEDDER"
        self.initialized_collections = set()
        self._cache_ttl = 300
        self._cache_prefix = "brain_cache:"
        
        # 💎 [INGESTION-STABILITY]: Batch size toi uu cho Qdrant
        self.batch_size = 64

    def _log(self, tag: str, msg: str, task_id: str = "brain"):
        try:
            engine.publish_mission_log(f"BRAIN:{tag}", msg, task_id)
        except: pass

    async def flush_collection(self, collection: str = None):
        """🧹 [NEURAL-PURGE]: Xóa trắng toàn bộ tri thức của một lãnh thổ."""
        target = collection or self.default_collection
        await qdrant_client.clear_collection(target)
        
        # Reset sync state logic
        sync_files = [
            os.path.join(settings.INTELLIGENCE_DIR, "last_sync.json"),
            os.path.join(settings.INTELLIGENCE_DIR, "last_sync_skills.json")
        ]
        for sf in sync_files:
            if os.path.exists(sf):
                try: os.remove(sf)
                except: pass
        
        try:
            redis = engine._get_redis()
            redis.delete(f"brain_last_sync:{target}")
        except: pass

        if target in self.initialized_collections:
            self.initialized_collections.remove(target)
            
        await self.initialize(target)
        return f"Lãnh thổ `{target}` đã được khởi tạo lại trạng thái sẵn sàng! 💎🫡"

    async def initialize(self, collection: str = None):
        """Khoi tao phao dai tri thuc cho tung lanh tho."""
        target = collection or self.default_collection
        if target in self.initialized_collections: return
        
        v_size = await engine.get_vector_size(self.embedder_role)
        await qdrant_client.ensure_collection(target, vector_size=v_size)
        self.initialized_collections.add(target)

    def _get_collection_for_path(self, path: str) -> str:
        """🗺️ [COGNITIVE-ROUTING]: Phân loại tri thức dựa trên vị trí lãnh thổ."""
        rel_path = os.path.relpath(path, settings.INTELLIGENCE_DIR).lower()
        if rel_path.startswith("skills"): return self.collections["SKILLS"]
        if rel_path.startswith("experience") or rel_path.startswith("mission_wisdom"): return self.collections["MEMORY"]
        if rel_path.startswith("tasks"): return self.collections["TASKS"]
        if rel_path.startswith("reflections"): return self.collections["REFLECTIONS"]
        return self.collections["DOCS"]

    async def ask(self, query: str, limit: int = 5, tier: int = 2, task_id: str = "knowledge_inquiry", role: str = None, collection: str = None) -> str:
        """[TRI-TIER INQUIRY]: Truy van Bo nao Tri thuc 3 Tang."""
        target = collection or self.default_collection
        await self.initialize(target)

        filter_dict = {}
        if role:
            role_map = {
                "PLANNER": ["planner", "refined", "rules", "patterns", "training", "reasoning"],
                "EXECUTOR": ["executor", "refined", "tools", "skills", "training"],
                "RECEPTIONIST": ["reasoning", "refined", "agents", "knowledge", "training"],
                "STEWARD": ["rules", "protocols", "training"]
            }
            target_categories = role_map.get(role.upper(), ["universal", "training"])
            filter_dict = {"category": target_categories}

        import hashlib
        cache_key = self._cache_prefix + hashlib.md5(f"{query}:{tier}:{limit}:{role}:{target}".encode()).hexdigest()
        try:
            cached = engine._get_redis().get(cache_key)
            if cached: return cached.decode("utf-8") if isinstance(cached, bytes) else cached
        except: pass

        try:
            embedding = await engine.get_embeddings(query)
            if not embedding: return "[BRAIN-ERR]: Khong the ma hoa truy van thua Ngai."

            search_results = await qdrant_client.search_similar(
                query_embedding=embedding,
                limit=limit,
                collection=target,
                filter_dict=filter_dict
            )

            if not search_results: return ""

            knowledge_chunks = []
            sources = set()
            for res in search_results:
                payload = res.get('payload', {})
                content = payload.get('content') or payload.get('text', '')
                source = payload.get('path') or payload.get('metadata', {}).get('path', 'Unknown')
                knowledge_chunks.append(f"--- SOURCE: {source} ---\n{content}")
                sources.add(os.path.basename(str(source)))

            raw_knowledge = "\n\n".join(knowledge_chunks)
            source_list = ", ".join(list(sources))

            if tier == 1:
                result = f"[TIER-1: RAW]\n{raw_knowledge}\n\n[NGUON]: {source_list}"
                try: engine._get_redis().setex(cache_key, self._cache_ttl, result)
                except: pass
                return result

            if tier == 2:
                safe_knowledge = raw_knowledge[:3000]
                prompt = (f"Dưới đây là tri thức trích xuất từ Kho dữ liệu JKAI (Lãnh thổ `{target}`) về chủ đề: '{query}'.\n"
                          f"TRI THỨC TRÍCH XUẤT:\n{safe_knowledge}\n\n"
                          f"YÊU CẦU: Ngôn ngữ Tiếng Việt, hào sảng, chuyên nghiệp, chỉ lấy thông tin có trong nguồn.")
                summary = await engine.call_chat(messages=[{"role": "user", "content": prompt}], role=self.summarizer_role, task_id=task_id)
                return f"{summary}\n\n📚 [NGUỒN]: {source_list}"

            if tier == 3:
                prompt = (f"CHÀO MỪNG TỚI TẦNG MINH TRIẾT JKAI ZENITH.\nChủ đề: '{query}'\n\nDỮ LIỆU:\n{raw_knowledge}\n\n"
                          f"NHIỆM VỤ: Phân tích chiến lược đa tầng dựa trên dữ liệu trên và 12 Trụ cột DNA.")
                analysis = await engine.call_chat(messages=[{"role": "user", "content": prompt}], role="PLANNER", task_id=task_id)
                result = f"[TIER-3: STRATEGIC ANALYSIS]\n{analysis}\n\n[NGUON]: {source_list}"
                try: engine._get_redis().setex(cache_key, self._cache_ttl, result)
                except: pass
                return result

        except Exception as e:
            logger.error(f"[BRAIN-QUERY-ERR]: {e}")
            return f"[BRAIN-ERR]: {e}."

    async def distill_experience(self, mission_log: str, task_id: str = "distillation"):
        """[DISTILLATION]: Qui trinh Chung cat Tri tue."""
        target = self.collections["MEMORY"]
        await self.initialize(target)
        prompt = (f"Phân tích Nhật ký Sứ mệnh `{task_id}` và trích xuất 'Success Strategies' & 'Learnings'.\n\nLOG:\n{mission_log}")
        distilled_wisdom = await engine.call_chat(messages=[{"role": "user", "content": prompt}], role=self.summarizer_role, task_id=task_id)
        
        if distilled_wisdom:
            embedding = await engine.get_embeddings(distilled_wisdom)
            if embedding:
                await qdrant_client.upsert_intel(text=distilled_wisdom, embedding=embedding, collection=target,
                    metadata={"path": f"mission_wisdom/{task_id}.md", "type": "distilled_experience", "timestamp": time.time(), "task_id": task_id})
                return distilled_wisdom
        return None

    async def sync_all(self, task_id: str = "sys_sync"):
        """🚀 [BLITZ-SYNC]: Dong bo hoa sieu toc tri thuc thua Master."""
        engine.start_mission(task_id)
        
        current_time = time.time()
        self._log("SYNC", "Khởi động Giao thức Blitz-Sync Đa tầng...", task_id)
        
        SUPPORTED_EXTS = {'.md', '.pdf', '.docx', '.xlsx', '.txt', '.csv', '.py', '.js', '.ts', '.html', '.css', '.sh', '.json', '.yaml', '.toml'}
        from core.utils.converter import converter

        # 🚀 [NEURAL-BUFFERS]: Buffer cho tung lanh tho
        buffers = {name: [] for name in self.collections.values()}
        files_indexed = 0

        for root, _, files in os.walk(settings.INTELLIGENCE_DIR):
            if any(x in root.lower() for x in ["archive", ".git", "__pycache__", "node_modules", "storage", "vault", "logs", "temp"]): continue
            category = os.path.basename(root)
            rel_folder = os.path.relpath(root, settings.INTELLIGENCE_DIR)

            for file in files:
                if "log" in file.lower() or "tail" in file.lower(): continue
                ext = os.path.splitext(file)[1].lower()
                if ext not in SUPPORTED_EXTS: continue

                file_path = os.path.join(root, file)
                try:
                    target_coll = self._get_collection_for_path(file_path)
                    await self.initialize(target_coll)
                    
                    last_sync_key = f"brain_last_sync:{target_coll}"
                    last_sync_time = float(engine._get_redis().get(last_sync_key) or 0)
                    
                    mtime = os.path.getmtime(file_path)
                    if mtime <= last_sync_time: continue

                    content = await converter.to_markdown(file_path, task_id=task_id)
                    if not content or not content.strip(): continue

                    chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
                    embeddings = await asyncio.gather(*[engine.get_embeddings(chunk) for chunk in chunks], return_exceptions=True)

                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        if isinstance(embedding, Exception) or not embedding: continue
                        
                        buffers[target_coll].append({
                            "id": str(uuid.uuid4()),
                            "vector": embedding,
                            "payload": {
                                "text": chunk, "filename": file, "file_type": ext, "category": category,
                                "category_path": rel_folder, "mtime": mtime, "sync_ts": current_time
                            }
                        })

                        # ⚡ [FLUSH-BUFFER]: Giai phong buffer khi dat nguong
                        if len(buffers[target_coll]) >= self.batch_size:
                            v_size = await engine.get_vector_size(self.embedder_role)
                            await qdrant_client.upsert_batch(buffers[target_coll], target_coll, vector_size=v_size)
                            self._log("SYNC", f"Phóng thích Batch vào `{target_coll}`.", task_id)
                            buffers[target_coll].clear()
                            # Cap nhat thoi gian sync cho collection nay
                            engine._get_redis().set(f"brain_last_sync:{target_coll}", str(current_time))

                    files_indexed += 1
                    self._log("SYNC", f"Vectơ hóa hoàn tất: {file}.", task_id)
                except Exception as e:
                    logger.error(f"[SYNC-ERR] {file_path}: {e}")

        # Flush not tiep phan con lai thua Master
        for target_coll, point_buffer in buffers.items():
            if point_buffer:
                v_size = await engine.get_vector_size(self.embedder_role)
                await qdrant_client.upsert_batch(point_buffer, target_coll, vector_size=v_size)
                engine._get_redis().set(f"brain_last_sync:{target_coll}", str(current_time))

        # Skill sync background
        try:
            skill_script = "/workspace/scripts/sync_skills_to_qdrant.py"
            if not os.path.exists(skill_script):
                skill_script = os.path.abspath(os.path.join(settings.BASE_DIR, "scripts", "sync_skills_to_qdrant.py"))
            os.system(f"python3 \"{skill_script}\" {task_id} &")
        except: pass

        res_msg = f"[SYNC-COMPLETE]: Đã phân phối {files_indexed} tệp vào các lãnh thổ nơ-ron!"
        self._log("SYNC", res_msg, task_id)
        return res_msg

knowledge_brain = KnowledgeBrain()
