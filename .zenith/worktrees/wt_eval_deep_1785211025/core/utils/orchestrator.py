import json
import os
from core.utils.engine import engine

class NeuralOrchestrator:
    """
    🧠 [NEURAL ORCHESTRATOR]: Trục xương sống nơ-ron SINGULARITY v1.0 Elite.
    Điều phối luồng dữ liệu và sự phối hợp giữa 112 kỹ năng.
    """
    def __init__(self):
        from core.config import settings
        self.bridge_path = os.path.join(settings.INTELLIGENCE_DIR, "NEURAL_LINK_BRIDGE.json")
        self.load_bridge()

    def load_bridge(self):
        if os.path.exists(self.bridge_path):
            with open(self.bridge_path, "r", encoding="utf-8") as f:
                self.bridge = json.load(f)
        else:
            self.bridge = {}

    def execute_chain(self, chain_name: str, initial_input: str, task_id: str):
        """
        🔗 [CHAIN EXECUTION]: Thực thi chuỗi kỹ năng liên hoàn.
        """
        chains = self.bridge.get("chains", {})
        if chain_name not in chains:
            engine.publish_mission_log("ERROR", f"❌ Chain `{chain_name}` không tồn tại trong Bridge.", task_id)
            return None

        current_data = initial_input
        steps = chains[chain_name]["steps"]

        engine.publish_mission_log("NEURAL_LINK", f"🌀 Bắt đầu chuỗi liên hoàn: `{chain_name}`", task_id)

        for step in steps:
            skill_id = step["skill_id"]
            action = step["action"]
            
            engine.publish_mission_log("LINK_STEP", f"⚙️ Đang chuyển giao dữ liệu tới Skill `{skill_id}`...", task_id)
            
            # Giả lập việc gọi kỹ năng (Trong thực tế sẽ gọi qua engine.run_skill)
            # Kết quả của kỹ năng này sẽ là đầu vào của kỹ năng tiếp theo
            result = engine.call_skill(skill_id, {"input": current_data, "action": action}, task_id)
            
            if result.get("status") == "success":
                current_data = result.get("output")
            else:
                engine.publish_mission_log("RECOVERY", f"🛡️ Phát hiện lỗi tại `{skill_id}`. Kích hoạt Self-Healing...", task_id)
                engine.run_skill("#05", {"target": skill_id}, task_id)
                break

        return current_data

orchestrator = NeuralOrchestrator()
