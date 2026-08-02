import sqlite3
import json
import time
import os
from pathlib import Path

class CogSQLite:
    """
    🏛️ [SOVEREIGN-MEMORY v2.0]: Kho lưu trữ SQLite Hermes-Zenith.
    Hỗ trợ vĩnh cửu hóa trí nhớ, rẽ nhánh session và tìm kiếm siêu tốc.
    """
    def __init__(self, db_path: str = "intelligence/brain.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    task_id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    goal TEXT,
                    final_answer TEXT,
                    status TEXT,
                    created_at REAL,
                    metadata TEXT
                )""")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS beliefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    content TEXT,
                    confidence REAL,
                    source TEXT,
                    ts REAL
                )""")
            # FTS5 with trigram for Vietnamese support
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS beliefs_fts USING fts5(content, task_id UNINDEXED, tokenize='trigram')")

    def save_mission(self, task_id, goal, answer, status, parent_id=None, metadata=None):
        """Lưu hoặc cập nhật sứ mệnh."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO missions (task_id, parent_id, goal, final_answer, status, created_at, metadata) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_id, parent_id, goal, answer, status, time.time(), json.dumps(metadata or {})))

    def branch_mission(self, original_task_id: str, new_task_id: str, new_goal: str):
        """
        🌿 [SESSION-BRANCHING]: Rẽ nhánh một sứ mệnh cũ.
        Kế thừa tri thức từ sứ mệnh gốc sang nhánh mới.
        """
        with sqlite3.connect(self.db_path) as conn:
            # 1. Tạo bản ghi sứ mệnh mới
            conn.execute("""
                INSERT INTO missions (task_id, parent_id, goal, status, created_at)
                SELECT ?, task_id, ?, 'branching', ? FROM missions WHERE task_id = ?
            """, (new_task_id, new_goal, time.time(), original_task_id))
            
            # 2. Sao chép các niềm tin (beliefs) quan trọng
            conn.execute("""
                INSERT INTO beliefs (task_id, content, confidence, source, ts)
                SELECT ?, content, confidence, source, ? FROM beliefs WHERE task_id = ?
            """, (new_task_id, time.time(), original_task_id))
            
            # 3. Đồng bộ FTS
            conn.execute("""
                INSERT INTO beliefs_fts (content, task_id)
                SELECT content, ? FROM beliefs WHERE task_id = ?
            """, (new_task_id, original_task_id))

    def add_belief(self, task_id, content, confidence, source):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO beliefs (task_id, content, confidence, source, ts) VALUES (?, ?, ?, ?, ?)",
                         (task_id, content, confidence, source, time.time()))
            conn.execute("INSERT INTO beliefs_fts (content, task_id) VALUES (?, ?)", (content, task_id))

    def search_beliefs(self, query: str, limit: int = 10):
        """Tìm kiếm tri thức toàn văn."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT task_id, content, rank 
                FROM beliefs_fts 
                WHERE content MATCH ? 
                ORDER BY rank 
                LIMIT ?
            """, (query, limit)).fetchall()

cog_sqlite = CogSQLite()

