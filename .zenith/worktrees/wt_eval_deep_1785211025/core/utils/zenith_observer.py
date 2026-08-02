import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

class ZenithObserver:
    """
    Observers interactions and logs them to project-specific neural history.
    Enables introspection and future learning.
    """
    
    def __init__(self, zenith_dir: str):
        self.zenith_dir = Path(zenith_dir)
        self.history_file = self.zenith_dir / "logs" / "neural_history.jsonl"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs a structured event to the neural history."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "data": data
        }
        
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
            
    def record_task_success(self, task_description: str, tools_used: list, outcome: str):
        """Records a successful task completion."""
        self.log_event("task_success", {
            "description": task_description,
            "tools": tools_used,
            "outcome": outcome
        })
        
    def record_failure(self, task_description: str, error_msg: str, stack_trace: str = None):
        """Records a failure for introspection."""
        self.log_event("task_failure", {
            "description": task_description,
            "error": error_msg,
            "stack_trace": stack_trace
        })

    def get_recent_history(self, limit: int = 10) -> list:
        """Retrieves recent history for introspection."""
        if not self.history_file.exists():
            return []
            
        history = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                history.append(json.loads(line))
        return history
