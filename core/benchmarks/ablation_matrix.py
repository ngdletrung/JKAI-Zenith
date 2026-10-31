"""
JKAI Ablation Matrix & Tiered Evaluation Engine
File: core/benchmarks/ablation_matrix.py

Triển khai cấu trúc 6 tầng cắt bỏ A0–A5 theo phân tích của Master LeeTrung:
A0: Model only (zero tools, direct answer)
A1: Model + direct tools (no governor/verification)
A2: Model + memory
A3: Model + memory + tools
A4: JKAI full without LoRA (Canonical)
A5: JKAI full + LoRA (Specialized)
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


class AblationTier(str, Enum):
    A0_MODEL_ONLY = "A0_MODEL_ONLY"
    A1_MODEL_DIRECT_TOOLS = "A1_MODEL_DIRECT_TOOLS"
    A2_MODEL_MEMORY = "A2_MODEL_MEMORY"
    A3_MODEL_MEMORY_TOOLS = "A3_MODEL_MEMORY_TOOLS"
    A4_JKAI_CANONICAL = "A4_JKAI_CANONICAL"
    A5_JKAI_LORA = "A5_JKAI_LORA"


@dataclass
class AblationConfig:
    tier: AblationTier
    has_tools: bool
    has_memory: bool
    has_governor: bool
    has_verification: bool
    has_lora: bool
    description: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d


ABLATION_CONFIGS: Dict[AblationTier, AblationConfig] = {
    AblationTier.A0_MODEL_ONLY: AblationConfig(
        tier=AblationTier.A0_MODEL_ONLY,
        has_tools=False,
        has_memory=False,
        has_governor=False,
        has_verification=False,
        has_lora=False,
        description="Thuần suy luận xác suất của Model, 0 tools, trả lời trực tiếp."
    ),
    AblationTier.A1_MODEL_DIRECT_TOOLS: AblationConfig(
        tier=AblationTier.A1_MODEL_DIRECT_TOOLS,
        has_tools=True,
        has_memory=False,
        has_governor=False,
        has_verification=False,
        has_lora=False,
        description="Model gọi công cụ trực tiếp không qua Policy Governor và Verification."
    ),
    AblationTier.A2_MODEL_MEMORY: AblationConfig(
        tier=AblationTier.A2_MODEL_MEMORY,
        has_tools=False,
        has_memory=True,
        has_governor=False,
        has_verification=False,
        has_lora=False,
        description="Model kết hợp truy xuất bộ nhớ (Memory RAG), không dùng công cụ."
    ),
    AblationTier.A3_MODEL_MEMORY_TOOLS: AblationConfig(
        tier=AblationTier.A3_MODEL_MEMORY_TOOLS,
        has_tools=True,
        has_memory=True,
        has_governor=False,
        has_verification=False,
        has_lora=False,
        description="Model có bộ nhớ và công cụ, nhưng thiếu chốt chặn Verification độc lập."
    ),
    AblationTier.A4_JKAI_CANONICAL: AblationConfig(
        tier=AblationTier.A4_JKAI_CANONICAL,
        has_tools=True,
        has_memory=True,
        has_governor=True,
        has_verification=True,
        has_lora=False,
        description="Toàn bộ hệ thống chuẩn JKAI: Controller + Memory + Governed Actuators + Verification L1-L4 (Chưa kích hoạt LoRA)."
    ),
    AblationTier.A5_JKAI_LORA: AblationConfig(
        tier=AblationTier.A5_JKAI_LORA,
        has_tools=True,
        has_memory=True,
        has_governor=True,
        has_verification=True,
        has_lora=True,
        description="Toàn bộ hệ thống chuẩn JKAI kết hợp LoRA adapter chuyên biệt."
    )
}


def get_ablation_config(tier: AblationTier) -> AblationConfig:
    return ABLATION_CONFIGS[tier]


class AblationComparisonEngine:
    """So sánh khoa học giữa các cấu hình cắt bỏ và thẩm định tính chính danh của LoRA."""
    def __init__(self, tier_reports: Dict[AblationTier, Dict[str, Any]]):
        self.tier_reports = tier_reports

    def evaluate_governance_impact(self) -> Dict[str, Any]:
        """Đo lường mức độ nâng cao năng lực nhờ có Hệ điều hành kiểm soát (Governance Runtime)."""
        a0 = self.tier_reports.get(AblationTier.A0_MODEL_ONLY, {}).get("completion_rate_pct", 0.0)
        a1 = self.tier_reports.get(AblationTier.A1_MODEL_DIRECT_TOOLS, {}).get("completion_rate_pct", 0.0)
        a4 = self.tier_reports.get(AblationTier.A4_JKAI_CANONICAL, {}).get("completion_rate_pct", 0.0)

        # False-positive completion in A1: Tool chạy exit code 0 nhưng verification thực tế rớt
        a1_unverified_fp = self.tier_reports.get(AblationTier.A1_MODEL_DIRECT_TOOLS, {}).get("false_positive_rate_pct", 0.0)

        return {
            "baseline_model_only_pct": a0,
            "direct_tools_pct": a1,
            "canonical_jkai_pct": a4,
            "governance_net_gain_pct": round(a4 - a0, 2),
            "tool_governor_gain_pct": round(a4 - a1, 2),
            "unverified_tool_false_positive_pct": a1_unverified_fp
        }

    def evaluate_lora_justification(self) -> Dict[str, Any]:
        """
        Quy tắc bất biến: LoRA chỉ được phép promote nếu chứng minh được:
        1. Net positive gain so với A4 (JKAI Canonical không LoRA) trên tập ngoài miền (OOD).
        2. Tỷ lệ suy giảm kỹ năng cơ sở (regression rate) = 0.
        """
        a4_metrics = self.tier_reports.get(AblationTier.A4_JKAI_CANONICAL, {})
        a5_metrics = self.tier_reports.get(AblationTier.A5_JKAI_LORA, {})

        a4_rate = a4_metrics.get("completion_rate_pct", 0.0)
        a5_rate = a5_metrics.get("completion_rate_pct", 0.0)
        regression_count = a5_metrics.get("regressed_tasks_count", 0)

        marginal_gain = round(a5_rate - a4_rate, 2)
        justified = (marginal_gain > 0.0) and (regression_count == 0)

        return {
            "a4_canonical_rate_pct": a4_rate,
            "a5_lora_rate_pct": a5_rate,
            "marginal_gain_pct": marginal_gain,
            "regressed_tasks_count": regression_count,
            "lora_promoted": justified,
            "verdict": "PROMOTED" if justified else "REJECTED_INSUFFICIENT_MARGINAL_GAIN_OR_REGRESSION"
        }
