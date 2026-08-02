# -*- coding: utf-8 -*-
# 🏛️ [ZENITH-INTELLIGENCE-CORE]: ECC Cloud Cost Guard v1.1.0 (Zenith Sovereign Refactor)
# 💎 [PILLAR-4]: MODELS & OPTIMIZATION
# 🛡️ CHỈ ÁP DỤNG CHO CÁC CUỘC GỌI CLOUD QUA API KEY (THEO RULES_SOFTWARE.MD)

"""
ECC Cloud Cost Guard (Zenith Edition)
Quản lý ngân sách và định tuyến cho các Model Đám Mây (Gemini, OpenAI, DeepSeek, Anthropic).
TUYỆT ĐỐI KHÔNG ÁP DỤNG CHO OLLAMA/LOCAL MODELS.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
import os

# ─────────────────────────────────────────────
# 🔑 [CLOUD-PROVIDER-REGISTRY]: Ánh xạ từ rules_software.md
# ─────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class CloudCostRecord:
    provider: str  # Google, OpenAI, DeepSeek, Anthropic, X.AI
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    skill_name: str = "general" # Tên skill kích hoạt (VD: SEARCH_WEB_GLOBAL)

@dataclass(frozen=True, slots=True)
class CloudBudgetTracker:
    # Ngân sách mặc định thưa Master ($10 cho toàn bộ Cloud Ops)
    global_budget_limit: float = 10.0 
    records: Tuple[CloudCostRecord, ...] = field(default_factory=tuple)

    def add_record(self, record: CloudCostRecord) -> "CloudBudgetTracker":
        """Nhất thể hóa bản ghi chi phí mới."""
        return CloudBudgetTracker(
            global_budget_limit=self.global_budget_limit,
            records=(*self.records, record),
        )

    @property
    def total_spend(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def is_over_budget(self) -> bool:
        return self.total_spend >= self.global_budget_limit

# ─────────────────────────────────────────────
# 🛰️ [CLOUD-ROUTER]: Định tuyến thông minh giữa các Cloud Providers
# ─────────────────────────────────────────────

class ZenithCloudRouter:
    """💎 [ZENITH-CLOUD-ROUTER]: Điều phối các tác vụ Cloud thâu đêm."""

    # Thứ tự ưu tiên theo rules_software.md thưa Master
    PRIORITY = ["GOOGLE", "DEEPSEEK", "OPENAI", "ANTHROPIC"]

    @staticmethod
    def select_cloud_model(task_type: str, context_length: int) -> Dict:
        """
        Lựa chọn nhà cung cấp và model đám mây tối ưu:
        - Tác vụ siêu tìm kiếm (Search): Ưu tiên Sonnet/GPT-4o
        - Tài liệu cực lớn (>8k): Ưu tiên Gemini 3.5 Flash
        - Lập trình chuyên sâu: Ưu tiên DeepSeek Cloud
        """
        if context_length > 8000:
            return {
                "provider": "GOOGLE",
                "model": "gemini-3.5-flash",
                "reason": "Vượt ngưỡng 8k tokens - Chuyển vùng Gemini thấu thị."
            }
        
        if task_type == "SUPER_SEARCH":
            return {
                "provider": "ANTHROPIC",
                "model": "claude-3-5-sonnet-20240620",
                "reason": "Skill Siêu Tìm Kiếm - Ưu tiên Claude Sonnet để tổng hợp đa tầng."
            }

        # Mặc định thưa Master
        return {
            "provider": "OPENAI",
            "model": "gpt-4o-mini",
            "reason": "Tác vụ Cloud thông thường - Tiết kiệm chi phí."
        }

# ─────────────────────────────────────────────
# 🛡️ [GUARD-RAILS]: Hàng rào bảo vệ ngân sách của Master
# ─────────────────────────────────────────────

def cloud_execution_guard(tracker: CloudBudgetTracker, estimated_cost: float = 0.0):
    """🛡️ Kiểm soát ngưỡng chi phí trước khi thực hiện cuộc gọi Cloud API."""
    if tracker.is_over_budget:
        raise PermissionError(f"🛑 BÁO ĐỘNG: Ngân sách Cloud đã cạn ({tracker.total_spend:.2f}$/10$). Dừng truy cập API để bảo vệ tài chính của Master!")
    
    if (tracker.total_spend + estimated_cost) > tracker.global_budget_limit:
        print(f"⚠️ CẢNH BÁO: Cuộc gọi này có thể khiến ngân sách vượt ngưỡng. Đang thực thi trong chế độ cảnh giác thưa Master.")

# Sovereign Property of Master LeeTrung. ECC Cloud Cost Guard v1.1.0 🏛️💰🛡️
