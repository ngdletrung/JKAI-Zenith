import json
import time
import os
from pathlib import Path
from core.utils.engine import engine

class TrajectoryRecorder:
    """
    🧬 JKAI ZENITH: TRAJECTORY RECORDER (v3.6 Internal Learning)
    Ghi lại hành trình nơ-ron để tự tối ưu hóa.
    """
    def __init__(self):
        from core.config import settings
        self.base_dir = Path(settings.INTELLIGENCE_DIR) / "trajectories"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def start_trajectory(self, task_id, goal):
        """Khởi tạo một hành trình mới."""
        trajectory = {
            "task_id": task_id,
            "goal": goal,
            "start_ts": time.time(),
            "steps": [],
            "status": "in_progress"
        }
        self._save(task_id, trajectory)
        return trajectory

    def add_step(self, task_id, action, observation, thought=""):
        """Ghi lại một bước đi của đặc vụ."""
        trajectory = self._load(task_id)
        if trajectory:
            trajectory["steps"].append({
                "ts": time.time(),
                "action": action,
                "thought": thought,
                "observation": observation
            })
            self._save(task_id, trajectory)

    def end_trajectory(self, task_id, status="success"):
        """Kết thúc và đóng gói hành trình."""
        trajectory = self._load(task_id)
        if trajectory:
            trajectory["status"] = status
            trajectory["end_ts"] = time.time()
            trajectory["duration"] = trajectory["end_ts"] - trajectory["start_ts"]
            self._save(task_id, trajectory)
            
            # 🚀 Tự động đúc kết Pattern nếu thành công
            if status == "success":
                self._forge_pattern(trajectory)

    def _save(self, task_id, data):
        file_path = self.base_dir / f"{task_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self, task_id):
        file_path = self.base_dir / f"{task_id}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _forge_pattern(self, trajectory):
        """Đúc kết tinh hoa từ hành trình thành Pattern tri thức."""
        # Logic đúc kết sẽ được gọi bởi skill_tucaitien
        pass

# Singleton
recorder = TrajectoryRecorder()
