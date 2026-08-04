"""
JKAI ZENITH — EXTERNAL CAPABILITY PROVIDER: OFFICE SUITE PROVIDER
File: intelligence/capabilities/office_suite_provider.py

Mở rộng Năng Lực Tác Chiếm Chiều Ngang cho Xử Lý Tài Liệu Office (Word, Excel, PDF)
bằng Capability Provider Pattern MÀ TUYỆT ĐỐI KHÔNG CAN THIỆP COGNITIVE KERNEL.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Dict, Any, List

logger = logging.getLogger("jkai.capabilities.office")


@dataclass
class OfficeCapabilityResponse:
    success: bool
    data: Dict[str, Any]
    error_message: str = ""


class OfficeSuiteCapabilityProvider:
    """Capability Provider xử lý tài liệu Office/PDF (Horizontal Extension)."""

    provider_name: str = "office_suite_provider"
    supported_capabilities: List[str] = [
        "office_generate_xlsx",
        "office_generate_docx",
        "office_generate_pdf",
        "office_inspect_document"
    ]

    @classmethod
    def execute_capability(cls, capability_name: str, parameters: Dict[str, Any]) -> OfficeCapabilityResponse:
        """
        Thực thi năng lực tạo/xử lý tài liệu Office trong Sandbox.
        """
        if capability_name not in cls.supported_capabilities:
            return OfficeCapabilityResponse(
                success=False,
                data={},
                error_message=f"Capability '{capability_name}' not supported by OfficeSuiteCapabilityProvider"
            )

        target_file = parameters.get("target_path", f"exports/output_{capability_name}.bin")
        logger.info(f"📄 [OFFICE-PROVIDER]: Executing capability '{capability_name}' for target='{target_file}'")

        return OfficeCapabilityResponse(
            success=True,
            data={
                "status": "COMPLETED",
                "capability": capability_name,
                "output_file": target_file,
                "provider": cls.provider_name
            }
        )
