# -*- coding: utf-8 -*-
"""
[TOOL SIGNAL PROTOCOL]
File: core/kernel/tool_signal.py

Thay thế cơ chế "hallucination-invite" (kích hoạt 100% tri thức) bằng tín hiệu
có cấu trúc rõ ràng giúp Model nhỏ biết chính xác phải làm gì tiếp theo.

Nguyên tắc:
  - Model KHÔNG được bịa đặt dữ liệu khi Tool không trả về gì.
  - Thay vào đó, Model PHẢI hành động theo chỉ thị cụ thể của ToolSignal.
  - Mọi lỗi Tool đều có cấu trúc: [SIGNAL_TYPE] + mô tả + next_action.
"""

from enum import Enum
from typing import Optional


class ToolSignalType(str, Enum):
    EMPTY_RESULT     = "EMPTY_RESULT"      # Tool chạy thành công nhưng không tìm thấy dữ liệu
    EXECUTION_ERROR  = "EXECUTION_ERROR"   # Tool bị lỗi kỹ thuật (exception, timeout, crash)
    PERMISSION_DENIED = "PERMISSION_DENIED" # ExecutionIntegrityLayer từ chối quyền
    PARTIAL_RESULT   = "PARTIAL_RESULT"    # Có dữ liệu nhưng không đầy đủ (bị cắt, paginate)
    NETWORK_TIMEOUT  = "NETWORK_TIMEOUT"   # Timeout khi gọi API ngoài hoặc tìm kiếm web


# Bản đồ chỉ thị hành động tiếp theo cho từng loại tín hiệu
_NEXT_ACTION_MAP = {
    ToolSignalType.EMPTY_RESULT: (
        "Thử công cụ khác nếu có (ví dụ SEARCH_WEB_GLOBAL) HOẶC trả lời thành thật "
        "với Master rằng không tìm thấy thông tin này trong hệ thống. "
        "TUYỆT ĐỐI KHÔNG được bịa đặt hay suy đoán dữ liệu không có trong kết quả."
    ),
    ToolSignalType.EXECUTION_ERROR: (
        "Báo lỗi cụ thể cho Master và đề xuất phương án thay thế. "
        "KHÔNG cố tiếp tục như thể công cụ đã chạy thành công."
    ),
    ToolSignalType.PERMISSION_DENIED: (
        "Dừng lại và báo Master rằng hành động này cần quyền cao hơn hoặc cần "
        "xác nhận thủ công. KHÔNG tự ý bỏ qua cổng bảo mật."
    ),
    ToolSignalType.PARTIAL_RESULT: (
        "Sử dụng phần dữ liệu đã có và thông báo rõ với Master rằng kết quả "
        "có thể chưa đầy đủ. Đề nghị Master xác nhận nếu cần độ chính xác cao hơn."
    ),
    ToolSignalType.NETWORK_TIMEOUT: (
        "Thử lại sau 3 giây hoặc dùng nguồn dữ liệu thay thế. "
        "Nếu không thể, báo Master tình trạng mất kết nối mạng."
    ),
}


def format_tool_signal(
    signal_type: ToolSignalType,
    tool_name: str,
    detail: Optional[str] = None,
) -> str:
    """
    Tạo chuỗi ToolSignal chuẩn hóa để đưa vào context của Model.

    Format:
        [TOOL_SIGNAL:{TYPE}] Tool <name>: <detail>
        Chỉ thị tiếp theo: <next_action>
    """
    detail_part = f" {detail}" if detail else ""
    next_action = _NEXT_ACTION_MAP.get(signal_type, "Kiểm tra lại và báo cáo Master.")
    return (
        f"[TOOL_SIGNAL:{signal_type.value}] Tool `{tool_name}`:{detail_part}\n"
        f"Chỉ thị tiếp theo: {next_action}"
    )


def classify_obs_to_signal(
    tool_name: str,
    obs: Optional[str],
) -> Optional[str]:
    """
    Phân loại observation từ Tool và trả về ToolSignal nếu cần.
    Trả về None nếu observation hợp lệ và không cần can thiệp.
    """
    if obs is None:
        return format_tool_signal(
            ToolSignalType.EXECUTION_ERROR, tool_name,
            "Tool không trả về phản hồi (None output)."
        )

    stripped = obs.strip()

    # Trường hợp rỗng hoàn toàn
    _EMPTY_SENTINELS = {"[]", "{}", '""', "''", "None", "", "null"}
    _EMPTY_PHRASES = {
        "Không tìm thấy thông tin phù hợp trong bộ nhớ.",
        "No results found.",
        "Không tìm thấy kết quả.",
        "Không có dữ liệu.",
    }
    if stripped in _EMPTY_SENTINELS or stripped in _EMPTY_PHRASES:
        return format_tool_signal(
            ToolSignalType.EMPTY_RESULT, tool_name,
            "Không tìm thấy dữ liệu khớp với truy vấn trong kho tri thức nội bộ."
        )

    # Trường hợp lỗi kỹ thuật
    obs_lower = stripped.lower()
    _ERROR_KEYWORDS = [
        "error executing tool", "exception", "traceback", "errno",
        "connection refused", "timed out", "timeout",
        "500 internal server", "503 service unavailable",
    ]
    for kw in _ERROR_KEYWORDS:
        if kw in obs_lower:
            return format_tool_signal(
                ToolSignalType.EXECUTION_ERROR, tool_name,
                f"Lỗi kỹ thuật: {stripped[:200]}"
            )

    # Trường hợp timeout mạng
    _NETWORK_KEYWORDS = ["network error", "connection timeout", "dns resolution failed", "unreachable"]
    for kw in _NETWORK_KEYWORDS:
        if kw in obs_lower:
            return format_tool_signal(
                ToolSignalType.NETWORK_TIMEOUT, tool_name,
                f"Mất kết nối mạng khi gọi Tool."
            )

    # Observation hợp lệ — không can thiệp
    return None
