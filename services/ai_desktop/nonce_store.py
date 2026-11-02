# -*- coding: utf-8 -*-
"""
services/ai_desktop/nonce_store.py
[JKAI PERSISTENT ANTI-REPLAY NONCE STORE]

Durable, thread-safe nonce ledger used by every desktop mutation path. SQLite WAL
keeps claims surviving process restarts so a crashed-then-replayed action is still
detected. This module is the single owner; scripts/persistent_nonce_store.py is a
compatibility re-export.
"""

import os
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "persistent_nonces.db"


class PersistentNonceStore:
    """
    Quản lý lưu trữ và xác thực Nonce bền vững (Persistent Anti-Replay Store).
    Thread-safe và chống tranh chấp ghi đồng thời.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with closing(self._get_connection()) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nonces (
                        nonce TEXT PRIMARY KEY,
                        scope TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nonces_expires ON nonces (expires_at);")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lease_claims (
                        lease_id TEXT PRIMARY KEY,
                        nonce TEXT NOT NULL,
                        claimed_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_lease_claims_expires ON lease_claims (expires_at);")
                conn.commit()

    def check_and_use_nonce(self, nonce: str, scope: str, ttl_seconds: float = 300.0) -> bool:
        """
        Kiểm tra và đánh dấu sử dụng nonce nguyên tử.
        Trả về True nếu nonce hợp lệ và chưa từng xuất hiện.
        Trả về False nếu nonce đã tồn tại hoặc đã bị dùng (Replay Attack).
        """
        if not nonce or not isinstance(nonce, str) or not nonce.strip():
            return False

        now = time.time()
        expires_at = now + max(0.01, ttl_seconds)

        with self._lock:
            with closing(self._get_connection()) as conn:
                try:
                    conn.execute("DELETE FROM nonces WHERE expires_at < ?", (now,))
                    conn.execute(
                        "INSERT INTO nonces (nonce, scope, created_at, expires_at) VALUES (?, ?, ?, ?)",
                        (nonce.strip(), scope.strip(), now, expires_at)
                    )
                    conn.commit()
                    return True
                except sqlite3.IntegrityError:
                    return False
                except Exception:
                    return False

    def check_and_use_two_nonces_atomic(
        self,
        nonce1: str,
        scope1: str,
        nonce2: str,
        scope2: str,
        ttl_seconds: float = 300.0
    ) -> bool:
        """
        Tiêu thụ đồng thời 2 Nonce trong duy nhất MỘT ACID Transaction (Compound Claim).
        Nếu một trong hai nonce đã tồn tại hoặc bị lỗi, toàn bộ transaction được Rollback lập tức.
        """
        if not nonce1 or not isinstance(nonce1, str) or not nonce1.strip():
            return False
        if not nonce2 or not isinstance(nonce2, str) or not nonce2.strip():
            return False

        n1 = nonce1.strip()
        n2 = nonce2.strip()
        if n1 == n2:
            return False

        now = time.time()
        expires_at = now + max(0.01, ttl_seconds)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM nonces WHERE expires_at < ?", (now,))
                conn.execute(
                    "INSERT INTO nonces (nonce, scope, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (n1, scope1.strip(), now, expires_at)
                )
                conn.execute(
                    "INSERT INTO nonces (nonce, scope, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (n2, scope2.strip(), now, expires_at)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                conn.rollback()
                return False
            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def check_and_use_single_nonce_with_two_scopes_atomic(
        self,
        nonce: str,
        scope1: str,
        scope2: str,
        ttl_seconds: float = 300.0
    ) -> bool:
        """
        Tiêu thụ MỘT nonce với HAI scope-prefix khác nhau trong 1 ACID transaction.
        Dùng khi approval_nonce == exec_nonce.
        """
        if not nonce or not isinstance(nonce, str) or not nonce.strip():
            return False
        n = nonce.strip()
        key1 = f"{scope1}_{n}"
        key2 = f"{scope2}_{n}"
        if key1 == key2:
            return False

        now = time.time()
        expires_at = now + max(0.01, ttl_seconds)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM nonces WHERE expires_at < ?", (now,))
                conn.execute(
                    "INSERT INTO nonces (nonce, scope, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (key1, scope1, now, expires_at)
                )
                conn.execute(
                    "INSERT INTO nonces (nonce, scope, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (key2, scope2, now, expires_at)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                conn.rollback()
                return False
            except Exception:
                conn.rollback()
                return False
            finally:
                conn.close()

    def is_nonce_used(self, nonce: str) -> bool:
        """Kiểm tra xem nonce đã từng được sử dụng chưa."""
        if not nonce or not isinstance(nonce, str):
            return True
        now = time.time()
        with self._lock:
            with closing(self._get_connection()) as conn:
                cursor = conn.execute("SELECT 1 FROM nonces WHERE nonce = ? AND expires_at >= ?", (nonce.strip(), now))
                return cursor.fetchone() is not None

    def record_lease_claim(self, lease_id: str, nonce: str, ttl_seconds: float = 120.0) -> bool:
        """Persist lease_id → nonce mapping tại thời điểm compound claim thành công."""
        if not lease_id or not nonce:
            return False
        now = time.time()
        expires_at = now + max(1.0, ttl_seconds)
        with self._lock:
            with closing(self._get_connection()) as conn:
                try:
                    conn.execute("DELETE FROM lease_claims WHERE expires_at < ?", (now,))
                    conn.execute(
                        "INSERT OR REPLACE INTO lease_claims (lease_id, nonce, claimed_at, expires_at) VALUES (?, ?, ?, ?)",
                        (lease_id.strip(), nonce.strip(), now, expires_at)
                    )
                    conn.commit()
                    return True
                except Exception:
                    return False

    def get_persisted_lease_nonce(self, lease_id: str) -> Optional[str]:
        """Lookup nonce của một lease_id đã từng được claim (persist trong SQLite)."""
        if not lease_id:
            return None
        now = time.time()
        with self._lock:
            with closing(self._get_connection()) as conn:
                cursor = conn.execute(
                    "SELECT nonce FROM lease_claims WHERE lease_id = ? AND expires_at >= ?",
                    (lease_id.strip(), now)
                )
                row = cursor.fetchone()
                return row[0] if row else None

    def prune_expired(self) -> int:
        """Xóa toàn bộ các nonce đã quá hạn khỏi database."""
        now = time.time()
        with self._lock:
            with closing(self._get_connection()) as conn:
                cursor = conn.execute("DELETE FROM nonces WHERE expires_at < ?", (now,))
                deleted = cursor.rowcount
                conn.execute("DELETE FROM lease_claims WHERE expires_at < ?", (now,))
                conn.commit()
                return deleted

    def clear_all_for_test(self) -> None:
        """Chỉ dùng trong unit test để reset database sạch."""
        with self._lock:
            with closing(self._get_connection()) as conn:
                conn.execute("DELETE FROM nonces")
                conn.execute("DELETE FROM lease_claims")
                conn.commit()
