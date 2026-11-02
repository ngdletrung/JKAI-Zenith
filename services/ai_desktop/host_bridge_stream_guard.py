# -*- coding: utf-8 -*-
"""
services/ai_desktop/host_bridge_stream_guard.py
[M5 Phase 3: Host Bridge WebSocket Read-Only Stream Guard & Security Policy]:
Tuân thủ tuyệt đối các yêu cầu bảo mật từ LƯỢT 333 của OpenCode Red Team:
  1. Pure Read-Only Boundary: Chỉ cho phép các message types: subscribe, unsubscribe, ping, frame, error, heartbeat.
     Chặn đứng và từ chối 100% mọi message có chứa: click, type, key, focus, scroll, command, action, mutation, dispatch, approve, lease_grant.
  2. Authentication & Origin: Bắt buộc session token, Origin allowlist, từ chối unknown sessions và target ngoài allowlist.
  3. Resource & Rate Limiting: Giới hạn max connections, rate limit, max payload size, backpressure, và dọn dẹp sạch sẽ khi disconnect (chống rò rỉ handle).
"""

import hmac
import os
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from core.security.runtime_secrets import get_secret

# Tập hợp các Message Type hợp lệ duy nhất được phép đi qua WebSocket Read-Only
ALLOWED_WS_MESSAGE_TYPES = {
    "subscribe",
    "unsubscribe",
    "ping",
    "frame",
    "error",
    "heartbeat"
}

# Danh sách từ khoá mutation cấm tuyệt đối (Fail-Closed)
PROHIBITED_MUTATION_KEYWORDS = {
    "click",
    "type",
    "key",
    "focus",
    "scroll",
    "command",
    "action",
    "mutation",
    "dispatch",
    "approve",
    "lease_grant"
}

# Tên field cấm tuyệt đối ở mọi độ sâu của message tree
PROHIBITED_MUTATION_FIELDS = {
    "action", "command", "dispatch", "mutation", "approve", "lease_grant",
    "click", "type_text", "key", "focus", "scroll"
}

MAX_WS_MESSAGE_DEPTH = 6

# Tên biến môi trường chứa token của Read-Only Stream. Không có giá trị mặc định:
# chưa cấu hình token nghĩa là mọi kết nối bị từ chối (Fail-Closed).
STREAM_TOKEN_ENV = "SATELLITE_WS_TOKEN"
MAX_WS_CONNECTIONS = 10
MAX_WS_PAYLOAD_SIZE = 1024 * 1024 * 2  # 2MB
MAX_MESSAGES_PER_SECOND = 10
ALLOWED_ORIGIN_HOSTS = {"localhost", "127.0.0.1", "::1"}


class WebSocketSecurityException(Exception):
    def __init__(self, code: str, reason: str):
        super().__init__(f"[{code}] {reason}")
        self.code = code
        self.reason = reason


def resolve_stream_token(explicit: Optional[str] = None) -> Optional[str]:
    """Token Read-Only Stream: env trước, rồi runtime_tokens.env do host_bridge tự sinh."""
    if explicit is not None:
        candidate = explicit
    else:
        candidate = get_secret(STREAM_TOKEN_ENV)
    if not isinstance(candidate, str):
        return None
    candidate = candidate.strip()
    return candidate or None


def validate_ws_token(token: Optional[str], configured_token: Optional[str]) -> bool:
    """
    Xác thực Token kết nối WebSocket bằng so sánh hằng thời gian (chống timing attack).
    Không có token cấu hình phía server => từ chối toàn bộ (Fail-Closed).
    """
    if not configured_token or not isinstance(configured_token, str):
        return False
    if not token or not isinstance(token, str):
        return False
    candidate = token.strip()
    if not candidate or len(candidate) > 256:
        return False
    return hmac.compare_digest(candidate, configured_token.strip())


def validate_ws_origin(origin: Optional[str]) -> bool:
    """
    Xác thực HTTP Origin Header chống WebSocket Cross-Site Hijacking (CSWSH).
    Origin là BẮT BUỘC: thiếu Origin luôn bị từ chối, không có ngoại lệ test/ngoại lệ native.
    """
    if not origin or not isinstance(origin, str) or not origin.strip():
        return False

    try:
        parsed = urlparse(origin.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        return hostname.lower() in ALLOWED_ORIGIN_HOSTS
    except Exception:
        return False


def validate_target_process_allowlist(process_name: str) -> bool:
    """
    Xác thực target process có nằm trong policy SSoT
    (config/security/desktop_app_allowlist.json) hay không.
    Desktop root là target mặc định hợp lệ cho stream quan sát.
    """
    p_lower = str(process_name or "").strip().lower()
    if p_lower in ("", "desktop"):
        return True
    try:
        from services.ai_desktop.app_policy import get_policy
        return p_lower in get_policy().allowed_processes
    except Exception:
        return False


def _assert_read_only_tree(node: Any, depth: int = 0) -> None:
    """Duyệt toàn bộ message tree, từ chối mọi field mutation hoặc type lồng không hợp lệ."""
    if depth > MAX_WS_MESSAGE_DEPTH:
        raise WebSocketSecurityException("WS_INVALID_PAYLOAD", "Message nesting depth exceeds limit")

    if isinstance(node, dict):
        for raw_key, value in node.items():
            key = str(raw_key).strip().casefold()
            if key in PROHIBITED_MUTATION_FIELDS:
                raise WebSocketSecurityException(
                    "WS_MUTATION_MESSAGE_REJECTED",
                    f"Mutation field '{key}' is strictly prohibited on read-only WebSocket stream",
                )
            if key == "type" and isinstance(value, str) and value not in ALLOWED_WS_MESSAGE_TYPES:
                raise WebSocketSecurityException(
                    "WS_MUTATION_MESSAGE_REJECTED",
                    f"Nested message type '{value}' is not allowed on read-only WebSocket stream",
                )
            _assert_read_only_tree(value, depth + 1)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _assert_read_only_tree(item, depth + 1)


class HostBridgeStreamGuard:
    """
    Bộ bảo vệ và quản trị phiên kết nối WebSocket Stream thuần Read-Only.
    """

    def __init__(
        self,
        max_connections: int = MAX_WS_CONNECTIONS,
        max_payload_size: int = MAX_WS_PAYLOAD_SIZE,
        max_rate_per_sec: int = MAX_MESSAGES_PER_SECOND,
        stream_token: Optional[str] = None,
    ):
        self.max_connections = max_connections
        self.max_payload_size = max_payload_size
        self.max_rate_per_sec = max_rate_per_sec
        self.stream_token = resolve_stream_token(stream_token)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.client_message_timestamps: Dict[str, List[float]] = {}

    def register_connection(
        self,
        connection_id: str,
        token: Optional[str],
        origin: Optional[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Đăng ký kết nối client mới với kiểm tra xác thực, origin và giới hạn kết nối."""
        if not self.stream_token:
            raise WebSocketSecurityException(
                "WS_TOKEN_NOT_CONFIGURED",
                f"Server has no {STREAM_TOKEN_ENV} configured; stream access is fail-closed",
            )

        if len(self.active_sessions) >= self.max_connections:
            raise WebSocketSecurityException("MAX_CONNECTIONS_EXCEEDED", "Maximum WebSocket client connections reached")

        if not validate_ws_origin(origin):
            raise WebSocketSecurityException("WS_ORIGIN_REJECTED", f"Origin '{origin}' is not allowed")

        if not validate_ws_token(token, self.stream_token):
            raise WebSocketSecurityException("WS_AUTH_REQUIRED", "Invalid or missing WebSocket authentication token")

        if not session_id or len(session_id) < 4:
            raise WebSocketSecurityException("WS_UNKNOWN_SESSION_REJECTED", "Missing or invalid session_id")

        session_info = {
            "connection_id": connection_id,
            "session_id": session_id,
            "connected_at": time.time(),
            "target_hwnd": None,
            "target_process": None,
            "messages_sent": 0,
            "is_closed": False
        }
        self.active_sessions[connection_id] = session_info
        self.client_message_timestamps[connection_id] = []
        return session_info

    def unregister_connection(self, connection_id: str) -> bool:
        """Dọn dẹp tài nguyên triệt để khi client ngắt kết nối (Clean disconnect, chống leak)."""
        if connection_id in self.active_sessions:
            self.active_sessions[connection_id]["is_closed"] = True
            del self.active_sessions[connection_id]
        if connection_id in self.client_message_timestamps:
            del self.client_message_timestamps[connection_id]
        return True

    def filter_incoming_message(
        self,
        connection_id: str,
        raw_message: str
    ) -> Dict[str, Any]:
        """
        Lọc và kiểm duyệt thông điệp nhận từ Web Client:
        Bảo đảm 100% Read-Only Invariant, chặn đứng mọi mutation commands.
        """
        if connection_id not in self.active_sessions:
            raise WebSocketSecurityException("WS_UNKNOWN_SESSION_REJECTED", "Connection not registered")

        # 1. Kiểm tra kích thước payload
        if len(raw_message.encode("utf-8")) > self.max_payload_size:
            raise WebSocketSecurityException("WS_PAYLOAD_TOO_LARGE_REJECTED", f"Payload exceeds {self.max_payload_size} bytes limit")

        # 2. Kiểm tra Rate Limiting (Messages per second)
        now = time.time()
        ts_list = self.client_message_timestamps.get(connection_id, [])
        ts_list = [t for t in ts_list if now - t < 1.0]
        if len(ts_list) >= self.max_rate_per_sec:
            raise WebSocketSecurityException("WS_RATE_LIMIT_ENFORCED", "Message rate limit exceeded (max 10 msgs/sec)")
        ts_list.append(now)
        self.client_message_timestamps[connection_id] = ts_list

        # 3. Phân tích JSON và rà soát từ khoá Mutation cấm
        import json
        try:
            msg_obj = json.loads(raw_message)
        except Exception:
            raise WebSocketSecurityException("WS_INVALID_JSON", "Message is not valid JSON")

        if not isinstance(msg_obj, dict):
            raise WebSocketSecurityException("WS_INVALID_PAYLOAD", "Message must be a JSON object")

        # Kiểm tra message type có thuộc danh sách hợp lệ duy nhất của Read-Only Stream hay không
        msg_type = msg_obj.get("type", "")
        if msg_type not in ALLOWED_WS_MESSAGE_TYPES:
            raise WebSocketSecurityException(
                "WS_MUTATION_MESSAGE_REJECTED",
                f"Message type '{msg_type}' is not allowed. Only read-only stream types are permitted: {ALLOWED_WS_MESSAGE_TYPES}"
            )

        # Rà soát đệ quy toàn bộ cây message: cấm field mutation ở mọi độ sâu
        # (chặn payload lồng nhau như {"type":"subscribe","data":{"action":"click"}}).
        _assert_read_only_tree(msg_obj)

        # 4. Xử lý logic subscribe an toàn
        if msg_type == "subscribe":
            target_proc = str(msg_obj.get("process_name") or "")
            if target_proc and not validate_target_process_allowlist(target_proc):
                raise WebSocketSecurityException(
                    "WS_UNAUTHORIZED_TARGET_REJECTED",
                    f"Target process '{target_proc}' is not in the desktop policy allowlist",
                )
            target_hwnd = msg_obj.get("hwnd")
            if target_hwnd is not None:
                if type(target_hwnd) is not int or target_hwnd <= 0:
                    raise WebSocketSecurityException("WS_INVALID_PAYLOAD", "hwnd must be a positive integer")
                self.active_sessions[connection_id]["target_hwnd"] = target_hwnd
                self.active_sessions[connection_id]["target_process"] = target_proc

        return {
            "status": "ALLOWED",
            "type": msg_type,
            "data": msg_obj
        }
