import os
import hashlib
import sqlite3
import json
import time
import threading
from typing import Optional

DB_FILENAME = ".ks_metadata.db"

class MetadataDB:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        if db_path:
            self.db_path = os.path.join(db_path, DB_FILENAME)
        else:
            from core.config import settings
            self.db_path = os.path.join(settings.INTELLIGENCE_DIR, DB_FILENAME)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        self._initialized = True

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        # 1. Đảm bảo bảng lưu phiên bản schema tồn tại
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY, version INTEGER NOT NULL)")
        row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
        current_version = row[0] if row else 0

        # 2. Danh sách các bản cập nhật cấu trúc database qua từng thời kỳ
        migrations = [
            # Phiên bản 1: Cấu trúc ban đầu
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                config TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_sync REAL,
                status TEXT DEFAULT 'active',
                error_msg TEXT
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                rel_path TEXT NOT NULL,
                abs_path TEXT NOT NULL,
                file_type TEXT NOT NULL DEFAULT '',
                checksum TEXT NOT NULL DEFAULT '',
                file_size INTEGER DEFAULT 0,
                mtime REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                last_indexed REAL,
                error_msg TEXT,
                UNIQUE(source_id, rel_path)
            );
            CREATE INDEX IF NOT EXISTS idx_files_source ON files(source_id);
            CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
            CREATE INDEX IF NOT EXISTS idx_files_checksum ON files(checksum);
            CREATE TABLE IF NOT EXISTS hot_queries (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1,
                last_hit REAL NOT NULL
            );
            """
            # Phiên bản 2, 3... (sẽ bổ sung ALTER TABLE ở đây khi hệ thống nâng cấp)
        ]

        # 3. Thực thi các bản nâng cấp còn thiếu
        if current_version < len(migrations):
            for idx in range(current_version, len(migrations)):
                conn.executescript(migrations[idx])
                new_version = idx + 1
                conn.execute("INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)", (new_version,))
            conn.commit()

    def register_source(self, source_id: str, name: str, source_type: str, config: dict = None):
        now = time.time()
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO sources (id, name, type, config, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, type=excluded.type, config=excluded.config,
                updated_at=excluded.updated_at
        """, (source_id, name, source_type, json.dumps(config or {}), now, now))
        conn.commit()

    def remove_source(self, source_id: str):
        conn = self._get_conn()
        conn.execute("DELETE FROM files WHERE source_id = ?", (source_id,))
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        conn.commit()

    def get_source(self, source_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row:
            d = dict(row)
            d["config"] = json.loads(d.get("config", "{}"))
            return d
        return None

    def list_sources(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM sources ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def upsert_file(self, source_id: str, rel_path: str, abs_path: str,
                    file_type: str = "", checksum: str = "", file_size: int = 0,
                    mtime: float = 0, status: str = "pending"):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO files (source_id, rel_path, abs_path, file_type, checksum,
                               file_size, mtime, status, last_indexed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id, rel_path) DO UPDATE SET
                abs_path=excluded.abs_path, file_type=excluded.file_type,
                checksum=excluded.checksum, file_size=excluded.file_size,
                mtime=excluded.mtime, status=excluded.status, last_indexed=excluded.last_indexed,
                error_msg=excluded.error_msg
        """, (source_id, rel_path, abs_path, file_type, checksum,
              file_size, mtime, status, time.time()))
        conn.commit()

    def mark_indexed(self, source_id: str, rel_path: str, checksum: str = ""):
        conn = self._get_conn()
        conn.execute("""
            UPDATE files SET status='indexed', last_indexed=?, checksum=?
            WHERE source_id=? AND rel_path=?
        """, (time.time(), checksum, source_id, rel_path))
        conn.commit()

    def mark_failed(self, source_id: str, rel_path: str, error_msg: str):
        conn = self._get_conn()
        conn.execute("""
            UPDATE files SET status='failed', error_msg=?, last_indexed=?
            WHERE source_id=? AND rel_path=?
        """, (error_msg, time.time(), source_id, rel_path))
        conn.commit()

    def get_stale_files(self, source_id: str, cutoff: float = None) -> list[dict]:
        conn = self._get_conn()
        if cutoff is None:
            cutoff = time.time()
        rows = conn.execute("""
            SELECT * FROM files
            WHERE source_id=? AND (last_indexed IS NULL OR last_indexed < ?)
            AND status != 'failed'
        """, (source_id, cutoff)).fetchall()
        return [dict(r) for r in rows]

    def get_all_indexed_files(self, source_id: str = None) -> list[dict]:
        conn = self._get_conn()
        if source_id:
            rows = conn.execute("SELECT * FROM files WHERE source_id=? AND status='indexed'",
                              (source_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM files WHERE status='indexed'").fetchall()
        return [dict(r) for r in rows]

    def get_file(self, source_id: str, rel_path: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM files WHERE source_id=? AND rel_path=?",
                          (source_id, rel_path)).fetchone()
        return dict(row) if row else None

    def get_all_files(self, source_id: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM files WHERE source_id=?", (source_id,)).fetchall()
        return [dict(r) for r in rows]

    def record_hot_query(self, query: str):
        h = hashlib.md5(query.encode()).hexdigest()
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO hot_queries (query_hash, query_text, hit_count, last_hit)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(query_hash) DO UPDATE SET
                hit_count=hit_count+1, last_hit=excluded.last_hit
        """, (h, query[:500], time.time()))
        conn.commit()

    def get_top_hot_queries(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT query_text, hit_count FROM hot_queries
            ORDER BY hit_count DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

metadata_db = MetadataDB()
