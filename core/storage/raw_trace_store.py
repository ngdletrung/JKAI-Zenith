# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — DEMS v1.0: RAW TRACE CANONICAL STORE             ║
│   SSoT Lịch Sử Bất Biến (Turn → Window → Episode → Mission)      │
╚══════════════════════════════════════════════════════════════════╝
Tuân thủ 7 Bất biến DEMS:
  I-DEMS-01: Historical Immutability (Append-only)
  I-DEMS-02: Evidence Provenance (Truy nguyên chính xác)
  I-DEMS-07: Derived Views Are Rebuildable
"""

from __future__ import annotations
import os
import time
import json
import sqlite3
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Generator

logger = logging.getLogger("JKAI.DEMS.RawTraceStore")

DEFAULT_DB_PATH = "intelligence/raw_traces.db"


@dataclass(frozen=True)
class RawTrace:
    trace_id: str
    mission_id: str
    episode_id: str
    window_id: str
    turn_id: str
    actor: str                # "user", "assistant", "tool", "system"
    event_type: str           # "prompt", "command_exec", "file_mutation", "observation", "verdict"
    payload: Dict[str, Any]   # Nội dung thô 100% không tóm tắt
    authority_level: int      # 1 (Model Inference) -> 4 (Runtime Tool)
    timestamp: float = field(default_factory=time.time)
    integrity_hash: str = ""
    parent_trace_id: Optional[str] = None

    def compute_hash(self) -> str:
        content_str = json.dumps(self.payload, sort_keys=True, ensure_ascii=False)
        raw = f"{self.trace_id}:{self.mission_id}:{self.episode_id}:{self.window_id}:{self.turn_id}:{self.actor}:{self.event_type}:{self.authority_level}:{self.timestamp}:{content_str}:{self.parent_trace_id or ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RawTraceStore:
    """
    📜 Kho Lưu Trữ Raw Trace Chuẩn Hóa (Canonical Event SSoT)
    - Lưu giữ toàn vẹn 100% vết tích tương tác thô trong SQLite (Append-Only).
    - Phục vụ việc tái tạo (Rebuild) toàn bộ Derived Indexes: Qdrant, BM25, TypedWorldGraph.
    """
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_traces (
                    trace_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    episode_id TEXT NOT NULL,
                    window_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    authority_level INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    integrity_hash TEXT NOT NULL,
                    parent_trace_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_mission ON raw_traces(mission_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_episode ON raw_traces(episode_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_window ON raw_traces(window_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_turn ON raw_traces(turn_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_ts ON raw_traces(timestamp)")

    def append_trace(
        self,
        mission_id: str,
        episode_id: str,
        window_id: str,
        turn_id: str,
        actor: str,
        event_type: str,
        payload: Dict[str, Any],
        authority_level: int = 1,
        parent_trace_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> RawTrace:
        """Ghi nhận vết tích thô bất biến (Append-Only) vào SQLite."""
        import uuid
        t_id = trace_id or f"tr_{uuid.uuid4().hex[:14]}"
        now = time.time()

        dummy = RawTrace(
            trace_id=t_id,
            mission_id=mission_id,
            episode_id=episode_id,
            window_id=window_id,
            turn_id=turn_id,
            actor=actor,
            event_type=event_type,
            payload=payload,
            authority_level=authority_level,
            timestamp=now,
            integrity_hash="",
            parent_trace_id=parent_trace_id
        )
        h = dummy.compute_hash()

        trace = RawTrace(
            trace_id=t_id,
            mission_id=mission_id,
            episode_id=episode_id,
            window_id=window_id,
            turn_id=turn_id,
            actor=actor,
            event_type=event_type,
            payload=payload,
            authority_level=authority_level,
            timestamp=now,
            integrity_hash=h,
            parent_trace_id=parent_trace_id
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO raw_traces (
                    trace_id, mission_id, episode_id, window_id, turn_id,
                    actor, event_type, payload_json, authority_level,
                    timestamp, integrity_hash, parent_trace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace.trace_id, trace.mission_id, trace.episode_id, trace.window_id, trace.turn_id,
                trace.actor, trace.event_type, json.dumps(trace.payload, ensure_ascii=False), trace.authority_level,
                trace.timestamp, trace.integrity_hash, trace.parent_trace_id
            ))

        logger.debug(f"[RAW-TRACE-APPEND]: Recorded {trace.trace_id} ({trace.event_type}) for mission {mission_id}")
        return trace

    def get_trace(self, trace_id: str) -> Optional[RawTrace]:
        """Đọc một RawTrace theo trace_id."""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT trace_id, mission_id, episode_id, window_id, turn_id,
                       actor, event_type, payload_json, authority_level,
                       timestamp, integrity_hash, parent_trace_id
                FROM raw_traces WHERE trace_id = ?
            """, (trace_id,)).fetchone()
            if not row:
                return None
            return self._row_to_trace(row)

    def get_traces_by_mission(self, mission_id: str, limit: int = 100) -> List[RawTrace]:
        """Truy xuất các traces thuộc một Mission."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT trace_id, mission_id, episode_id, window_id, turn_id,
                       actor, event_type, payload_json, authority_level,
                       timestamp, integrity_hash, parent_trace_id
                FROM raw_traces WHERE mission_id = ? ORDER BY timestamp ASC LIMIT ?
            """, (mission_id, limit)).fetchall()
            return [self._row_to_trace(r) for r in rows]

    def get_traces_by_episode(self, episode_id: str, limit: int = 50) -> List[RawTrace]:
        """Truy xuất các traces thuộc một Episode."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT trace_id, mission_id, episode_id, window_id, turn_id,
                       actor, event_type, payload_json, authority_level,
                       timestamp, integrity_hash, parent_trace_id
                FROM raw_traces WHERE episode_id = ? ORDER BY timestamp ASC LIMIT ?
            """, (episode_id, limit)).fetchall()
            return [self._row_to_trace(r) for r in rows]

    def iterate_all_traces(self, batch_size: int = 100) -> Generator[RawTrace, None, None]:
        """Lặp qua toàn bộ traces để phục vụ Rebuild Derived Indexes."""
        last_rowid = 0
        while True:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT rowid, trace_id, mission_id, episode_id, window_id, turn_id,
                           actor, event_type, payload_json, authority_level,
                           timestamp, integrity_hash, parent_trace_id
                    FROM raw_traces WHERE rowid > ? ORDER BY rowid ASC LIMIT ?
                """, (last_rowid, batch_size)).fetchall()
                if not rows:
                    break
                for r in rows:
                    last_rowid = r[0]
                    yield self._row_to_trace(r[1:])

    def count_traces(self) -> int:
        with self._get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM raw_traces").fetchone()[0]

    def _row_to_trace(self, row: tuple) -> RawTrace:
        return RawTrace(
            trace_id=row[0],
            mission_id=row[1],
            episode_id=row[2],
            window_id=row[3],
            turn_id=row[4],
            actor=row[5],
            event_type=row[6],
            payload=json.loads(row[7]),
            authority_level=row[8],
            timestamp=row[9],
            integrity_hash=row[10],
            parent_trace_id=row[11]
        )


raw_trace_store = RawTraceStore()
