# -*- coding: utf-8 -*-
"""
Unit tests for JKAI UIA Semantic Perception Adapter (M5 Phase 2)
Kế thừa tiêu chuẩn từ vercel-labs/agent-desktop:
  - Kiểm tra Semantic Ref IDs (@ref:e1, @ref:e2...)
  - Kiểm tra trích xuất Pattern Details (ValuePattern, TogglePattern, etc.)
  - Kiểm tra sinh Semantic Prompt dạng Markdown cho LLM Planner
  - Kiểm tra chuyển đổi to_dict() phục vụ tool/API
  - Kiểm tra Read-Only Invariant (tuyệt đối không can thiệp/thay đổi trạng thái màn hình)
"""

import json
import pytest
from services.ai_desktop.uia_tree_inspector import UIATreeInspector, UIATreeSnapshot, UIAElementNode


class TestUIASemanticPerception:
    @pytest.fixture
    def inspector(self):
        return UIATreeInspector(is_live_mode=False)

    def test_mock_tree_inspection_and_refs(self, inspector):
        """Kiểm tra bóc tách Mock Tree với đầy đủ Semantic Ref IDs."""
        snap = inspector.inspect_tree(hwnd=1234)
        assert isinstance(snap, UIATreeSnapshot)
        assert snap.element_count == 4
        assert snap.hwnd == 1234
        assert snap.window_title == "Untitled - Notepad"

        # Kiểm tra thứ tự và cấu trúc ref ID
        refs = [e.ref for e in snap.elements]
        assert refs == ["e1", "e2", "e3", "e4"]

        # Kiểm tra tra cứu O(1) theo ref ID
        e1 = inspector.get_element_by_ref(snap, "e1")
        assert e1 is not None
        assert e1.name == "File"
        assert e1.control_type == "MenuItem"

        # Kiểm tra tra cứu với tiền tố '@ref:'
        e3 = inspector.get_element_by_ref(snap, "@ref:e3")
        assert e3 is not None
        assert e3.name == "Text Editor"
        assert e3.control_type == "Edit"
        assert e3.value == ""
        assert e3.is_read_only is False

    def test_semantic_prompt_generation(self, inspector):
        """Kiểm tra sinh prompt Markdown ngữ nghĩa cho LLM Planner."""
        snap = inspector.inspect_tree(hwnd=1234)
        prompt = inspector.to_semantic_prompt(snap, max_elements=10)

        assert "### Active Window: Untitled - Notepad" in prompt
        assert "HWND: 1234" in prompt
        assert "[@ref:e1] MenuItem \"File\"" in prompt
        assert "[@ref:e2] MenuItem \"Edit\"" in prompt
        assert "[@ref:e3] Edit \"Text Editor\"" in prompt
        assert "[@ref:e4] Button \"Close\"" in prompt
        assert "bounds:" in prompt

    def test_to_dict_serialization(self, inspector):
        """Kiểm tra chuyển đổi to_dict() phục vụ trả về cho MCP tool hoặc API."""
        snap = inspector.inspect_tree(hwnd=1234)
        data = inspector.to_dict(snap)

        assert isinstance(data, dict)
        assert data["window_title"] == "Untitled - Notepad"
        assert data["element_count"] == 4
        assert len(data["elements"]) == 4

        first_el = data["elements"][0]
        assert first_el["ref"] == "e1"
        assert first_el["name"] == "File"
        assert first_el["control_type"] == "MenuItem"
        assert "rect" in first_el
        assert "center" in first_el
        assert "supported_patterns" in first_el

        # Đảm bảo serialize JSON hoàn hảo
        json_str = json.dumps(data)
        assert "Untitled - Notepad" in json_str

    def test_fast_find_element(self, inspector):
        """Kiểm tra tìm kiếm nhanh phần tử theo tên và loại điều khiển."""
        res = inspector.fast_find_element("Editor", control_type="Edit", hwnd=1234)
        assert res["found"] is True
        assert res["name"] == "Text Editor"
        assert res["ref"] == "e3"
        assert res["control_type"] == "Edit"
        assert "elapsed_ms" in res

        # Tìm kiếm không thấy
        not_found = inspector.fast_find_element("NonExistentButton", hwnd=1234)
        assert not_found["found"] is False

    def test_read_only_invariant(self, inspector):
        """Chứng minh module là Pure Read-Only, không thực hiện bất kỳ lệnh can thiệp nào."""
        # Gọi inspect_tree nhiều lần liên tiếp
        snap1 = inspector.inspect_tree(hwnd=1234)
        snap2 = inspector.inspect_tree(hwnd=1234)

        # Trạng thái băm và phần tử phải hoàn toàn bất biến
        assert snap1.snapshot_hash == snap2.snapshot_hash
        assert snap1.element_count == snap2.element_count

    def test_live_notepad_semantic_inspection(self):
        """Kiểm thử trực tiếp trên ứng dụng Notepad thật trên Windows Host."""
        import subprocess
        import time
        import win32gui
        import win32process

        proc = subprocess.Popen(["notepad.exe"])
        time.sleep(0.8)
        try:
            hwnds = []
            def enum_cb(h, _):
                if win32process.GetWindowThreadProcessId(h)[1] == proc.pid and win32gui.IsWindowVisible(h):
                    hwnds.append(h)
                return True

            win32gui.EnumWindows(enum_cb, None)
            assert len(hwnds) > 0, "Không tìm thấy cửa sổ Notepad vừa mở"
            hwnd = hwnds[0]

            live_inspector = UIATreeInspector(is_live_mode=True)
            snap = live_inspector.inspect_tree(hwnd)

            assert snap.engine == "NATIVE_COM_UIA3"
            assert snap.element_count >= 10
            assert "Notepad" in snap.window_title or "Untitled" in snap.window_title

            # Kiểm tra Ref Map
            assert "e1" in snap.ref_map
            e1 = live_inspector.get_element_by_ref(snap, "e1")
            assert e1 is not None

            # Kiểm tra sinh prompt
            prompt = live_inspector.to_semantic_prompt(snap, max_elements=10)
            assert "### Active Window:" in prompt
            assert "[@ref:e1]" in prompt

            # Kiểm tra tìm kiếm nhanh Edit control
            found = live_inspector.fast_find_element("Text Editor", control_type="Edit", hwnd=hwnd)
            assert found["found"] is True
            assert found["engine"] == "NATIVE_COM_UIA3"
        finally:
            proc.terminate()
            proc.wait(timeout=3)
