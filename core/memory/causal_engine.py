"""
JKAI ZENITH v3 — ADAPTIVE COGNITION LAYER: CAUSAL EXPERIENCE LEARNING ENGINE (v3.0)
File: core/memory/causal_engine.py

Chuyển đổi tri thức Engram từ "Recall" thành "Causal Learning" (Giải thích NGUYÊN NHÂN TẠI SAO - WHY).
Tuân thủ Uy Quyền Tối Thượng: Tri thức Causal chỉ là EVIDENCE (Bằng chứng), KHÔNG PHẢI TRUTH.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from core.contracts.verification_contract import VerificationResult, ExperienceRecord

logger = logging.getLogger("jkai.memory.causal")


@dataclass(frozen=True)
class CausalHypothesis:
    task_signature: str
    recommended_strategy: str
    causal_explanation: str
    confidence_score: float
    is_evidence_only: bool = True  # Luôn đóng dấu BẰNG CHỨNG (EVIDENCE)


class CausalExperienceEngine:
    """Động Cơ Học Tri Thức Nguyên Nhân (Causal Experience Engine)."""

    _hypotheses: Dict[str, CausalHypothesis] = {}

    @classmethod
    def distill_causal_hypothesis(cls, task_signature: str, verification: VerificationResult, strategy_used: str) -> CausalHypothesis:
        """
        Rút trích giả thuyết nguyên nhân thành công/thất bại từ kết quả kiểm thử.
        """
        if verification.passed:
            explanation = f"Strategy '{strategy_used}' succeeded because all verification criteria passed cleanly."
            conf = 0.95
        else:
            explanation = f"Strategy '{strategy_used}' failed due to missing criteria: {verification.missing_criteria}."
            conf = 0.30

        hyp = CausalHypothesis(
            task_signature=task_signature,
            recommended_strategy=strategy_used if verification.passed else "fallback_strategy",
            causal_explanation=explanation,
            confidence_score=conf,
            is_evidence_only=True
        )

        cls._hypotheses[task_signature] = hyp
        logger.info(f"🧬 [CAUSAL-ENGINE]: Distilled hypothesis for '{task_signature}': {explanation}")
        return hyp

    @classmethod
    def get_hypothesis(cls, task_signature: str) -> Optional[CausalHypothesis]:
        """Truy vấn giả thuyết nguyên nhân cho chữ ký tác vụ."""
        return cls._hypotheses.get(task_signature)
