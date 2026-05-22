import json
import logging
from typing import List, Dict, Any

class CapabilityGraph:
    """
    🏛️ JKAI ZENITH: CAPABILITY GRAPH v1.0
    Chuyển đổi danh sách Skill phẳng thành bản đồ năng lực đa chiều.
    """
    def __init__(self, skills_dict: Dict[str, Any]):
        self.graph = {}
        self._build_graph(skills_dict)

    def _build_graph(self, skills: Dict[str, Any]):
        for s_id, data in skills.items():
            # 🧬 [SKILL-DNA]: Trích xuất mã gen năng lực
            capabilities = self._extract_capabilities(data)
            self.graph[s_id] = {
                "id": s_id,
                "name": data.get("name"),
                "capabilities": capabilities,
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "reliability": data.get("rating", 100) / 100,
                "domain": data.get("domain", "general"),
                "failure_modes": data.get("failure_modes", [])
            }

    def _extract_capabilities(self, data: Dict[str, Any]) -> List[str]:
        """
        🧪 [MACRO-CAPABILITY-MINING]: Trích xuất năng lực vĩ mô.
        Hỗ trợ đa ngôn ngữ và miễn nhiễm với lỗi dấu tiếng Việt.
        """
        from core.utils.intent_lexicon import _normalize
        desc_raw = (data.get("description", "") + " " + data.get("notes", "")).lower()
        desc_norm = _normalize(desc_raw)
        
        caps = []
        # 🏛️ [CAPABILITY-LEXICON-v2.0]: Bản đồ năng lực vĩ mô
        keywords = {
            "web_search": ["search", "google", "internet", "tin tuc", "news", "tra cuu", "online", "web"],
            "finance": ["forex", "money", "stock", "crypto", "tai chinh", "tien te", "gia"],
            "code": ["python", "script", "execute", "programming", "code", "lap trinh"],
            "system": ["terminal", "shell", "os", "file", "system", "he thong"],
            "analysis": ["analyze", "summarize", "research", "phan tich", "tong hop"]
        }
        
        for cap, tags in keywords.items():
            # Đối soát song song: Có dấu và Không dấu
            if any(t in desc_raw or t in desc_norm for t in tags):
                caps.append(cap)
        return caps

    def match_capabilities(self, required_caps: List[str]) -> List[str]:
        """Tìm kiếm các Đặc vụ có năng lực phù hợp."""
        matches = []
        for s_id, data in self.graph.items():
            score = sum(1 for c in required_caps if c in data["capabilities"])
            if score > 0:
                matches.append(s_id)
        return matches
