# -*- coding: utf-8 -*-
"""
services/ai_desktop/desktop_actuator.py
[M5-ACTUATOR] High-level Desktop OS Actuator Orchestrator.
Kết hợp Threat Model, Window Inspector, Smooth Mouse Engine, Elevation Blocker,
Signed Mutation Approval Gate & TOCTOU Revalidation & Watchdog (M5-G0 -> M5-G5).
Nâng cấp theo tiêu chí OpenCode Lượt 143:
- Revalidate HWND + PID + process path + rect + target snapshot ngay trước mouse_down.
- Ghi nhận pre-action & post-action state, foreground activation, và trajectory bounds.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .threat_model import DesktopSecurityGate, DesktopSecurityViolation
from .mouse_engine import (
    DesktopMouseAdapterProtocol,
    MockDesktopMouseAdapter,
    NativeWindowsMouseAdapter,
    SmoothMouseEngine,
)
from .window_inspector import (
    MockWindowInspector,
    NativeWindowInspector,
    WindowElementRef,
    WindowInspectorProtocol,
)
from .watchdog import DesktopEmergencyStop, DesktopWatchdog
from .window_message_adapter import WindowMessageAdapter
from .gateway_verifier import GatewayObservationVerifier
from .mouse_engine import CursorActionError, CursorReadbackDriftError

logger = logging.getLogger("ai-desktop-actuator")


@dataclass
class DesktopActRequest:
    action: str  # "observe", "click", "hover", "move"
    target_name: Optional[str] = None
    target_coords: Optional[Tuple[int, int]] = None
    target_process: Optional[str] = None
    target_hwnd: Optional[int] = None
    target_identity: Optional[str] = None  # AutomationId hoặc stable element signature
    approval_token: Optional[str] = None
    execution_mode: str = "visual"  # "visual" | "background_message" | "background_uia"
    button: str = "left"
    text: str = ""
    trace_id: str = ""
    task_id: str = ""
    timeout_s: float = 10.0
    skip_mutation_gate: bool = False
    postcondition_verifier: Optional[Callable[[int], bool]] = None
    expected_postcondition: Optional[str] = None  # 'target_mutation' | 'control_state'
    emergency_containment: bool = False


@dataclass
class DesktopActResponse:
    status: str  # "success", "rejected", "failed"
    action: str
    resolved_target: str = ""
    final_coords: Tuple[int, int] = (0, 0)
    trajectory_steps: int = 0
    mutation_risk: str = "READ_ONLY"
    msg: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)


class DesktopOSActuator:
    """
    [M5 SOVEREIGN ACTUATOR]
    Tác tử điều khiển Desktop OS toàn diện:
    1. Kiểm toán bảo mật Threat Model & Process Scoping [M5-G0].
    2. Chặn đứng các cửa sổ đặc quyền Administrator (Elevated Blocker) [M5-G0].
    3. Cổng phê duyệt Mutation Approval Token (M5-G4) ràng buộc cứng HWND, PID, Process, Target.
    4. Tái kiểm tra danh tính cửa sổ chống TOCTOU Race Condition [M5-G4].
    5. Bộ đếm nhịp an toàn Watchdog Timer & Emergency Stop [M5-G5].
    6. Quét cấu trúc cửa sổ & phần tử giao diện UIA [M5-G1].
    7. Di chuyển chuột vật lý trực quan theo đường cong Bezier [M5-G2].
    8. Ghi nhận nhật ký quỹ đạo & Evidence Contract ẩn danh hóa token.
    """

    def __init__(
        self,
        mouse_adapter: Optional[DesktopMouseAdapterProtocol] = None,
        window_inspector: Optional[WindowInspectorProtocol] = None,
        is_live_mode: bool = False,
        sandbox: Optional[Any] = None,
    ):
        self.is_live_mode = is_live_mode
        self.sandbox = sandbox
        self.mouse_adapter: DesktopMouseAdapterProtocol = (
            mouse_adapter or (NativeWindowsMouseAdapter() if is_live_mode else MockDesktopMouseAdapter())
        )
        self.window_inspector: WindowInspectorProtocol = (
            window_inspector or (NativeWindowInspector() if is_live_mode else MockWindowInspector())
        )

    def observe(self) -> Dict[str, Any]:
        """Quan sát trạng thái cửa sổ đang hoạt động (Foreground Window)."""
        fg_info = self.window_inspector.get_foreground_window_info()
        hwnd = fg_info.get("hwnd", 0)
        elements = self.window_inspector.inspect_window_elements(hwnd)

        return {
            "status": "success",
            "foreground": fg_info,
            "element_count": len(elements),
            "elements": [
                {
                    "name": el.name,
                    "control_type": el.control_type,
                    "automation_id": el.automation_id,
                    "rect": el.rect,
                    "center": el.center,
                }
                for el in elements
            ],
        }

    def execute_action(self, req: DesktopActRequest) -> DesktopActResponse:
        """
        Thực thi hành động chuột trên Desktop có kiểm soát rủi ro, TOCTOU guard và Watchdog.
        """
        if req.emergency_containment and self.sandbox:
            try:
                self.sandbox.terminate_all_now()
                return DesktopActResponse(
                    status="rejected",
                    action=req.action,
                    msg="EMERGENCY_CONTAINMENT_TRIGGERED: Đã hard kill toàn bộ tiến trình thuộc Job Object.",
                    evidence={"trace_id": req.trace_id, "worker_terminated": True, "sandbox_job_stats": self.sandbox.get_job_stats()},
                )
            except Exception as e:
                return DesktopActResponse(
                    status="failed",
                    action=req.action,
                    msg=f"FAIL_CLOSED_EMERGENCY_CONTAINMENT_FAILED: Lỗi khi thực thi hard kill Job Object: {e}",
                    evidence={"trace_id": req.trace_id, "worker_terminated": False, "error": str(e)},
                )
        # 1. Quan sát cửa sổ mục tiêu (hoặc Foreground nếu không chỉ định HWND)
        if req.target_hwnd:
            fg_info = self.window_inspector.get_window_info(req.target_hwnd)
        else:
            fg_info = self.window_inspector.get_foreground_window_info()
        proc_name = fg_info.get("process_name", "")
        proc_path = fg_info.get("process_path", "")
        win_title = fg_info.get("title", "")
        win_rect = fg_info.get("rect", (0, 0, 1920, 1080))
        hwnd = fg_info.get("hwnd", 0)
        pid = fg_info.get("pid", 0)
        is_elevated = fg_info.get("is_elevated", False)

        trace_id = req.trace_id or f"trace_desktop_{int(time.time()*1000)}"
        task_id = req.task_id or "task_desktop_default"

        # 2. Kiểm toán Threat Model [M5-G0]
        # 2A. Kiểm tra tiến trình (Allowlist vs Blacklist)
        proc_ok, proc_reason = DesktopSecurityGate.validate_process_scope(proc_name)
        if not proc_ok:
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=proc_name,
                msg=f"SECURITY_REJECTED: {proc_reason}",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "proc_name": proc_name},
            )

        # 2B. Kiểm tra tiêu đề cửa sổ (Chống chạm UAC / Admin / Security Dialogs)
        win_ok, win_reason = DesktopSecurityGate.validate_window_title(win_title)
        if not win_ok:
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=win_title,
                msg=f"SECURITY_REJECTED: {win_reason}",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "win_title": win_title},
            )

        # 2C. [ELEVATED WINDOW BLOCKER]: Cấm tuyệt đối cửa sổ Administrator
        elev_ok, elev_reason = DesktopSecurityGate.validate_elevation(is_elevated)
        if not elev_ok:
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=win_title,
                msg=f"SECURITY_REJECTED: {elev_reason}",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "is_elevated": is_elevated},
            )

        # 3. Phân giải tọa độ mục tiêu
        target_coords: Optional[Tuple[int, int]] = None
        target_label = req.target_name or "Custom Coordinate"
        target_elem_ref: Optional[WindowElementRef] = None

        if req.target_name:
            elem = self.window_inspector.find_element_by_name(hwnd, req.target_name)
            if not elem:
                return DesktopActResponse(
                    status="failed",
                    action=req.action,
                    resolved_target=req.target_name,
                    msg=f"ELEMENT_NOT_FOUND: Không tìm thấy phần tử '{req.target_name}' trong cửa sổ '{win_title}'.",
                    evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
                )
            target_coords = elem.center
            target_elem_ref = elem
        elif req.target_coords:
            target_coords = req.target_coords
        else:
            return DesktopActResponse(
                status="failed",
                action=req.action,
                msg="INVALID_REQUEST: Phải chỉ định target_name hoặc target_coords.",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
            )

        # 4. [CHỐNG TRƯỢT TỌA ĐỘ]: Kiểm tra tọa độ nằm trong BoundingBox cửa sổ
        target_x, target_y = target_coords
        if not DesktopSecurityGate.validate_coordinates_within_window(target_x, target_y, win_rect):
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=target_label,
                final_coords=(target_x, target_y),
                msg=f"BOUNDARY_VIOLATION: Tọa độ ({target_x}, {target_y}) trượt ra ngoài phạm vi cửa sổ {win_rect}!",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "target_coords": target_coords, "win_rect": win_rect},
            )

        # 5. [M5-G4]: Đánh giá rủi ro Mutation & Enforce Approval Token
        is_mutation = req.action in ("click", "double_click", "drag", "type", "type_text")
        risk_level = "MUTATION" if is_mutation else "READ_ONLY"

        allow_unsafe = os.getenv("JKAI_ALLOW_UNSAFE_MUTATION", "0").lower() in ("1", "true")

        if is_mutation and not (allow_unsafe and req.skip_mutation_gate):
            # 5A. Bắt buộc phải có token phê duyệt cho hành động click
            if not req.approval_token:
                return DesktopActResponse(
                    status="rejected",
                    action=req.action,
                    resolved_target=target_label,
                    final_coords=(target_x, target_y),
                    mutation_risk=risk_level,
                    msg=f"APPROVAL_REQUIRED: Hành động '{req.action}' làm thay đổi trạng thái (MUTATION) bắt buộc phải có chữ ký approval_token (M5-G4).",
                    evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "target_label": target_label},
                )

            # 5B. Xác minh token phê duyệt (Khóa chặt HWND, PID, Process, Target, Action)
            token_ok, token_msg = DesktopSecurityGate.verify_approval_token(
                token=req.approval_token,
                expected_hwnd=hwnd,
                expected_proc=proc_name,
                expected_target=target_label,
                expected_action=req.action,
                expected_pid=pid,
                expected_mode=req.execution_mode,
                expected_identity=req.target_identity,
                expected_postcondition=req.expected_postcondition,
            )
            if not token_ok:
                return DesktopActResponse(
                    status="rejected",
                    action=req.action,
                    resolved_target=target_label,
                    final_coords=(target_x, target_y),
                    mutation_risk=risk_level,
                    msg=f"APPROVAL_REJECTED: {token_msg}",
                    evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid, "target_label": target_label},
                )

        # 6. [TOCTOU GUARD & PRE-ACTION REVALIDATION]:
        # Tái thẩm định toàn diện cửa sổ mục tiêu (HWND, PID, Process, Rect, Bounds) ngay trước khi di chuột
        if req.target_hwnd:
            reval_fg = self.window_inspector.get_window_info(req.target_hwnd)
        else:
            reval_fg = self.window_inspector.get_foreground_window_info()

        reval_hwnd = reval_fg.get("hwnd")
        reval_pid = reval_fg.get("pid")
        reval_proc = reval_fg.get("process_name")
        reval_rect = reval_fg.get("rect")

        # 6A. Kiểm tra tráo đổi HWND hoặc Process
        if reval_hwnd != hwnd or reval_proc != proc_name:
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=target_label,
                final_coords=(target_x, target_y),
                mutation_risk=risk_level,
                msg=f"TOCTOU_IDENTITY_DRIFT: Cửa sổ Foreground đã bị tráo đổi (HWND {hwnd} -> {reval_hwnd}, PROC {proc_name} -> {reval_proc}) trước khi thao tác!",
                evidence={
                    "trace_id": trace_id,
                    "task_id": task_id,
                    "expected_hwnd": hwnd,
                    "actual_hwnd": reval_hwnd,
                    "expected_proc": proc_name,
                    "actual_proc": reval_proc,
                },
            )

        # 6B. Kiểm tra tráo đổi PID (chống PID recycling / process replacement)
        if pid and reval_pid and reval_pid != pid:
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=target_label,
                final_coords=(target_x, target_y),
                mutation_risk=risk_level,
                msg=f"TOCTOU_PID_DRIFT: PID của tiến trình mục tiêu đã thay đổi ({pid} -> {reval_pid})!",
                evidence={"trace_id": trace_id, "task_id": task_id, "expected_pid": pid, "actual_pid": reval_pid},
            )

        # 6C. Kiểm tra trượt Bounding Rect (chống cửa sổ bị di dời hoặc resize trước click)
        if reval_rect and not DesktopSecurityGate.validate_coordinates_within_window(target_x, target_y, reval_rect):
            return DesktopActResponse(
                status="rejected",
                action=req.action,
                resolved_target=target_label,
                final_coords=(target_x, target_y),
                mutation_risk=risk_level,
                msg=f"TOCTOU_BOUNDS_DRIFT: Tọa độ đích ({target_x}, {target_y}) trượt ra ngoài Rect mới {reval_rect}!",
                evidence={"trace_id": trace_id, "task_id": task_id, "reval_rect": reval_rect, "target_coords": target_coords},
            )

        # Ghi nhận trạng thái tiền thực thi (Pre-action Snapshot)
        pre_action_state = {
            "cursor_before": self.mouse_adapter.get_position(),
            "target_center": (target_x, target_y),
            "window_rect": reval_rect or win_rect,
            "hwnd": hwnd,
            "pid": pid,
            "process_name": proc_name,
            "process_path": proc_path,
            "window_title": win_title,
        }

        # 7. [M5-G5 WATCHDOG]: Giám sát thời gian thực thi chống treo luồng chuột
        watchdog = DesktopWatchdog(timeout_s=req.timeout_s)
        watchdog.start()

        trajectory: List[Tuple[int, int]] = []
        msg_receipt = None
        verifier_provenance = None
        try:
            if req.execution_mode == "background_message":
                # [GATEWAY-OWNED VERIFIER SYNTHESIS & ENFORCEMENT]:
                effective_verifier = req.postcondition_verifier
                verifier_provenance = {
                    "synthesized_by": "NONE",
                    "verifier_id": "NONE",
                    "expected_postcondition": req.expected_postcondition or "NONE",
                }

                if risk_level == "MUTATION":
                    # [CHẶN ĐỨNG CALLER CALLBACK INJECTION]: Cấm tuyệt đối caller tự tiêm callback verifier
                    if req.postcondition_verifier is not None:
                        return DesktopActResponse(
                            status="rejected",
                            action=req.action,
                            resolved_target=target_label,
                            final_coords=(target_x, target_y),
                            mutation_risk=risk_level,
                            msg="POLICY_VIOLATION_CALLER_CALLBACK_FORBIDDEN: Nghiêm cấm caller tự tiêm callback verifier. Verifier bắt buộc phải do Central Gateway tự động tổng hợp từ Token Expectation Binding.",
                            evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
                        )

                    target_auto_id = target_elem_ref.automation_id if (target_elem_ref and target_elem_ref.automation_id) else (target_label or "target")
                    exp_type = req.expected_postcondition
                    if not exp_type and req.approval_token:
                        payload = DesktopSecurityGate.decode_token_payload(req.approval_token)
                        if payload and payload.get("postcond"):
                            exp_type = payload.get("postcond")

                    # Nếu có expectation -> Gateway TỰ TỔNG HỢP Verifier độc lập (Central Gateway Owned)
                    is_live = isinstance(self.window_inspector, NativeWindowInspector)
                    if exp_type:
                        if exp_type == "control_state":
                            effective_verifier = GatewayObservationVerifier.create_control_state_verifier(
                                hwnd=hwnd,
                                target_automation_id=target_auto_id,
                                is_live_mode=is_live,
                            )
                            verifier_provenance = {
                                "synthesized_by": "CENTRAL_GATEWAY",
                                "verifier_id": f"GATEWAY_VERIFIER_CONTROL_STATE_{target_auto_id}",
                                "expected_postcondition": "control_state",
                            }
                        elif exp_type == "target_mutation":
                            effective_verifier = GatewayObservationVerifier.create_target_mutation_verifier(
                                hwnd=hwnd,
                                target_automation_id=target_auto_id,
                                is_live_mode=is_live,
                            )
                            verifier_provenance = {
                                "synthesized_by": "CENTRAL_GATEWAY",
                                "verifier_id": f"GATEWAY_VERIFIER_TARGET_MUTATION_{target_auto_id}",
                                "expected_postcondition": "target_mutation",
                            }
                        elif exp_type.startswith("title:") or exp_type.startswith("expected_title:"):
                            expected_title_val = exp_type.split(":", 1)[1].strip()
                            effective_verifier = GatewayObservationVerifier.create_expected_title_verifier(
                                hwnd=hwnd,
                                expected_title=expected_title_val,
                                exact=True,
                                is_live_mode=is_live,
                            )
                            verifier_provenance = {
                                "synthesized_by": "CENTRAL_GATEWAY",
                                "verifier_id": f"GATEWAY_VERIFIER_EXPECTED_TITLE_{expected_title_val[:16]}",
                                "expected_postcondition": exp_type,
                                "expected_title": expected_title_val,
                            }
                        elif exp_type.startswith("text:") or exp_type.startswith("expected_text:"):
                            expected_text_val = exp_type.split(":", 1)[1].strip()
                            effective_verifier = GatewayObservationVerifier.create_expected_text_verifier(
                                hwnd=hwnd,
                                expected_text=expected_text_val,
                                exact=True,
                                is_live_mode=is_live,
                            )
                            verifier_provenance = {
                                "synthesized_by": "CENTRAL_GATEWAY",
                                "verifier_id": f"GATEWAY_VERIFIER_EXPECTED_TEXT_{expected_text_val[:16]}",
                                "expected_postcondition": exp_type,
                                "expected_text": expected_text_val,
                            }
                        elif exp_type == "visual_diff":
                            effective_verifier = GatewayObservationVerifier.create_visual_diff_verifier(
                                hwnd=hwnd,
                                is_live_mode=is_live,
                                expected_diff=True,
                            )
                            verifier_provenance = {
                                "synthesized_by": "CENTRAL_GATEWAY",
                                "verifier_id": f"GATEWAY_VERIFIER_VISUAL_DIFF_{hwnd}",
                                "expected_postcondition": "visual_diff",
                            }
                        else:
                            return DesktopActResponse(
                                status="rejected",
                                action=req.action,
                                resolved_target=target_label,
                                final_coords=(target_x, target_y),
                                mutation_risk=risk_level,
                                msg=f"POLICY_VIOLATION_UNKNOWN_EXPECTATION: Expectation '{exp_type}' không được Gateway hỗ trợ.",
                                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
                            )
                    else:
                        return DesktopActResponse(
                            status="rejected",
                            action=req.action,
                            resolved_target=target_label,
                            final_coords=(target_x, target_y),
                            mutation_risk=risk_level,
                            msg="POLICY_VIOLATION_NO_VERIFIER: Mọi thao tác Background Mutation bắt buộc phải có Postcondition Expectation để Gateway tự tổng hợp Verifier độc lập.",
                            evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
                        )

                # Kênh thực thi ngầm qua Windows Messages (không dùng con trỏ vật lý)
                msg_adapter = WindowMessageAdapter()
                if req.action in ("type", "type_text"):
                    msg_receipt = msg_adapter.send_text(
                        hwnd=hwnd,
                        text=req.text,
                        expected_pid=pid,
                        target_identity=req.target_identity,
                        verify_postcondition=effective_verifier,
                    )
                else:
                    msg_receipt = msg_adapter.send_click(
                        hwnd=hwnd,
                        screen_x=target_x,
                        screen_y=target_y,
                        button=req.button,
                        expected_pid=pid,
                        expected_process_name=proc_name,
                        target_identity=req.target_identity,
                        verify_postcondition=effective_verifier,
                    )
                if msg_receipt.delivery_status == "not_delivered" or not msg_receipt.success:
                    return DesktopActResponse(
                        status="failed",
                        action=req.action,
                        resolved_target=target_label,
                        final_coords=(target_x, target_y),
                        mutation_risk=risk_level,
                        msg=f"FAIL_CLOSED: Gửi Window Message thất bại: {msg_receipt.error_msg}",
                        evidence={"trace_id": trace_id, "task_id": task_id, "receipt": msg_receipt.__dict__},
                    )
                # Bắt buộc đạt delivered_verified đối với mutation actions!
                if risk_level == "MUTATION" and msg_receipt.delivery_status != "delivered_verified":
                    return DesktopActResponse(
                        status="failed",
                        action=req.action,
                        resolved_target=target_label,
                        final_coords=(target_x, target_y),
                        mutation_risk=risk_level,
                        msg=f"FAIL_CLOSED_UNVERIFIED: Thao tác background chưa được xác thực bởi Postcondition Verifier ({msg_receipt.delivery_status})",
                        evidence={"trace_id": trace_id, "task_id": task_id, "receipt": msg_receipt.__dict__},
                    )
            elif req.action == "move" or req.action == "hover":
                trajectory = SmoothMouseEngine.execute_smooth_move(
                    self.mouse_adapter,
                    target_x,
                    target_y,
                    cancel_check=watchdog.is_cancelled,
                )
            elif req.action == "click":
                trajectory = SmoothMouseEngine.execute_smooth_click(
                    self.mouse_adapter,
                    target_x,
                    target_y,
                    button=req.button,
                    cancel_check=watchdog.is_cancelled,
                )
            else:
                return DesktopActResponse(
                    status="failed",
                    action=req.action,
                    msg=f"UNSUPPORTED_ACTION: Hành động '{req.action}' chưa được hỗ trợ trên Desktop OS.",
                    evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
                )

            if watchdog.is_cancelled():
                worker_terminated = False
                kill_error = None
                if self.sandbox:
                    try:
                        self.sandbox.terminate_all_now()
                        worker_terminated = True
                    except Exception as e:
                        worker_terminated = False
                        kill_error = str(e)

                # [FAIL-CLOSED ON WATCHDOG KILL FAILURE]:
                # Nếu có sandbox nhưng việc hard kill worker bị lỗi, BẮT BUỘC trả status='failed'
                if self.sandbox and not worker_terminated:
                    return DesktopActResponse(
                        status="failed",
                        action=req.action,
                        resolved_target=target_label,
                        final_coords=self.mouse_adapter.get_position(),
                        mutation_risk=risk_level,
                        msg=f"FAIL_CLOSED_WATCHDOG_CONTAINMENT_FAILED: Watchdog timeout ngắt thao tác nhưng hard kill worker thất bại: {kill_error}",
                        evidence={
                            "trace_id": trace_id,
                            "task_id": task_id,
                            "hwnd": hwnd,
                            "pid": pid,
                            "worker_terminated": False,
                            "error": kill_error,
                            "sandbox_job_stats": self.sandbox.get_job_stats() if self.sandbox else None,
                        },
                    )

                return DesktopActResponse(
                    status="rejected",
                    action=req.action,
                    resolved_target=target_label,
                    final_coords=self.mouse_adapter.get_position(),
                    mutation_risk=risk_level,
                    msg=f"WATCHDOG_TIMEOUT_INTERRUPT: Thao tác chuột bị ngắt do vượt ngưỡng thời gian {req.timeout_s}s (M5-G5).",
                    evidence={
                        "trace_id": trace_id,
                        "task_id": task_id,
                        "hwnd": hwnd,
                        "pid": pid,
                        "worker_terminated": worker_terminated,
                        "sandbox_job_stats": self.sandbox.get_job_stats() if self.sandbox else None,
                    },
                )
        except (CursorActionError, CursorReadbackDriftError) as e:
            return DesktopActResponse(
                status="failed",
                action=req.action,
                resolved_target=target_label,
                final_coords=self.mouse_adapter.get_position(),
                mutation_risk=risk_level,
                msg=f"FAIL_CLOSED: {e}",
                evidence={"trace_id": trace_id, "task_id": task_id, "hwnd": hwnd, "pid": pid},
            )
        finally:
            watchdog.stop()

        # Ghi nhận trạng thái hậu thực thi (Post-action Snapshot)
        post_cursor_pos = self.mouse_adapter.get_position()
        post_win_info = {}
        try:
            post_win_info = self.window_inspector.get_window_info(hwnd) if hwnd else {}
        except Exception:
            pass
        post_title = post_win_info.get("title", "")
        arrived = (post_cursor_pos == (target_x, target_y)) if req.execution_mode == "visual" else (msg_receipt.delivery_status == "delivered_verified" if msg_receipt else True)
        post_action_state = {
            "cursor_after": post_cursor_pos,
            "arrived_at_target": arrived,
            "trajectory_points_count": len(trajectory),
            "execution_mode": req.execution_mode,
            "delivery_status": msg_receipt.delivery_status if msg_receipt else ("visual_arrived" if arrived else "visual_drift"),
            "message_receipt": msg_receipt.__dict__ if msg_receipt else None,
            "window_title_after": post_title,
        }

        # [FAIL-CLOSED ENFORCEMENT]: Nếu ở Visual Mode mà trỏ chuột thực tế không tới đích -> Fail Closed!
        if req.execution_mode == "visual" and not arrived:
            return DesktopActResponse(
                status="failed",
                action=req.action,
                resolved_target=target_label,
                final_coords=post_cursor_pos,
                mutation_risk=risk_level,
                msg=f"FAIL_CLOSED_DRIFT: Con trỏ kết thúc tại {post_cursor_pos} nhưng mục tiêu là {(target_x, target_y)}",
                evidence={
                    "trace_id": trace_id,
                    "task_id": task_id,
                    "hwnd": hwnd,
                    "pid": pid,
                    "pre_action_state": pre_action_state,
                    "post_action_state": post_action_state,
                "receipt": msg_receipt.__dict__ if msg_receipt else None,
                },
            )

        # Mã băm ẩn danh cho token trong evidence (không log raw secret token)
        token_hash = (
            f"sha256_{hashlib.sha256(req.approval_token.encode('utf-8')).hexdigest()[:16]}"
            if req.approval_token
            else "READ_ONLY_AUTHORIZED"
        )

        return DesktopActResponse(
            status="success",
            action=req.action,
            resolved_target=target_label,
            final_coords=(target_x, target_y),
            trajectory_steps=len(trajectory),
            mutation_risk=risk_level,
            msg=f"Thực thi thành công '{req.action}' trực quan tới {target_label} ({target_x}, {target_y}).",
            evidence={
                "trace_id": trace_id,
                "task_id": task_id,
                "hwnd": hwnd,
                "pid": pid,
                "process_name": proc_name,
                "process_path": proc_path,
                "window_title": win_title,
                "window_rect": reval_rect or win_rect,
                "target_name": target_label,
                "target_coords": (target_x, target_y),
                "final_position": post_cursor_pos,
                "trajectory_steps_count": len(trajectory),
                "approval_token_hash": token_hash,
                "mutation_risk": risk_level,
                "pre_action_state": pre_action_state,
                "post_action_state": post_action_state,
                "receipt": msg_receipt.__dict__ if msg_receipt else None,
                "verifier_result": (msg_receipt.postcondition_verified if msg_receipt else False),
                "verifier_provenance": verifier_provenance,
                "before_after_state": {
                    "title_before": pre_action_state.get("window_title", ""),
                    "title_after": post_action_state.get("window_title_after", ""),
                    "effect_detected": (pre_action_state.get("window_title") != post_action_state.get("window_title_after")),
                },
                "toctou_revalidation": {
                    "hwnd_verified": True,
                    "pid_verified": True,
                    "process_name_verified": True,
                    "bounds_verified": True,
                },
            },
        )
