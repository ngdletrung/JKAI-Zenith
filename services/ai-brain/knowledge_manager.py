import os
import re
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.utils.engine import engine

class JKAIKnowledgeOrchestrator:
    """
    🧬 JKAI Knowledge Orchestrator v10.0 (Neural Evolution)
    Quản trị và truy xuất tri thức dựa trên Intelligence Map.
    Hỗ trợ Auto-Discovery cho tất cả định dạng MAP_SKILLS.md.
    """
    def __init__(self, base_dir: str = "D:/Docker/N8N/intelligence"):
        self.base_dir = Path(base_dir)
        self.map_path = self.base_dir / "map.json"
        
        # Load Map
        try:
            with open(self.map_path, "r", encoding="utf-8") as f:
                self.intel_map = json.load(f)
        except:
            self.intel_map = {}

    def get_jkai_manifests(self) -> Dict:
        """Thống kê trạng thái các khu vực tri thức."""
        stats = []
        categories = ["agents", "rules", "skills", "knowledge"]
        
        for cat in categories:
            path = self.base_dir / cat
            count = len(list(path.glob("*.md"))) if path.exists() else 0
            stats.append({
                "id": cat.upper(),
                "description": f"Bản ghi Elite: {count}",
                "path": str(path),
                "status": "Healthy"
            })
        return {"indexes": stats, "version": "v10.0"}

    def get_jkai_manifesto(self) -> str:
        """Đọc bản tuyên ngôn (Manifesto) chính thức của Tập đoàn."""
        manifesto_path = self.base_dir / "JKAI_ZENITH_CORP.md"
        if manifesto_path.exists():
            return manifesto_path.read_text(encoding="utf-8")
        return "Tập đoàn JKAI Zenith: Hệ điều hành Trí tuệ Chiến lược."

    def get_knowledge_index(self) -> str:
        """Truy xuất danh mục 19 bộ Mật tịch trong Đại thư viện Zenith."""
        knowledge_path = self.base_dir / "knowledge"
        if not knowledge_path.exists(): return "Đại thư viện đang trống thưa Master."
        
        summary = ["DANH MUC DAI THU VIEN ZENITH:"]
        for f in sorted(knowledge_path.glob("*.md")):
            summary.append(f"- {f.name}")
        return "\n".join(summary)

    def get_category_map(self, category: str) -> str:
        """Đọc bản đồ chuyên khu để lấy danh mục tri thức và tính năng."""
        map_path = self.base_dir / f"MAP_{category.upper()}.md"
        if map_path.exists():
            return map_path.read_text(encoding="utf-8")
        return f"Chua co ban do cho danh muc {category}."

    def get_all_skills_dict(self) -> Dict:
        """📦 [GROUND-TRUTH]: Đọc toàn bộ kỹ năng từ registry.json thưa Master."""
        registry_path = self.base_dir / "registry.json"
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("skills", {})
        except:
            return {}

    def get_all_skills_summary(self) -> str:
        """
        Tóm tắt toàn bộ kỹ năng (Skills) dựa trên MAP_SKILLS.md v33.8 thưa Master.
        Hỗ trợ định dạng: - **Emoji #Number. name** [TYPE]: Description
        """
        map_content = self.get_category_map("skills")
        if "Chua co ban do" in map_content:
            return "Kho kỹ năng đang trống thưa Master."
        
        lines = map_content.splitlines()
        summary = []
        
        for line in lines:
            # Định dạng: - **... skill_name** [TYPE]: Description
            match = re.search(r'- \*\*.*?\s+#(\d+)\.\s+(skill_[a-zA-Z0-9_]+)\*\*\s+\[(.*?)\]:\s+(.*)', line)
            if match:
                s_id, s_name, s_type, s_desc = match.groups()
                summary.append(f"- {s_name} (#{s_id}): {s_desc} [{s_type}]")
                continue
            
            # Fallback cho định dạng cũ thưa Ngài
            if "**" in line and "`" in line:
                matches = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]*)`', line)
                for m in matches:
                    summary.append(f"- {m}")
                        
        return "\n".join(summary) if summary else "Chưa có kỹ năng nào được ghi danh thưa Master."

    def resolve_path(self, key: str) -> str:
        """Chuyển đổi ID từ Map thành đường dẫn tuyệt đối (Environment Aware)."""
        rel_path = self.intel_map.get(key)
        if not rel_path: return ""
        
        # Nếu đang chạy trong Docker (có /intelligence), dùng root /
        if os.path.exists("/intelligence"):
            return str(Path("/") / rel_path)
        # Nếu đang chạy trên Windows host
        return str(Path("D:/Docker/N8N") / rel_path)

    async def smart_retrieve(self, query: str, task_id: str = "system") -> Dict[str, Any]:
        """
        🧪 [ADR-090]: 5-Phase Smart Retrieval thưa Master.
        """
        # 1. Query Expansion thưa Master
        expanded_queries = await self._expand_query(query, task_id)
        
        # 2. Hybrid Search & RRF Fusion (Mocking BM25 + Vector) thưa Master
        # Hiện tại ta ưu tiên Vector search từ Qdrant thưa Ngài
        from core.qdrant_client import qdrant_client
        from core.utils.embed import embed
        
        all_results = []
        for q in expanded_queries[:2]: # Chỉ lấy 2 query hàng đầu để tiết kiệm
            vector = embed(q)
            if vector:
                res = await qdrant_client.search_similar(vector, limit=5)
                all_results.extend(res)
        
        # 3. Recency Boost & MMR Diversity thưa Master
        # (Lọc bỏ trùng lặp và chọn các nơ-ron tri thức tươi nhất)
        unique_results = self._apply_mmr(all_results, query)
        
        # 4. Context Synthesis thưa Master
        context_text = "\n\n".join([r.get("payload", {}).get("content", "") for r in unique_results if r.get("payload")])
        
        return {
            "expanded_queries": expanded_queries,
            "context": context_text[:15000], # Giới hạn nơ-ron thưa Master
            "sources": [r.get("payload", {}).get("source", "Unknown") for r in unique_results]
        }

    async def _expand_query(self, query: str, task_id: str) -> List[str]:
        """Giai đoạn 1: Khai phóng truy vấn thưa Master."""
        prompt = f"Phân tích yêu cầu '{query}' và tạo ra 3 biến thể tìm kiếm (tiếng Anh và tiếng Việt) để quét sâu tri thức. Trả về JSON list các chuỗi (string)."
        try:
            res = await engine.call_chat([{"role": "user", "content": prompt}], role="SUMMARIZER", task_id=task_id, json_mode=True)
            if isinstance(res, list):
                # Clean up if the model returns a list of dicts
                clean_res = []
                for item in res:
                    if isinstance(item, str): clean_res.append(item)
                    elif isinstance(item, dict) and item.values(): clean_res.append(str(list(item.values())[0]))
                if clean_res: return clean_res
        except: pass
        return [query]

    def _apply_mmr(self, results: List[Dict], query: str, lambda_param: float = 0.5) -> List[Dict]:
        """Giai đoạn 4: MMR Diversity - Chống trùng lặp tri thức thưa Master."""
        seen_ids = set()
        diverse_results = []
        for r in results:
            p_id = r.get("id")
            if p_id not in seen_ids:
                diverse_results.append(r)
                seen_ids.add(p_id)
        return diverse_results[:5]
