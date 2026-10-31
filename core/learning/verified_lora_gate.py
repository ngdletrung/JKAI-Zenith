"""
JKAI Verified LoRA Gate & Intervention Hierarchy Engine
File: core/learning/verified_lora_gate.py

Triển khai tiêu chuẩn Phase R5 theo Cương lĩnh của Master LeeTrung:
- Thứ tự can thiệp nghiêm ngặt: Prompt -> Memory -> Route -> Tool -> LoRA -> Model Swap.
- Chặn đứng hành vi dùng LoRA bừa bãi để sửa lỗi do thiếu tool/prompt/memory.
- Ngưỡng tối thiểu Gold Traces: Bắt buộc >= 100 gold traces mới được phép kích hoạt tiến trình huấn luyện.
- Đánh giá Held-Out OOD: Tăng trưởng ròng (gain > 0) và tỷ lệ hồi quy (regression = 0). Tự động rollback nếu vi phạm.
"""

from enum import IntEnum, Enum
from typing import Dict, Any, List, Tuple, Optional


class InterventionType(IntEnum):
    """Thứ tự can thiệp bắt buộc từ rẻ nhất/an toàn nhất đến đắt nhất/rủi ro nhất."""
    PROMPT_CONTEXT = 1       # 1. Sửa prompt / context (rẻ nhất, an toàn nhất)
    MEMORY_UPDATE = 2        # 2. Cập nhật / sửa memory tri thức
    ROUTING_CONTROLLER = 3   # 3. Điều chỉnh chiến lược controller / routing
    TOOL_RUNTIME = 4         # 4. Sửa tool / runtime actuator
    LORA_FINETUNE = 5        # 5. Fine-tune / LoRA (phương án áp chót, chỉ dùng khi 1-4 bất khả thi)
    MODEL_SWAP = 6           # 6. Đổi model nền tảng (phương án cuối cùng)


class RootCause(str, Enum):
    MISSING_CONTEXT = "MISSING_CONTEXT"
    STALE_MEMORY = "STALE_MEMORY"
    WRONG_ROUTING = "WRONG_ROUTING"
    TOOL_EXECUTION_FAILURE = "TOOL_EXECUTION_FAILURE"
    MODEL_REASONING_DEFECT = "MODEL_REASONING_DEFECT"


class InterventionSelector:
    """Xác định can thiệp tối ưu nhất, ngăn chặn lạm dụng LoRA."""
    @staticmethod
    def select_appropriate_intervention(root_cause: RootCause) -> InterventionType:
        if root_cause == RootCause.MISSING_CONTEXT:
            return InterventionType.PROMPT_CONTEXT
        elif root_cause == RootCause.STALE_MEMORY:
            return InterventionType.MEMORY_UPDATE
        elif root_cause == RootCause.WRONG_ROUTING:
            return InterventionType.ROUTING_CONTROLLER
        elif root_cause == RootCause.TOOL_EXECUTION_FAILURE:
            return InterventionType.TOOL_RUNTIME
        else:  # MODEL_REASONING_DEFECT
            return InterventionType.LORA_FINETUNE


class GoldTraceLedger:
    """Sổ cái lưu trữ các vết thực thi vàng (Gold Traces) đã qua kiểm chứng L1-L4."""
    MIN_TRACES_FOR_LORA = 100

    def __init__(self):
        self.traces: List[Dict[str, Any]] = []

    def add_trace(self, trace_id: str, prompt: str, actions: List[str], verdict: str, verified_by: str):
        if verdict != "COMPLETE" or not verified_by:
            raise ValueError("Chỉ chấp nhận trace đã kiểm chứng COMPLETE vào Gold Ledger!")
        self.traces.append({
            "trace_id": trace_id,
            "prompt": prompt,
            "actions": actions,
            "verdict": verdict,
            "verified_by": verified_by
        })

    def count(self) -> int:
        return len(self.traces)

    def is_eligible_for_lora(self) -> bool:
        """Quy tắc bất biến: Chỉ huấn luyện khi đạt >= 100 gold traces."""
        return len(self.traces) >= self.MIN_TRACES_FOR_LORA


class LoRAPromotionGate:
    """Cổng thẩm định và thăng hạng LoRA với cơ chế Anti-Regression."""
    def __init__(self, min_ood_gain_pct: float = 2.0, max_allowed_regressions: int = 0):
        self.min_ood_gain_pct = min_ood_gain_pct
        self.max_allowed_regressions = max_allowed_regressions

    def evaluate_candidate(
        self,
        gold_trace_count: int,
        base_model_metrics: Dict[str, Any],
        lora_candidate_metrics: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        # 1. Kiểm tra điều kiện tiên quyết: Số lượng gold traces
        if gold_trace_count < GoldTraceLedger.MIN_TRACES_FOR_LORA:
            return False, f"REJECTED_INSUFFICIENT_GOLD_TRACES: Cần tối thiểu {GoldTraceLedger.MIN_TRACES_FOR_LORA} traces, hiện có {gold_trace_count}", {}

        # 2. Kiểm tra hiệu năng ngoài miền (OOD gain)
        base_ood = base_model_metrics.get("ood_accuracy_pct", 0.0)
        lora_ood = lora_candidate_metrics.get("ood_accuracy_pct", 0.0)
        marginal_gain = round(lora_ood - base_ood, 2)

        if marginal_gain < self.min_ood_gain_pct:
            return False, f"REJECTED_LOW_MARGINAL_GAIN: Tăng trưởng OOD ({marginal_gain}%) < ngưỡng yêu cầu ({self.min_ood_gain_pct}%)", {
                "marginal_gain_pct": marginal_gain
            }

        # 3. Kiểm tra chống hồi quy (Anti-Regression Gate)
        regressions = lora_candidate_metrics.get("base_task_regressions", 0)
        if regressions > self.max_allowed_regressions:
            return False, f"REJECTED_CATASTROPHIC_REGRESSION: Gây suy giảm {regressions} tác vụ cơ sở (tối đa cho phép {self.max_allowed_regressions})", {
                "regressions": regressions,
                "action": "ROLLBACK_TO_BASE_MODEL"
            }

        # Đạt mọi tiêu chuẩn thăng hạng
        return True, "PROMOTED_VERIFIED_LORA", {
            "gold_traces": gold_trace_count,
            "marginal_gain_pct": marginal_gain,
            "regressions": regressions,
            "status": "ACTIVE_IN_PRODUCTION"
        }
