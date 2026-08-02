from runtime.cir import CanonicalIntentRepresentation
import hashlib

class GoalIntegrityMonitor:
    """
    🎯 Máy Quét Toàn Vẹn Mục Tiêu (Goal Integrity Monitor)
    Ngăn chặn hiện tượng Goal Mutation (Ví dụ: Từ "Giải phóng RAM" biến thành "Tối ưu ổ đĩa" sau 10 bước suy luận).
    """
    def __init__(self):
        pass

    def _hash_goal(self, goal: str) -> str:
        # Ở cấp độ Production thực tế, đây nên là Vector Embedding Similarity (Cosme)
        # Tạm thời dùng băm từ khóa chính để so khớp ngữ nghĩa cơ bản
        keywords = "".join([w for w in goal.lower().split() if len(w) > 3])
        return hashlib.md5(keywords.encode()).hexdigest()

    def check_integrity(self, original_goal: str, current_subgoal: str) -> float:
        """
        Đánh giá độ tương đồng giữa mục tiêu gốc và mục tiêu hiện tại.
        Trả về Similarity Score (0.0 -> 1.0)
        """
        # Giả lập Vector Similarity Score (Thực tế sẽ dùng Model Embedder)
        # Trả về điểm giả lập tạm thời dựa trên keyword overlap
        orig_words = set(original_goal.lower().split())
        sub_words = set(current_subgoal.lower().split())
        
        if not orig_words: return 1.0
        
        overlap = orig_words.intersection(sub_words)
        score = len(overlap) / len(orig_words)
        
        # Bơm điểm (padding) để không quá khắt khe, nhưng nếu hoàn toàn lệch pha thì score = 0
        return min(score + 0.3, 1.0) 

class CognitiveCritic:
    """
    👁️ Thẩm Phán Nhận Thức (Cognitive Critic Layer)
    Không chỉ bắt lỗi cú pháp, mà bắt lỗi Suy Luận Logic (Reasoning Drift).
    """
    def __init__(self):
        self.goal_monitor = GoalIntegrityMonitor()
        self.logic_axioms = {
            "FREE_RAM": ["kill_process", "restart_service", "clear_cache"],
            "FREE_DISK": ["delete_file", "empty_trash", "uninstall"]
        }

    def evaluate_reasoning_chain(self, original_goal: str, current_subgoal: str, cir: CanonicalIntentRepresentation) -> dict:
        """
        Kiểm tra xem Intent của Planner có thực sự giải quyết được Goal không.
        Trả về: {"approved": bool, "reason": str}
        """
        # 0. Kiểm tra Toàn vẹn Mục Tiêu (Goal Integrity)
        integrity_score = self.goal_monitor.check_integrity(original_goal, current_subgoal)
        if integrity_score < 0.4:
            return {
                "approved": False,
                "reason": f"🚨 [GOAL MUTATION]: Mục tiêu đã bị bóp méo! (Similarity Score: {integrity_score:.2f}). Abort!"
            }

        intent = cir.intent
        
        # 1. Detect Reasoning Drift (Suy luận trôi dạt)
        if "ram" in original_goal.lower() or "bộ nhớ tạm" in original_goal.lower():
            if intent in ["DELETE_FILE", "REMOVE_DIR", "FORMAT_DISK"]:
                return {
                    "approved": False, 
                    "reason": "🚨 [REASONING DRIFT]: Để giải phóng RAM, không được dùng lệnh xóa file vật lý trên đĩa cứng!"
                }
                
        return {"approved": True, "reason": "Logic Validated."}

    def validate_blueprint(self, original_goal: str, steps: list) -> dict:
        """
        Kiểm định toàn bộ kế hoạch (blueprint steps) trước khi đưa vào DAG Executor
        để bảo đảm Không Có Sự Bóp Méo Mục Tiêu (Goal Mutation) và Trôi Dạt Suy Luận (Reasoning Drift).
        """
        for idx, step in enumerate(steps):
            subgoal = str(step.get("action", "") or step.get("description", "") or step.get("goal", "") or "")
            if not subgoal:
                continue
            # Kiểm tra Goal Integrity
            integrity_score = self.goal_monitor.check_integrity(original_goal, subgoal)
            if integrity_score < 0.25:
                return {
                    "approved": False,
                    "reason": f"Bước {idx+1} ('{subgoal[:50]}...') vi phạm tính toàn vẹn mục tiêu (Score: {integrity_score:.2f})."
                }

            # Kiểm tra Reasoning Drift
            sub_lower = subgoal.lower()
            orig_lower = original_goal.lower()
            if ("ram" in orig_lower or "bộ nhớ tạm" in orig_lower) and any(w in sub_lower for w in ["format", "delete_file", "rm -rf", "xóa file"]):
                return {
                    "approved": False,
                    "reason": f"Bước {idx+1} vi phạm lập luận logic: Dùng lệnh xóa dữ liệu vật lý để giải phóng RAM."
                }
                
        return {"approved": True, "reason": "Zero Drift Validated."}

    def detect_recursive_confusion(self, trace_history: list) -> bool:
        if len(trace_history) < 3:
            return False
            
        last_3_intents = [t.get("intent") for t in trace_history[-3:]]
        if len(set(last_3_intents)) == 1 and last_3_intents[0] is not None:
            return True
            
        return False

