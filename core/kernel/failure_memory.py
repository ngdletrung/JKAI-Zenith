# -*- coding: utf-8 -*-
"""
JKAI Failure Memory & Known Gaps Self-Awareness Layer (P1).
Provides closed-loop recording and reading of:
1. Critic findings (M1: closes the 1-write, 0-read gap).
2. Known gaps registry (M2/M3: loads KNOWN_GAPS.md into agent prompt).
"""

import json
import os
import time
from typing import Any, Dict, List, Optional


_FAILURE_LOG_PATH = "data/knowledge/critic_findings_ledger.jsonl"
_KNOWN_GAPS_PATH = "data/knowledge/KNOWN_GAPS.md"


def record_critic_finding(task_id: str, action_plan: List[str], details: Optional[Dict[str, Any]] = None) -> None:
    """Ghi nhận phát hiện và kế hoạch sửa lỗi của Hội đồng Thẩm định (Critic) vào sổ bộ dài hạn."""
    os.makedirs(os.path.dirname(_FAILURE_LOG_PATH), exist_ok=True)
    entry = {
        "ts": time.time(),
        "task_id": str(task_id),
        "action_plan": list(action_plan or []),
        "details": details or {},
    }
    with open(_FAILURE_LOG_PATH, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_critic_findings(task_id: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
    """Đọc lại các phát hiện phản biện gần nhất để nạp vào nhận thức của Agent (Đóng mạch M1)."""
    if not os.path.exists(_FAILURE_LOG_PATH):
        return []
    matching = []
    try:
        with open(_FAILURE_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if not task_id or obj.get("task_id") == task_id or task_id in obj.get("task_id", ""):
                        matching.append(obj)
                except Exception:
                    pass
    except Exception:
        return []
    return matching[-limit:]


def load_known_gaps_summary(max_lines: int = 40) -> str:
    """Đọc tóm tắt các khiếm khuyết đã biết từ KNOWN_GAPS.md (Đóng mạch M2/M3)."""
    if not os.path.exists(_KNOWN_GAPS_PATH):
        return ""
    try:
        with open(_KNOWN_GAPS_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip().startswith(("### GAP-", "* **Quy tắc"))]
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def get_failure_awareness_prompt(task_id: Optional[str] = None, goal: str = "") -> str:
    """Tạo khối chỉ dẫn tự nhận thức về điểm yếu quá khứ qua Meta CCA Error Signatures."""
    parts = []
    # 1. Trích xuất động từ ErrorSignatureEngine (Meta CCA - Tự học thất bại)
    try:
        from core.kernel.error_signature import get_error_signature_engine
        sig_prompt = get_error_signature_engine().render_dynamic_awareness_prompt(goal or "")
        if sig_prompt:
            parts.append(sig_prompt)
    except Exception:
        pass

    # 2. Fallback nhẹ sang KNOWN_GAPS nếu signatures rỗng
    if not parts:
        gaps = load_known_gaps_summary(max_lines=20)
        if gaps:
            parts.append(f"⚠️ [SỔ BỘ ĐIỂM YẾU HỆ THỐNG ĐÃ BIẾT - TUYỆT ĐỐI KHÔNG TÁI PHẠM]:\n{gaps}")

    findings = get_critic_findings(task_id=task_id, limit=2)
    if findings:
        f_list = []
        for item in findings:
            plans = "; ".join(item.get("action_plan", []))
            f_list.append(f"- Nhiệm vụ {item.get('task_id')}: Critic yêu cầu: {plans}")
        parts.append(f"🔍 [BÀI HỌC CẢNH BÁO TỪ HỘI ĐỒNG THẨM ĐỊNH GẦN NHẤT]:\n" + "\n".join(f_list))

    return "\n\n".join(parts)


class MissionStateStoreProxy:
    """Proxy tương thích với các lệnh gọi cũ get_mission_state_store()."""
    def ensure_mission(self, task_id: str, goal: str):
        pass

    def record_critic_finding(self, task_id: str, action_plan: List[str]):
        record_critic_finding(task_id, action_plan)


def get_mission_state_store():
    return MissionStateStoreProxy()
