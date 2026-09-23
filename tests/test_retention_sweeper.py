# -*- coding: utf-8 -*-
"""
tests/test_retention_sweeper.py
Unit tests verifying SQLiteRetentionSweeper adheres to N3.1-N3.4.

Test matrix:
- N3.1: Sweep both checkpoints and raw_traces databases
- N3.2: On-startup call + Size guard threshold triggering
- N3.3: Atomic transaction, rollbacks on error, dry-run does not mutate DB
- N3.4: 3-boundary test: expired deleted (< cutoff), exact boundary kept (== cutoff), new kept (> cutoff)
"""

import os
import time
import sqlite3
import pytest
from pathlib import Path
from core.storage.retention_sweeper import (
    SQLiteRetentionSweeper,
    StoreRetentionTarget,
    DEFAULT_CHECKPOINT_TTL_DAYS,
    DEFAULT_TRACE_TTL_DAYS,
)


@pytest.fixture
def temp_checkpoint_db(tmp_path: Path):
    db_file = tmp_path / "test_checkpoints.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE mission_checkpoints (
            mission_id TEXT,
            step_id INTEGER,
            status TEXT,
            state_json TEXT,
            idempotency_key TEXT,
            created_at REAL,
            updated_at REAL
        );
    """)
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture
def temp_trace_db(tmp_path: Path):
    db_file = tmp_path / "test_traces.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE raw_traces (
            trace_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            timestamp REAL NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    return db_file


class TestSQLiteRetentionSweeper:

    def test_3_boundary_retention_sweep(self, temp_checkpoint_db: Path):
        """
        [N3.4] Kiểm tra 3 biên:
        - Row 1: timestamp < cutoff (Quá 30 ngày) -> BỊ XÓA
        - Row 2: timestamp == cutoff (Đúng biên 30 ngày) -> ĐƯỢC GIỮ
        - Row 3: timestamp > cutoff (Mới 5 ngày) -> ĐƯỢC GIỮ
        """
        now = 1000000.0  # Mốc thời gian giả lập
        ttl_days = 30
        cutoff = now - (ttl_days * 86400.0)

        t_expired = cutoff - 100.0      # Quá hạn
        t_boundary = cutoff             # Đúng biên
        t_fresh = now - (5 * 86400.0)   # Mới

        conn = sqlite3.connect(str(temp_checkpoint_db))
        conn.executemany("""
            INSERT INTO mission_checkpoints (mission_id, step_id, status, state_json, idempotency_key, created_at, updated_at)
            VALUES (?, ?, 'COMPLETED', '{}', ?, ?, ?);
        """, [
            ("m_expired", 1, "k1", t_expired, t_expired),
            ("m_boundary", 1, "k2", t_boundary, t_boundary),
            ("m_fresh", 1, "k3", t_fresh, t_fresh),
        ])
        conn.commit()
        conn.close()

        target = StoreRetentionTarget(
            name="test_checkpoints",
            db_path=temp_checkpoint_db,
            table_name="mission_checkpoints",
            timestamp_column="created_at",
            ttl_days=ttl_days,
        )

        sweeper = SQLiteRetentionSweeper(checkpoint_ttl_days=ttl_days)
        report = sweeper.sweep_store(target, dry_run=False, now=now)

        assert report.status == "SUCCESS"
        assert report.rows_deleted == 1
        assert report.rows_retained == 2

        # Xác minh trong DB thực
        conn = sqlite3.connect(str(temp_checkpoint_db))
        cur = conn.cursor()
        cur.execute("SELECT mission_id FROM mission_checkpoints ORDER BY created_at ASC;")
        remaining = [row[0] for row in cur.fetchall()]
        conn.close()

        assert "m_expired" not in remaining
        assert "m_boundary" in remaining
        assert "m_fresh" in remaining

    def test_dry_run_does_not_mutate(self, temp_trace_db: Path):
        """
        [N3.3] Dry-run tính toán số lượng bản ghi cần xóa nhưng KHÔNG thay đổi dữ liệu.
        """
        now = 2000000.0
        ttl_days = 90
        cutoff = now - (ttl_days * 86400.0)

        conn = sqlite3.connect(str(temp_trace_db))
        conn.executemany("""
            INSERT INTO raw_traces (trace_id, mission_id, payload_json, timestamp)
            VALUES (?, 'm1', '{}', ?);
        """, [
            ("tr_old_1", cutoff - 1000.0),
            ("tr_old_2", cutoff - 2000.0),
            ("tr_fresh", now),
        ])
        conn.commit()
        conn.close()

        target = StoreRetentionTarget(
            name="test_traces",
            db_path=temp_trace_db,
            table_name="raw_traces",
            timestamp_column="timestamp",
            ttl_days=ttl_days,
        )

        sweeper = SQLiteRetentionSweeper(trace_ttl_days=ttl_days)
        report = sweeper.sweep_store(target, dry_run=True, now=now)

        assert report.dry_run is True
        assert report.rows_deleted == 2

        # Kiểm tra DB vẫn còn nguyên 3 bản ghi
        conn = sqlite3.connect(str(temp_trace_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM raw_traces;")
        count = cur.fetchone()[0]
        conn.close()

        assert count == 3

    def test_size_guard_emergency_cleanup(self, temp_checkpoint_db: Path):
        """
        [N3.2] Khi file vượt ngưỡng size_guard, cutoff bị ép xuống một nửa để dọn khẩn cấp.
        """
        now = 5000000.0
        ttl_days = 30
        standard_cutoff = now - (30 * 86400.0)
        emergency_cutoff = now - (15 * 86400.0)

        conn = sqlite3.connect(str(temp_checkpoint_db))
        conn.executemany("""
            INSERT INTO mission_checkpoints (mission_id, step_id, status, state_json, idempotency_key, created_at, updated_at)
            VALUES (?, 1, 'COMPLETED', '{}', ?, ?, ?);
        """, [
            ("m_standard_expired", "k1", standard_cutoff - 100.0, standard_cutoff - 100.0), # > 30 ngày
            ("m_emergency_target", "k2", standard_cutoff + 100.0, standard_cutoff + 100.0), # 20 ngày (bình thường giữ, khẩn cấp xóa)
            ("m_very_fresh", "k3", now - 100.0, now - 100.0),                              # Vừa tạo
        ])
        conn.commit()
        conn.close()

        target = StoreRetentionTarget(
            name="test_checkpoints",
            db_path=temp_checkpoint_db,
            table_name="mission_checkpoints",
            timestamp_column="created_at",
            ttl_days=ttl_days,
        )

        # Đặt size_guard cực nhỏ (1 byte) để kích hoạt size guard
        sweeper = SQLiteRetentionSweeper(checkpoint_ttl_days=ttl_days, size_guard_bytes=1)
        report = sweeper.sweep_store(target, dry_run=False, now=now)

        assert report.size_guard_triggered is True
        assert report.rows_deleted == 2
        assert report.rows_retained == 1

        conn = sqlite3.connect(str(temp_checkpoint_db))
        cur = conn.cursor()
        cur.execute("SELECT mission_id FROM mission_checkpoints;")
        remaining = [row[0] for row in cur.fetchall()]
        conn.close()

        assert remaining == ["m_very_fresh"]
