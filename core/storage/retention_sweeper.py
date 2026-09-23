# -*- coding: utf-8 -*-
"""
🏛️ SQLITE RETENTION SWEEPER (SSoT RETENTION POLICY)
File: core/storage/retention_sweeper.py
Version: SDS v26.5 (P1-N3 Infrastructure Hardening)

Tuân thủ nghiêm ngặt 4 điều kiện ràng buộc của Opencode (Turn 52):
- N3.1: Sweep cả 3 stores:
    1) data/checkpoints/jkai_checkpoints.db (Checkpoints > 30 ngày)
    2) intelligence/raw_traces.db (Raw Traces > 90 ngày)
    3) services/ai-executor/intelligence/raw_traces.db (Worker Traces > 90 ngày)
- N3.2: Trigger = on-startup + size-guard (>100MB quét bất kể tuổi). CẤM daemon/cron loop mới.
- N3.3: Transaction atomic (BEGIN IMMEDIATE / COMMIT / ROLLBACK) + log COUNT xóa/giữ + dry_run flag.
- N3.4: Hỗ trợ kiểm thử 3 biên: row quá hạn bị xóa, row mới giữ lại, row đúng biên thời gian giữ lại.
"""

from __future__ import annotations

import os
import time
import sqlite3
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("JKAI.RetentionSweeper")

DEFAULT_CHECKPOINT_TTL_DAYS = 30
DEFAULT_TRACE_TTL_DAYS = 90
SIZE_GUARD_THRESHOLD_BYTES = 100 * 1024 * 1024  # 100 MB


@dataclass
class StoreRetentionTarget:
    name: str
    db_path: Path
    table_name: str
    timestamp_column: str
    ttl_days: int
    is_unix_timestamp: bool = True  # True: epoch float/int; False: ISO-8601 string


@dataclass
class SweepReport:
    store_name: str
    db_path: str
    exists: bool
    size_before_bytes: int
    size_after_bytes: int
    rows_deleted: int
    rows_retained: int
    size_guard_triggered: bool
    dry_run: bool
    status: str = "SUCCESS"
    error_message: Optional[str] = None


class SQLiteRetentionSweeper:
    """
    🧹 Bộ dọn dẹp dữ liệu lưu trữ SQLite tập trung theo chính sách thống nhất.
    """

    def __init__(
        self,
        checkpoint_ttl_days: int = DEFAULT_CHECKPOINT_TTL_DAYS,
        trace_ttl_days: int = DEFAULT_TRACE_TTL_DAYS,
        size_guard_bytes: int = SIZE_GUARD_THRESHOLD_BYTES,
    ):
        self.checkpoint_ttl_days = checkpoint_ttl_days
        self.trace_ttl_days = trace_ttl_days
        self.size_guard_bytes = size_guard_bytes

        # N3.1: Danh sách các store cần quản lý vòng đời
        self.targets: List[StoreRetentionTarget] = [
            StoreRetentionTarget(
                name="checkpoints",
                db_path=Path("data/checkpoints/jkai_checkpoints.db"),
                table_name="mission_checkpoints",
                timestamp_column="created_at",
                ttl_days=self.checkpoint_ttl_days,
                is_unix_timestamp=True,
            ),
            StoreRetentionTarget(
                name="raw_traces_host",
                db_path=Path("intelligence/raw_traces.db"),
                table_name="raw_traces",
                timestamp_column="timestamp",
                ttl_days=self.trace_ttl_days,
                is_unix_timestamp=True,
            ),
            StoreRetentionTarget(
                name="raw_traces_executor",
                db_path=Path("services/ai-executor/intelligence/raw_traces.db"),
                table_name="raw_traces",
                timestamp_column="timestamp",
                ttl_days=self.trace_ttl_days,
                is_unix_timestamp=True,
            ),
        ]

    def _get_file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0

    def sweep_store(
        self,
        target: StoreRetentionTarget,
        dry_run: bool = False,
        now: Optional[float] = None
    ) -> SweepReport:
        current_time = now if now is not None else time.time()
        size_before = self._get_file_size(target.db_path)

        if not target.db_path.exists():
            return SweepReport(
                store_name=target.name,
                db_path=str(target.db_path),
                exists=False,
                size_before_bytes=0,
                size_after_bytes=0,
                rows_deleted=0,
                rows_retained=0,
                size_guard_triggered=False,
                dry_run=dry_run,
                status="SKIPPED_NOT_FOUND"
            )

        size_guard_triggered = size_before >= self.size_guard_bytes
        cutoff_timestamp = current_time - (target.ttl_days * 86400.0)

        # N3.3: Transaction atomic
        conn = None
        try:
            conn = sqlite3.connect(str(target.db_path), timeout=30.0)
            conn.execute("PRAGMA foreign_keys = ON;")

            # Đếm tổng số bản ghi hiện tại
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {target.table_name};")
            total_before = cur.fetchone()[0]

            # Xác định các bản ghi quá hạn:
            # - Theo tuổi chuẩn: timestamp < cutoff_timestamp
            # - Hoặc nếu size guard kích hoạt: hạ cutoff xuống một nửa để giải phóng khẩn cấp
            active_cutoff = cutoff_timestamp
            if size_guard_triggered:
                # Ép dọn sớm hơn để cứu dung lượng ổ đĩa
                active_cutoff = current_time - ((target.ttl_days / 2) * 86400.0)
                logger.warning(
                    f"[SIZE-GUARD] Store '{target.name}' vượt ngưỡng {self.size_guard_bytes/(1024*1024):.1f}MB "
                    f"(hiện tại: {size_before/(1024*1024):.2f}MB). Kích hoạt dọn dẹp khẩn cấp."
                )

            # Đếm số lượng sẽ xóa
            count_query = f"SELECT COUNT(*) FROM {target.table_name} WHERE {target.timestamp_column} < ?;"
            cur.execute(count_query, (active_cutoff,))
            rows_to_delete = cur.fetchone()[0]

            if not dry_run and rows_to_delete > 0:
                conn.execute("BEGIN IMMEDIATE;")
                delete_query = f"DELETE FROM {target.table_name} WHERE {target.timestamp_column} < ?;"
                conn.execute(delete_query, (active_cutoff,))
                conn.commit()
                # Tối ưu hóa file nếu xóa nhiều
                if rows_to_delete > 100:
                    try:
                        conn.execute("PRAGMA incremental_vacuum;")
                    except Exception:
                        pass
                logger.info(
                    f"[RETENTION] Store '{target.name}': Đã xóa {rows_to_delete} bản ghi quá hạn (< {active_cutoff})."
                )
            elif dry_run:
                logger.info(
                    f"[DRY-RUN] Store '{target.name}': Sẽ xóa {rows_to_delete} / {total_before} bản ghi."
                )

            rows_retained = total_before - rows_to_delete
            size_after = self._get_file_size(target.db_path)

            return SweepReport(
                store_name=target.name,
                db_path=str(target.db_path),
                exists=True,
                size_before_bytes=size_before,
                size_after_bytes=size_after,
                rows_deleted=rows_to_delete,
                rows_retained=rows_retained,
                size_guard_triggered=size_guard_triggered,
                dry_run=dry_run,
                status="SUCCESS"
            )

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"[RETENTION-ERROR] Thất bại khi quét store '{target.name}': {e}", exc_info=True)
            return SweepReport(
                store_name=target.name,
                db_path=str(target.db_path),
                exists=True,
                size_before_bytes=size_before,
                size_after_bytes=size_before,
                rows_deleted=0,
                rows_retained=0,
                size_guard_triggered=size_guard_triggered,
                dry_run=dry_run,
                status="FAILED",
                error_message=str(e)
            )
        finally:
            if conn:
                conn.close()

    def sweep_all(self, dry_run: bool = False, now: Optional[float] = None) -> List[SweepReport]:
        """Quét tất cả các store SQLite đã đăng ký."""
        reports = []
        for target in self.targets:
            reports.append(self.sweep_store(target, dry_run=dry_run, now=now))
        return reports


# Singleton & convenience runner
_sweeper_instance: Optional[SQLiteRetentionSweeper] = None

def get_retention_sweeper() -> SQLiteRetentionSweeper:
    global _sweeper_instance
    if _sweeper_instance is None:
        _sweeper_instance = SQLiteRetentionSweeper()
    return _sweeper_instance

def run_startup_retention_sweep(dry_run: bool = False) -> List[SweepReport]:
    """Hàm chạy on-startup được cắm vào entrypoint hệ thống (N3.2)."""
    sweeper = get_retention_sweeper()
    return sweeper.sweep_all(dry_run=dry_run)
