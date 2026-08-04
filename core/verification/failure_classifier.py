"""
JKAI ZENITH — VERIFICATION PACKAGE: FAILURE CLASSIFIER (v2.1)
File: core/verification/failure_classifier.py
"""

from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional

from core.contracts.verification_contract import (
    VerificationResult,
    FailureClassification,
    RecoveryStrategy,
)

logger = logging.getLogger("jkai.verification.classifier")


class LegacyClassificationResult:
    def __init__(self, category: str, recommended_recovery: str):
        self.category = category
        self.recommended_recovery = recommended_recovery


class FailureClassifier:
    """Bộ Phân Loại Lỗi Tác Chiến (Failure Classifier)."""

    def classify(self, eval_res: Any, obs: Any = None) -> LegacyClassificationResult:
        if obs and getattr(obs, "status_code", 0) == 507:
            return LegacyClassificationResult(category="RESOURCE_FAILURE", recommended_recovery="FALLBACK_MODEL")
        return LegacyClassificationResult(category="KNOWLEDGE_FAILURE", recommended_recovery="MORE_CONTEXT")

    @classmethod
    def classify_failure(cls, missing_criteria: List[str], logs: List[str]) -> tuple[FailureClassification, RecoveryStrategy]:
        """
        Phân loại lỗi và đề xuất chiến lược phục hồi.
        """
        for miss in missing_criteria:
            if "POLICY_VIOLATION" in miss or "SECURITY_DENIED" in miss:
                return FailureClassification.POLICY_FAILURE, RecoveryStrategy.ABORT
            if "EXCEL_CORRUPTED" in miss or "FILE_EMPTY_ZERO_BYTES" in miss:
                return FailureClassification.VERIFICATION_FAILURE, RecoveryStrategy.DIAGNOSE_AND_REPAIR
            if "PHYSICAL_FILE_MISSING" in miss or "TOOL_EXCEPTION" in miss:
                return FailureClassification.TOOL_FAILURE, RecoveryStrategy.SUBSTITUTE_CAPABILITY
            if "MODEL_HALLUCINATION" in miss or "INVALID_JSON_FORMAT" in miss:
                return FailureClassification.MODEL_FAILURE, RecoveryStrategy.CHANGE_MODEL
            if "TIMEOUT" in miss or "CONNECTION_ERROR" in miss:
                return FailureClassification.TRANSIENT, RecoveryStrategy.RETRY

        return FailureClassification.PLAN_FAILURE, RecoveryStrategy.REPLAN
