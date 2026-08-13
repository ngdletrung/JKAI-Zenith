"""
core/os/cognition/escl/prompt_contract_registry.py
E3 — Prompt Contract Registry.

Versioned System Prompt Specifications with strict Input/Output Contracts,
Allowed Actions, and Semantic Requirement Bindings.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from core.os.cognition.escl.contracts import PromptContract


class PromptContractRegistry:
    """Authoritative registry for versioned Prompt Contracts."""

    def __init__(self):
        self._prompts: Dict[str, PromptContract] = {}
        self._register_default_prompts()

    def register(self, contract: PromptContract):
        self._prompts[contract.prompt_id] = contract

    def get(self, prompt_id: str) -> Optional[PromptContract]:
        return self._prompts.get(prompt_id)

    def _register_default_prompts(self):
        # 1. RECEPTIONIST_OFFICE_V2
        self.register(PromptContract(
            prompt_id="PROMPT_OFFICE_SYNTHESIS_V2",
            version="2.2.0",
            role="RECEPTIONIST",
            expected_output_format="JSON_ACTION",
            allowed_actions=["OFFICE_SUITE_MASTER", "execute_skill"],
            forbidden_behaviors=[
                "RAW_FILE_MUTATION_WITHOUT_GOVERNOR",
                "FAKE_COMPLETION_WITHOUT_ACTION",
                "OMITTING_CHARTS_WHEN_REQUESTED"
            ],
            required_fields=["action", "format", "title"],
            system_instruction=(
                "Bạn là JKAI Zenith Office Architect. Khi Master yêu cầu tạo bảng tính/văn bản/biểu đồ, "
                "bắt buộc gọi Action: OFFICE_SUITE_MASTER kèm đầy đủ tham số cấu trúc, công thức và biểu đồ. "
                "Tuyệt đối không trả lời lý thuyết suông khi chưa xuất file."
            )
        ))

        # 2. CODE_SYNTHESIS_V2
        self.register(PromptContract(
            prompt_id="PROMPT_CODE_SYNTHESIS_V2",
            version="2.2.0",
            role="EXECUTOR",
            expected_output_format="JSON_ACTION",
            allowed_actions=["PYTHON_SANDBOX_RUNNER", "write_to_file", "replace_file_content"],
            forbidden_behaviors=["UNSAFE_RAW_EXECUTION"],
            required_fields=["action", "script_code"],
            system_instruction="Chạy mã nguồn trong sandbox có kiểm chứng cú pháp trước khi ghi nhận thành công."
        ))


prompt_contract_registry = PromptContractRegistry()
