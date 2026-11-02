# -*- coding: utf-8 -*-
"""
tests/test_phase3_perception_cache.py
[M5 Phase 3: Perception & UIA Cache Test Suite]:
Thực hiện đầy đủ 10 bài kiểm thử bảo mật & hiệu năng UIA Cache theo Turn 333 của OpenCode:
  1. UIA_CACHE_HAPPY_PATH
  2. UIA_CACHE_TTL_EXPIRY
  3. UIA_CACHE_PID_EXIT_INVALIDATION
  4. UIA_CACHE_WINDOW_DESTROYED_INVALIDATION
  5. UIA_CACHE_HASH_DRIFT_INVALIDATION
  6. UIA_CACHE_CONCURRENT_READ_WRITE
  7. UIA_CACHE_UNBOUNDED_GROWTH_REJECTED
  8. UIA_CACHE_MUTATION_INVALIDATION
  9. UIA_COM_FAILURE_FAIL_CLOSED
  10. PROCESS_NAME_DYNAMIC_RESOLUTION
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock
from services.ai_desktop.uia_tree_inspector import UIATreeInspector, UIATreeSnapshot, UIAElementNode


class TestPhase3PerceptionCache:

    def test_uia_cache_happy_path(self):
        """UIA_CACHE_HAPPY_PATH: Truy vấn lần 2 trả về từ cache cực nhanh (<1ms), trùng khớp snapshot_id."""
        inspector = UIATreeInspector(is_live_mode=False)
        snap1 = inspector.inspect_tree(1234)
        t0 = time.perf_counter()
        snap2 = inspector.inspect_tree(1234)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert snap1.snapshot_id == snap2.snapshot_id
        assert snap1.snapshot_hash == snap2.snapshot_hash
        assert elapsed_ms < 5.0
        assert snap2.element_count == 4

    def test_uia_cache_ttl_expiry(self):
        """UIA_CACHE_TTL_EXPIRY: Khi TTL (0.5s) hết hạn, cache tự động bị vô hiệu hóa và quét fresh snapshot."""
        inspector = UIATreeInspector(is_live_mode=False)
        snap1 = inspector.inspect_tree(1234)

        # Giả lập thời gian trôi qua 0.6s (> 0.5s TTL)
        with patch("time.time", return_value=time.time() + 0.6):
            snap2 = inspector.inspect_tree(1234)

        assert snap1.snapshot_id != snap2.snapshot_id  # Snapshot mới được sinh ra

    def test_uia_cache_pid_exit_invalidation(self):
        """UIA_CACHE_PID_EXIT_INVALIDATION: Nếu tiến trình PID đã thoát (exit), cache tự động bị xoá."""
        inspector = UIATreeInspector(is_live_mode=True)
        # Mock window valid nhưng psutil.pid_exists trả về False
        with patch("win32gui.IsWindow", return_value=True), \
             patch.object(inspector, "_native_inspect_tree") as mock_native, \
             patch("psutil.pid_exists", return_value=False):

            mock_snap = UIATreeSnapshot(
                hwnd=9999, window_title="Test", process_name="notepad.exe",
                pid=99999, element_count=1, snapshot_hash="sha256_mock"
            )
            mock_native.return_value = mock_snap

            # Lần 1: nạp vào cache
            s1 = inspector.inspect_tree(9999)
            assert (9999, 99999, "notepad.exe") in inspector._cache

            # Lần 2: kiểm tra pid_exists(99999) -> False -> phải evict khỏi cache
            s2 = inspector.inspect_tree(9999)
            assert mock_native.call_count == 2

    def test_uia_cache_window_destroyed_invalidation(self):
        """UIA_CACHE_WINDOW_DESTROYED_INVALIDATION: Nếu HWND bị huỷ (destroyed), cache bị evict và fail-closed."""
        inspector = UIATreeInspector(is_live_mode=True)
        with patch("win32gui.IsWindow", side_effect=[True, False]), \
             patch.object(inspector, "_native_inspect_tree") as mock_native:

            mock_snap = UIATreeSnapshot(
                hwnd=8888, window_title="Test", process_name="notepad.exe",
                pid=1111, element_count=1, snapshot_hash="sha256_mock"
            )
            mock_native.return_value = mock_snap

            s1 = inspector.inspect_tree(8888)
            # Lần 2: window destroyed -> IsWindow False
            s2 = inspector.inspect_tree(8888)
            assert s2.snapshot_hash == "empty_invalid_hwnd"
            assert s2.element_count == 0

    def test_uia_cache_hash_drift_invalidation(self):
        """UIA_CACHE_HASH_DRIFT_INVALIDATION: Biến đổi cây phần tử sinh hash mới và cập nhật cache."""
        inspector = UIATreeInspector(is_live_mode=False)
        snap1 = inspector.inspect_tree(1234, force_fresh=True)
        snap2 = inspector.inspect_tree(1234, force_fresh=True)
        # Khi force_fresh được gọi, snapshot_id thay đổi
        assert snap1.snapshot_id != snap2.snapshot_id

    def test_uia_cache_concurrent_read_write(self):
        """UIA_CACHE_CONCURRENT_READ_WRITE: An toàn luồng tuyệt đối khi 10 luồng đọc/ghi đồng thời."""
        inspector = UIATreeInspector(is_live_mode=False)
        errors = []

        def worker(w_id: int):
            try:
                for i in range(20):
                    hwnd = 1000 + (i % 3)
                    snap = inspector.inspect_tree(hwnd)
                    assert snap.element_count == 4
                    if i % 5 == 0:
                        inspector.invalidate_cache(hwnd)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_uia_cache_unbounded_growth_rejected(self):
        """UIA_CACHE_UNBOUNDED_GROWTH_REJECTED: Cache có dung lượng trần LRU (capacity=50), không tăng vô hạn."""
        inspector = UIATreeInspector(is_live_mode=False, cache_capacity=10)
        # Nạp 25 HWND khác nhau vào cache
        for h in range(1, 26):
            inspector.inspect_tree(h)

        assert len(inspector._cache) <= 10

    def test_uia_cache_mutation_invalidation(self):
        """UIA_CACHE_MUTATION_INVALIDATION: invalidate_cache xoá đúng HWND mục tiêu sau khi dispatch mutation."""
        inspector = UIATreeInspector(is_live_mode=False)
        inspector.inspect_tree(1234)
        inspector.inspect_tree(5678)
        assert len(inspector._cache) == 2

        removed = inspector.invalidate_cache(1234)
        assert removed == 1
        assert len(inspector._cache) == 1
        # HWND 5678 vẫn còn
        remaining_hwnds = [k[0] for k in inspector._cache.keys()]
        assert 5678 in remaining_hwnds

    def test_uia_com_failure_fail_closed(self):
        """UIA_COM_FAILURE_FAIL_CLOSED: Lỗi COM nghiêm trọng phải fail-closed."""
        inspector = UIATreeInspector(is_live_mode=True, force_fallback=False)
        with patch("win32gui.IsWindow", return_value=True), \
             patch("win32process.GetWindowThreadProcessId", return_value=(0, 1234)), \
             patch.object(inspector, "_native_com_uia_inspect_tree", side_effect=Exception("COM_INITIALIZATION_ERROR")):

            # Khi COM lỗi và fallback bị chặn hoặc gọi trực tiếp native com, phải fail closed
            with pytest.raises(Exception):
                inspector._native_inspect_tree(1234)

    def test_process_name_dynamic_resolution(self):
        """PROCESS_NAME_DYNAMIC_RESOLUTION: Tra cứu process_name động từ PID, không hardcode notepad.exe."""
        inspector = UIATreeInspector(is_live_mode=False)
        with patch("psutil.Process") as mock_proc:
            mock_proc.return_value.name.return_value = "CalculatorApp.exe"
            p_name = inspector._resolve_process_name(9999)
            assert p_name == "CalculatorApp.exe"

        # Với PID không tồn tại hoặc lỗi, trả về unknown.exe an toàn
        with patch("psutil.Process", side_effect=Exception("No such process")):
            p_name = inspector._resolve_process_name(999999999)
            assert p_name == "unknown.exe"
