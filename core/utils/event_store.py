import sqlite3
import json
import time
import os
from typing import List, Dict, Any, Optional
from core.utils.hlc import hlc

class EventStore:
    """
    🏛️ [EVENT-STORE]: Lõi lưu trữ sự kiện nơ-ron.
    Triển khai Event Sourcing (ADR-007) để đảm bảo tính nhất quán và khả năng hậu kiểm.
    """
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Fallback cho môi trường
            base_dir = "d:/Docker/N8N/core/data"
            if not os.path.exists(base_dir): os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "zenith_events.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hlc_timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON events(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hlc ON events(hlc_timestamp)")

    def log_event(self, task_id: str, agent_id: str, event_type: str, payload: Dict[str, Any]):
        """Ghi lại một nơ-ron sự kiện."""
        try:
            ts_hlc = str(hlc.now())
            payload_json = json.dumps(payload, ensure_ascii=False)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO events (hlc_timestamp, task_id, agent_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (ts_hlc, task_id, agent_id, event_type, payload_json, time.time())
                )
        except Exception as e:
            print(f"❌ [EVENT-STORE-ERR]: {e}")

    def get_events_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Truy xuất toàn bộ nơ-ron lịch sử của một tác vụ."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM events WHERE task_id = ? ORDER BY hlc_timestamp ASC", (task_id,))
            return [dict(row) for row in cursor.fetchall()]

# Singleton
event_store = EventStore()
