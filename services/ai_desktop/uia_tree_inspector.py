# -*- coding: utf-8 -*-
"""
Windows UI Automation (UIA) Tree Inspector for JKAI Desktop Actuator (M5)
Kế thừa và chuẩn hóa từ:
  - vercel-labs/agent-desktop (Semantic UIA Element Tree & Stable Ref IDs: @ref:e1, @ref:e2)
  - Jeomon/Windows-Use (Accessibility Tree + Accessibility ID / Patterns)
  - simular-ai/Agent-S (AOM / Accessibility Observation Model)

Bóc tách cây phần tử giao diện Windows thông qua:
  1. Primary: Native Windows UIAutomation COM Interface (IUIAutomation via UIAutomationCore.dll)
  2. Fallback: Win32 Accessibility Child Enumeration
  3. Features:
     - Automation ID, Control Type, Name, ClassName, Bounding Rect, Center
     - Stable Short Ref IDs (e.g. "e1", "e2", "e3"...) cho LLM Planner dễ dàng trỏ mục tiêu
     - Pattern Details: Giá trị text (ValuePattern), cờ chỉ đọc, trạng thái Toggle (On/Off), Selection, Expand/Collapse
     - Semantic Prompt Generation: Tạo Markdown ngữ nghĩa tinh gọn cho LLM
     - Fast Query: Tra cứu phần tử <3ms không cần chụp ảnh màn hình
     - Snapshot Hash: Mã băm SHA-256 đại diện cho trạng thái cây phần tử, chống TOCTOU
"""

from dataclasses import dataclass, field
from collections import OrderedDict
import hashlib
import json
import os
import threading
import time
import uuid
from .semantic_action_ir import compute_canonical_element_hash, compute_canonical_snapshot_hash
from .uia_cache import build_tree_cache_request, find_all_cached, read_element as read_uia_element
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class UIAElementNode:
    name: str
    control_type: str
    automation_id: str
    class_name: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    center: Tuple[int, int]
    hwnd: int
    is_enabled: bool = True
    is_visible: bool = True
    supported_patterns: List[str] = field(default_factory=list)
    element_hash: str = ""
    # Mở rộng cho Semantic Computer Use:
    ref: str = ""  # ID tham chiếu ngắn ổn định (e.g. 'e1', 'e2')
    value: Optional[str] = None  # Nội dung text/giá trị (từ ValuePattern / TextPattern)
    is_read_only: Optional[bool] = None  # Cờ chỉ đọc
    toggle_state: Optional[str] = None  # Trạng thái On / Off / Indeterminate (từ TogglePattern)
    is_selected: Optional[bool] = None  # True / False (từ SelectionItemPattern)
    expand_state: Optional[str] = None  # Expanded / Collapsed / Leaf (từ ExpandCollapsePattern)

    def __post_init__(self):
        if not self.element_hash:
            self.element_hash = compute_canonical_element_hash(
                name=self.name,
                control_type=self.control_type,
                automation_id=self.automation_id,
                class_name=self.class_name,
                rect=self.rect
            )


@dataclass
class UIATreeSnapshot:
    hwnd: int
    window_title: str
    process_name: str
    pid: int
    element_count: int
    snapshot_hash: str
    engine: str = "WIN32_ACCESSIBILITY_FALLBACK"  # NATIVE_COM_UIA3 hoặc WIN32_ACCESSIBILITY_FALLBACK
    elements: List[UIAElementNode] = field(default_factory=list)
    ref_map: Dict[str, UIAElementNode] = field(default_factory=dict)  # Tra cứu O(1) theo ref ID ('e1', 'e2')
    snapshot_id: str = ""
    captured_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        if not self.expires_at:
            self.expires_at = self.captured_at + 0.5  # Policy-owned TTL 0.5s
        if not self.element_count:
            self.element_count = len(self.elements)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def elements_count(self) -> int:
        return self.element_count

    def find_by_ref(self, ref: str) -> Optional[UIAElementNode]:
        return self.ref_map.get(ref)

    def find_by_automation_id(self, auto_id: str) -> Optional[UIAElementNode]:
        for el in self.elements:
            if el.automation_id == auto_id:
                return el
        return None

    def find_by_name(self, name: str, case_sensitive: bool = False) -> List[UIAElementNode]:
        target = name if case_sensitive else name.lower()
        return [el for el in self.elements if (name in el.name if case_sensitive else target in el.name.lower())]


UIA_CONTROL_TYPE_MAP = {
    50000: "Button",
    50001: "Calendar",
    50002: "CheckBox",
    50003: "ComboBox",
    50004: "Edit",
    50005: "Hyperlink",
    50006: "Image",
    50007: "ListItem",
    50008: "List",
    50009: "Menu",
    50010: "MenuBar",
    50011: "MenuItem",
    50012: "ProgressBar",
    50013: "RadioButton",
    50014: "ScrollBar",
    50015: "Slider",
    50016: "Spinner",
    50017: "StatusBar",
    50018: "Tab",
    50019: "TabItem",
    50020: "Text",
    50021: "ToolBar",
    50022: "ToolTip",
    50023: "Tree",
    50024: "TreeItem",
    50025: "Custom",
    50026: "Group",
    50027: "Thumb",
    50028: "DataGrid",
    50029: "DataItem",
    50030: "Document",
    50031: "SplitButton",
    50032: "Window",
    50033: "Pane",
    50034: "Header",
    50035: "HeaderItem",
    50036: "Table",
    50037: "TitleBar",
    50038: "Separator",
    50039: "SemanticZoom",
    50040: "AppBar",
}


class UIATreeInspector:
    """
    Bộ bóc tách và phân tích cây trợ năng Windows (UIA Semantic Perception Adapter).
    Hỗ trợ Native COM UIA3 và Win32 Fallback.
    """

    def __init__(self, is_live_mode: bool = False, force_fallback: bool = False, cache_ttl_seconds: float = 0.5, cache_capacity: int = 50):
        self.is_live_mode = is_live_mode
        self.force_fallback = force_fallback
        self.cache_ttl_seconds = 0.5  # Policy-owned invariant: 0.5s
        self.cache_capacity = cache_capacity  # Bounded LRU capacity
        self.engine_name = "WIN32_ACCESSIBILITY_FALLBACK"
        self._lock = threading.Lock()
        self._cache: OrderedDict[Tuple[int, int, str], Tuple[float, UIATreeSnapshot]] = OrderedDict()

    @staticmethod
    def _resolve_process_name(pid: int) -> str:
        """Truy vấn định danh process name động từ PID thực tế, tuyệt đối không hardcode."""
        if pid <= 0:
            return ""
        try:
            import psutil
            p = psutil.Process(pid)
            return p.name()
        except Exception:
            pass
        try:
            import win32api
            import win32process
            # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000, PROCESS_VM_READ = 0x0010
            h_proc = win32api.OpenProcess(0x1000 | 0x0010, False, pid)
            if h_proc:
                try:
                    mod_name = win32process.GetModuleFileNameEx(h_proc, 0)
                    return os.path.basename(mod_name)
                finally:
                    win32api.CloseHandle(h_proc)
        except Exception:
            pass
        return "unknown.exe"

    def invalidate_cache(self, hwnd: Optional[int] = None) -> int:
        """Xoá cache thủ công hoặc tự động sau khi mutation dispatch thực thi."""
        with self._lock:
            if hwnd is None:
                count = len(self._cache)
                self._cache.clear()
                return count
            keys_to_del = [k for k in self._cache.keys() if k[0] == hwnd]
            for k in keys_to_del:
                del self._cache[k]
            return len(keys_to_del)

    @staticmethod
    def _infer_control_type(class_name: str, name: str) -> str:
        """Suy luận ControlType từ Win32 ClassName và đặc trưng phần tử."""
        c = class_name.lower().strip()
        if "edit" in c or "rich" in c:
            return "Edit"
        elif "button" in c:
            return "Button"
        elif "menu" in c:
            return "MenuItem"
        elif "list" in c:
            return "List"
        elif "tree" in c:
            return "Tree"
        elif "combo" in c:
            return "ComboBox"
        elif "scroll" in c:
            return "ScrollBar"
        elif "static" in c:
            return "Text"
        return "Pane"

    @staticmethod
    def _query_native_patterns(el) -> List[str]:
        """Truy vấn các UI Patterns thực tế được phần tử hỗ trợ qua COM GetCurrentPattern."""
        patterns, _ = UIATreeInspector._extract_com_pattern_details(el)
        return patterns

    @staticmethod
    def _extract_com_pattern_details(el) -> Tuple[List[str], Dict[str, Any]]:
        """Truy vấn các UI Patterns thực tế và bóc tách dữ liệu ngữ nghĩa (value, toggle, selection, expand)."""
        patterns = []
        details: Dict[str, Any] = {
            "value": None,
            "is_read_only": None,
            "toggle_state": None,
            "is_selected": None,
            "expand_state": None
        }

        # 1. ValuePattern (10002)
        try:
            val_ptr = el.GetCurrentPattern(10002)
            if bool(val_ptr):
                patterns.append("ValuePattern")
                from comtypes.gen.UIAutomationClient import IUIAutomationValuePattern
                val_obj = val_ptr.QueryInterface(IUIAutomationValuePattern)
                details["value"] = str(val_obj.CurrentValue or "")
                details["is_read_only"] = bool(val_obj.CurrentIsReadOnly)
        except Exception:
            pass

        # 2. InvokePattern (10000)
        try:
            inv_ptr = el.GetCurrentPattern(10000)
            if bool(inv_ptr):
                patterns.append("InvokePattern")
        except Exception:
            pass

        # 3. TogglePattern (10015)
        try:
            tog_ptr = el.GetCurrentPattern(10015)
            if bool(tog_ptr):
                patterns.append("TogglePattern")
                from comtypes.gen.UIAutomationClient import IUIAutomationTogglePattern
                tog_obj = tog_ptr.QueryInterface(IUIAutomationTogglePattern)
                st = tog_obj.CurrentToggleState
                # ToggleState_Off = 0, ToggleState_On = 1, ToggleState_Indeterminate = 2
                details["toggle_state"] = "On" if st == 1 else ("Off" if st == 0 else "Indeterminate")
        except Exception:
            pass

        # 4. SelectionItemPattern (10010)
        try:
            sel_ptr = el.GetCurrentPattern(10010)
            if bool(sel_ptr):
                patterns.append("SelectionItemPattern")
                from comtypes.gen.UIAutomationClient import IUIAutomationSelectionItemPattern
                sel_obj = sel_ptr.QueryInterface(IUIAutomationSelectionItemPattern)
                details["is_selected"] = bool(sel_obj.CurrentIsSelected)
        except Exception:
            pass

        # 5. ExpandCollapsePattern (10005)
        try:
            exp_ptr = el.GetCurrentPattern(10005)
            if bool(exp_ptr):
                patterns.append("ExpandCollapsePattern")
                from comtypes.gen.UIAutomationClient import IUIAutomationExpandCollapsePattern
                exp_obj = exp_ptr.QueryInterface(IUIAutomationExpandCollapsePattern)
                exp_st = exp_obj.CurrentExpandCollapseState
                # ExpandCollapseState_Collapsed = 0, ExpandCollapseState_Expanded = 1, Partially = 2, LeafNode = 3
                details["expand_state"] = "Expanded" if exp_st == 1 else ("Collapsed" if exp_st == 0 else "PartiallyExpanded")
        except Exception:
            pass

        # 6. ScrollPattern (10004)
        try:
            scr_ptr = el.GetCurrentPattern(10004)
            if bool(scr_ptr):
                patterns.append("ScrollPattern")
        except Exception:
            pass

        # 7. TextPattern (10014)
        try:
            txt_ptr = el.GetCurrentPattern(10014)
            if bool(txt_ptr):
                patterns.append("TextPattern")
        except Exception:
            pass

        # 8. LegacyIAccessiblePattern (10018)
        try:
            leg_ptr = el.GetCurrentPattern(10018)
            if bool(leg_ptr):
                patterns.append("LegacyIAccessiblePattern")
        except Exception:
            pass

        return patterns, details

    @staticmethod
    def _infer_supported_patterns(control_type: str) -> List[str]:
        """Suy luận các UI Patterns hỗ trợ dựa trên ControlType."""
        ct = control_type.lower()
        patterns = []
        if ct in ["button", "menuitem"]:
            patterns.append("InvokePattern")
        if ct in ["edit", "combobox"]:
            patterns.append("ValuePattern")
            patterns.append("TextPattern")
        if ct in ["checkbox", "radiobutton"]:
            patterns.append("TogglePattern")
        if ct in ["list", "tree"]:
            patterns.append("SelectionPattern")
            patterns.append("ScrollPattern")
        return patterns

    def fast_find_element(
        self,
        target_name: str,
        control_type: Optional[str] = None,
        hwnd: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fast-Path Semantic Query (<3ms) tìm kiếm phần tử giao diện bằng UIA3 (Thuần Read-Only)."""
        target_hwnd = hwnd
        if not target_hwnd or target_hwnd <= 0:
            import win32gui
            target_hwnd = win32gui.GetForegroundWindow() or win32gui.GetDesktopWindow()

        snap = self.inspect_tree(target_hwnd)
        matches = []
        t_lower = target_name.lower().strip()
        ct_lower = control_type.lower().strip() if control_type else None

        for el in snap.elements:
            name_match = t_lower in el.name.lower() or t_lower in el.automation_id.lower()
            ct_match = True if not ct_lower else (el.control_type.lower() == ct_lower)
            if name_match and ct_match:
                matches.append({
                    "ref": el.ref,
                    "name": el.name,
                    "control_type": el.control_type,
                    "automation_id": el.automation_id,
                    "rect": list(el.rect),
                    "center": list(el.center),
                    "is_enabled": el.is_enabled,
                    "supported_patterns": el.supported_patterns
                })

        return {
            "status": "SUCCESS" if matches else "NOT_FOUND",
            "hwnd": target_hwnd,
            "count": len(matches),
            "matches": matches,
            "snapshot_hash": snap.snapshot_hash
        }

    def get_active_window_tree(self) -> UIATreeSnapshot:
        """Quét và sinh Snapshot cho cửa sổ đang ở foreground (kích hoạt hiện tại)."""
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindow(hwnd):
            hwnd = win32gui.GetDesktopWindow()
        return self.inspect_tree(hwnd)

    def inspect_tree(self, hwnd: int, force_fresh: bool = False) -> UIATreeSnapshot:
        """
        Quét và sinh Snapshot toàn diện cho cây phần tử của HWND.
        Hỗ trợ Caching có TTL (0.5s), an toàn luồng, Bounded LRU, và tự động invalidate khi cửa sổ đóng / PID thoát.
        """
        now = time.time()

        # 1. Kiểm tra tính hợp lệ của HWND nếu ở live mode (Fail-Closed)
        if self.is_live_mode:
            try:
                import win32gui
                if not win32gui.IsWindow(hwnd):
                    self.invalidate_cache(hwnd)
                    return UIATreeSnapshot(
                        hwnd=hwnd,
                        window_title="",
                        process_name="",
                        pid=0,
                        element_count=0,
                        snapshot_hash="empty_invalid_hwnd",
                        engine=self.engine_name,
                        elements=[],
                        ref_map={}
                    )
            except Exception:
                pass

        # 2. Kiểm tra Cache với Lock an toàn luồng
        with self._lock:
            cached_key = None
            for key in list(self._cache.keys()):
                if key[0] == hwnd:
                    cached_key = key
                    break

            if cached_key and not force_fresh:
                ts, snap = self._cache[cached_key]
                # Kiểm tra TTL 0.5s
                if now - ts < self.cache_ttl_seconds and not snap.is_expired:
                    # Kiểm tra live PID nếu ở live mode
                    pid_alive = True
                    if self.is_live_mode:
                        try:
                            import psutil
                            if not psutil.pid_exists(snap.pid):
                                pid_alive = False
                        except Exception:
                            pass
                    if pid_alive:
                        self._cache.move_to_end(cached_key)
                        return snap
                    else:
                        del self._cache[cached_key]
                else:
                    # Hết hạn TTL
                    del self._cache[cached_key]

        # 3. Quét fresh snapshot
        if not self.is_live_mode:
            snap = self._mock_inspect_tree(hwnd)
        else:
            snap = self._native_inspect_tree(hwnd)

        # 4. Ghi cache với composite key (hwnd, pid, process_name) và LRU eviction
        with self._lock:
            key = (hwnd, snap.pid, snap.process_name)
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (now, snap)
            while len(self._cache) > self.cache_capacity:
                self._cache.popitem(last=False)

        return snap

    def _native_inspect_tree(self, hwnd: int) -> UIATreeSnapshot:
        """Bóc tách cây phần tử thật trên Windows Host.
        Ưu tiên sử dụng COM Native UIAutomation (IUIAutomation via UIAutomationCore.dll),
        tự động fallback về Win32 EnumChildWindows nếu COM UIA không khả dụng."""
        if not self.force_fallback:
            com_snap = self._native_com_uia_inspect_tree(hwnd)
            if com_snap is not None:
                return com_snap
        return self._native_win32_inspect_tree(hwnd)

    def _native_com_uia_inspect_tree(self, hwnd: int) -> Optional[UIATreeSnapshot]:
        """Bóc tách cây phần tử trợ năng native qua Windows UI Automation COM Interface (IUIAutomation)."""
        com_initialized = False
        try:
            import comtypes
            comtypes.CoInitialize()
            com_initialized = True
            import comtypes.client
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation, TreeScope_Descendants
            import win32gui
            import win32process

            if not win32gui.IsWindow(hwnd):
                return None

            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = self._resolve_process_name(pid)

            uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
            root_elem = uia.ElementFromHandle(hwnd)
            if not root_elem:
                return None

            cond = uia.CreateTrueCondition()
            descendants = None
            try:
                cache_request = build_tree_cache_request(uia)
                descendants = find_all_cached(uia, root_elem, TreeScope_Descendants, cond, cache_request)
            except Exception:
                descendants = None
            if descendants is None:
                descendants = root_elem.FindAll(TreeScope_Descendants, cond)
            if descendants is None:
                return None

            elements: List[UIAElementNode] = []
            ref_idx = 1
            for i in range(descendants.Length):
                try:
                    el = descendants.GetElement(i)
                    info = read_uia_element(el)
                    name = info["name"]
                    class_name = info["class_name"] or "Unknown"
                    auto_id = info["automation_id"] or f"ctrl_uia_{i}"
                    ct_id = info["control_type_id"]
                    ctrl_type = UIA_CONTROL_TYPE_MAP.get(ct_id, self._infer_control_type(class_name, name))

                    rect = info["rect"]
                    if rect is None:
                        continue
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2

                    is_enabled = bool(info["is_enabled"])
                    is_offscreen = bool(info["is_offscreen"])
                    is_visible = not is_offscreen

                    native_pat, pat_details = self._extract_com_pattern_details(el)
                    patterns = native_pat if native_pat else self._infer_supported_patterns(ctrl_type)

                    elem = UIAElementNode(
                        name=name,
                        control_type=ctrl_type,
                        automation_id=auto_id,
                        class_name=class_name,
                        rect=rect,
                        center=(center_x, center_y),
                        hwnd=hwnd,
                        is_enabled=is_enabled,
                        is_visible=is_visible,
                        supported_patterns=patterns,
                        ref=f"e{ref_idx}",
                        value=pat_details.get("value"),
                        is_read_only=pat_details.get("is_read_only"),
                        toggle_state=pat_details.get("toggle_state"),
                        is_selected=pat_details.get("is_selected"),
                        expand_state=pat_details.get("expand_state"),
                    )
                    elements.append(elem)
                    ref_idx += 1
                except Exception:
                    continue

            snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc_name, elements=elements)
            ref_map = {e.ref: e for e in elements if e.ref}

            return UIATreeSnapshot(
                hwnd=hwnd,
                window_title=title,
                process_name=proc_name,
                pid=pid,
                element_count=len(elements),
                snapshot_hash=snap_hash,
                engine="NATIVE_COM_UIA3",
                elements=elements,
                ref_map=ref_map,
            )
        except Exception:
            return None
        finally:
            # Release every COM proxy before tearing down the apartment: a
            # cached FindAll collection outliving CoUninitialize raises
            # RPC_E_DISCONNECTED (0x80010108) as a fatal Windows exception, not
            # a catchable Python error, when the target process exits under it.
            uia = root_elem = cond = descendants = cache_request = el = None
            if com_initialized:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass

    def _native_win32_inspect_tree(self, hwnd: int) -> UIATreeSnapshot:
        """Bóc tách cây phần tử dự phòng sử dụng Win32 EnumChildWindows."""
        import win32gui
        import win32process

        if not win32gui.IsWindow(hwnd):
            return UIATreeSnapshot(
                hwnd=hwnd,
                window_title="",
                process_name="",
                pid=0,
                element_count=0,
                snapshot_hash="empty_invalid_hwnd",
                engine=self.engine_name,
                elements=[],
                ref_map={},
            )

        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = self._resolve_process_name(pid)

        elements: List[UIAElementNode] = []
        children: List[int] = []

        def enum_cb(child_hwnd, _):
            children.append(child_hwnd)
            return True

        try:
            win32gui.EnumChildWindows(hwnd, enum_cb, None)
        except Exception:
            pass

        ref_idx = 1
        for child in children:
            try:
                c_title = win32gui.GetWindowText(child) or ""
                c_class = win32gui.GetClassName(child) or "Unknown"
                c_rect = win32gui.GetWindowRect(child)
                c_visible = bool(win32gui.IsWindowVisible(child))
                c_enabled = bool(win32gui.IsWindowEnabled(child))

                ctrl_type = self._infer_control_type(c_class, c_title)
                patterns = self._infer_supported_patterns(ctrl_type)

                center_x = (c_rect[0] + c_rect[2]) // 2
                center_y = (c_rect[1] + c_rect[3]) // 2

                elem = UIAElementNode(
                    name=c_title or f"{ctrl_type}_{child}",
                    control_type=ctrl_type,
                    automation_id=f"ctrl_{child}",
                    class_name=c_class,
                    rect=c_rect,
                    center=(center_x, center_y),
                    hwnd=child,
                    is_enabled=c_enabled,
                    is_visible=c_visible,
                    supported_patterns=patterns,
                    ref=f"e{ref_idx}",
                )
                elements.append(elem)
                ref_idx += 1
            except Exception:
                continue

        # Tính toán snapshot_hash chuẩn hóa từ toàn bộ cây phần tử
        snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc_name, elements=elements)
        ref_map = {e.ref: e for e in elements if e.ref}

        return UIATreeSnapshot(
            hwnd=hwnd,
            window_title=title,
            process_name=proc_name,
                pid=pid,
            element_count=len(elements),
            snapshot_hash=snap_hash,
            engine=self.engine_name,
            elements=elements,
            ref_map=ref_map,
        )

    def _mock_inspect_tree(self, hwnd: int, process_name: str = "notepad.exe", pid: int = 5678) -> UIATreeSnapshot:
        """Tạo Mock Snapshot chuẩn xác phục vụ kiểm thử đơn vị độc lập."""
        mock_nodes = [
            UIAElementNode(
                name="File",
                control_type="MenuItem",
                automation_id="Menu_File",
                class_name="MenuItem",
                rect=(110, 130, 150, 155),
                center=(130, 142),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e1",
            ),
            UIAElementNode(
                name="Edit",
                control_type="MenuItem",
                automation_id="Menu_Edit",
                class_name="MenuItem",
                rect=(155, 130, 195, 155),
                center=(175, 142),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e2",
            ),
            UIAElementNode(
                name="Text Editor",
                control_type="Edit",
                automation_id="EditorArea",
                class_name="Edit",
                rect=(105, 160, 895, 690),
                center=(500, 425),
                hwnd=hwnd,
                supported_patterns=["ValuePattern", "TextPattern"],
                ref="e3",
                value="",
                is_read_only=False,
            ),
            UIAElementNode(
                name="Close",
                control_type="Button",
                automation_id="Sys_Close",
                class_name="Button",
                rect=(860, 105, 895, 130),
                center=(877, 117),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e4",
            ),
        ]

        snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=process_name, elements=mock_nodes)
        ref_map = {e.ref: e for e in mock_nodes}

        return UIATreeSnapshot(
            hwnd=hwnd,
            window_title="Untitled - Notepad",
            process_name=process_name,
            pid=pid,
            element_count=len(mock_nodes),
            snapshot_hash=snap_hash,
            engine=self.engine_name,
            elements=mock_nodes,
            ref_map=ref_map,
        )

    def get_element_by_ref(self, snapshot: UIATreeSnapshot, ref: str) -> Optional[UIAElementNode]:
        """Tra cứu phần tử siêu tốc O(1) bằng Semantic Ref ID (ví dụ 'e1', '@ref:e1')."""
        clean_ref = ref.replace("@ref:", "").replace("@", "").strip()
        return snapshot.ref_map.get(clean_ref)

    def to_semantic_prompt(self, snapshot: UIATreeSnapshot, max_elements: int = 50, interactive_only: bool = True) -> str:
        """
        Sinh biểu diễn Markdown ngữ nghĩa tinh gọn cho LLM Planner (chuẩn hóa theo agent-desktop).
        Liệt kê các phần tử hành động kèm @ref, tên, vai trò và trạng thái.
        """
        ACTIONABLE_TYPES = {
            "Button", "Edit", "MenuItem", "CheckBox", "RadioButton",
            "ComboBox", "TabItem", "Hyperlink", "Document", "SplitButton", "ListItem"
        }
        ACTIONABLE_PATTERNS = {
            "InvokePattern", "ValuePattern", "TogglePattern",
            "SelectionItemPattern", "ExpandCollapsePattern"
        }

        lines = [
            f"### Active Window: {snapshot.window_title} (HWND: {snapshot.hwnd}, PID: {snapshot.pid}, Engine: {snapshot.engine})",
            f"Elements detected: {snapshot.element_count}",
            ""
        ]

        rendered_count = 0
        for el in snapshot.elements:
            if interactive_only:
                # Lọc bỏ rác giao diện không có tên và không có khả năng tương tác
                has_name = bool(el.name and el.name.strip())
                has_val = bool(el.value and el.value.strip())
                is_action_type = el.control_type in ACTIONABLE_TYPES
                has_action_pat = any(p in ACTIONABLE_PATTERNS for p in el.supported_patterns)
                if not (has_name or has_val or is_action_type or has_action_pat):
                    continue

            extra_info = []
            if el.value is not None and el.value != "":
                val_preview = el.value if len(el.value) <= 40 else el.value[:37] + "..."
                extra_info.append(f'value: "{val_preview}"')
            if el.is_read_only:
                extra_info.append("read_only")
            if el.toggle_state:
                extra_info.append(f"toggle: {el.toggle_state}")
            if el.is_selected:
                extra_info.append("selected")
            if el.expand_state:
                extra_info.append(f"expand: {el.expand_state}")

            bounds_str = f"bounds: ({el.rect[0]}, {el.rect[1]}, {el.rect[2]}, {el.rect[3]})"
            extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
            name_str = f' "{el.name}"' if el.name else ""
            lines.append(f"- [@ref:{el.ref}] {el.control_type}{name_str}{extra_str} [{bounds_str}]")
            rendered_count += 1
            if rendered_count >= max_elements:
                break

        if snapshot.element_count > rendered_count:
            lines.append(f"... and {snapshot.element_count - rendered_count} more elements.")

        return "\n".join(lines)

    def to_dict(self, snapshot: UIATreeSnapshot) -> Dict[str, Any]:
        """Chuyển đổi Snapshot thành Dict cấu trúc phục vụ trả về cho MCP Tools hoặc Tool Calls."""
        return {
            "window_title": snapshot.window_title,
            "hwnd": snapshot.hwnd,
            "pid": snapshot.pid,
            "engine": snapshot.engine,
            "element_count": snapshot.element_count,
            "snapshot_hash": snapshot.snapshot_hash,
            "elements": [
                {
                    "ref": e.ref,
                    "name": e.name,
                    "control_type": e.control_type,
                    "automation_id": e.automation_id,
                    "class_name": e.class_name,
                    "rect": list(e.rect),
                    "center": list(e.center),
                    "is_enabled": e.is_enabled,
                    "is_visible": e.is_visible,
                    "value": e.value,
                    "is_read_only": e.is_read_only,
                    "toggle_state": e.toggle_state,
                    "is_selected": e.is_selected,
                    "expand_state": e.expand_state,
                    "supported_patterns": e.supported_patterns,
                    "element_hash": e.element_hash
                }
                for e in snapshot.elements
            ]
        }

    def fast_find_element(
        self,
        name_query: str,
        control_type: Optional[str] = None,
        hwnd: Optional[int] = None,
        match_mode: str = "contains"
    ) -> Dict[str, Any]:
        """
        Fast-Path Semantic Query (<3ms):
        Tìm kiếm phần tử theo Tên / Control Type trực tiếp qua COM Native UIA3.
        Bỏ qua toàn bộ bước chụp ảnh màn hình và suy luận VLM.
        """
        import win32gui
        t0 = time.perf_counter()

        target_hwnd = hwnd if (hwnd and win32gui.IsWindow(hwnd)) else win32gui.GetForegroundWindow()
        if not target_hwnd or not win32gui.IsWindow(target_hwnd):
            target_hwnd = win32gui.GetDesktopWindow()

        snap = self.inspect_tree(target_hwnd)
        query_norm = name_query.strip().lower()

        for el in snap.elements:
            el_name = (el.name or "").strip().lower()
            if not el_name:
                continue

            name_matched = False
            if match_mode == "exact":
                name_matched = (el_name == query_norm)
            else:
                name_matched = (query_norm in el_name)

            type_matched = True
            if control_type:
                type_matched = (el.control_type.lower() == control_type.strip().lower())

            if name_matched and type_matched:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                return {
                    "found": True,
                    "name": el.name,
                    "ref": el.ref,
                    "control_type": el.control_type,
                    "automation_id": el.automation_id,
                    "rect": list(el.rect),
                    "center": list(el.center),
                    "hwnd": el.hwnd or target_hwnd,
                    "value": el.value,
                    "supported_patterns": el.supported_patterns,
                    "elapsed_ms": elapsed_ms,
                    "engine": snap.engine
                }

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "found": False,
            "query": name_query,
            "target_hwnd": target_hwnd,
            "scanned_elements": len(snap.elements),
            "elapsed_ms": elapsed_ms
        }
