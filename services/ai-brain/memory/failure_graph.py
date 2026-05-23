import json
import os

class SemanticFailureGraph:
    """
    🧠 Đồ Thị Sụp Đổ Ngữ Nghĩa (Semantic Failure Graph)
    Không chỉ lưu Log tuyến tính, mà vẽ ra biểu đồ nhân-quả (Cause & Effect) của các lỗi.
    Ví dụ: Tool A -> Thường Timeout -> Khi Network > 200ms.
    """
    def __init__(self, db_path: str = "d:/Docker/N8N/services/ai-brain/memory/failure_graph.json"):
        self.db_path = db_path
        self.graph = self._load_graph()

    def _load_graph(self) -> dict:
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"nodes": {}, "edges": []}

    def record_failure_event(self, intent: str, error_code: str, env_context: dict):
        """
        Ghi nhận một điểm nứt gãy vào Đồ thị.
        """
        # Node là Intent (Hành động)
        if intent not in self.graph["nodes"]:
            self.graph["nodes"][intent] = {"fail_count": 0, "types": {}}
            
        self.graph["nodes"][intent]["fail_count"] += 1
        
        # Phân nhánh theo loại lỗi
        if error_code not in self.graph["nodes"][intent]["types"]:
            self.graph["nodes"][intent]["types"][error_code] = 0
        self.graph["nodes"][intent]["types"][error_code] += 1
        
        # Edge (Mắt xích nguyên nhân)
        # Giả sử env_context chứa thông tin RAM lúc đó
        ram_state = "HIGH_RAM" if env_context.get("ram_percent", 0) > 80 else "NORMAL_RAM"
        
        edge = {
            "source": intent,
            "target": error_code,
            "condition": ram_state
        }
        self.graph["edges"].append(edge)
        
        # Lưu Graph
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.graph, f, indent=4)
            
    def analyze_root_cause(self, intent: str) -> str:
        """
        Phân tích nguyên nhân sâu xa của một Tool hay bị lỗi.
        """
        if intent not in self.graph["nodes"]:
            return "Chưa đủ dữ liệu đồ thị."
            
        node = self.graph["nodes"][intent]
        dominant_error = max(node["types"], key=node["types"].get)
        
        return f"🚨 [ROOT CAUSE]: Kỹ năng {intent} thường xuyên sụp đổ do mã lỗi {dominant_error}."
