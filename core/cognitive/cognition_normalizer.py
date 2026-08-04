"""
JKAI ZENITH — COGNITION LAYER: COGNITION NORMALIZER (v2.1)
File: core/cognitive/cognition_normalizer.py

Chuẩn hóa CognitiveRequest đầu ra đảm bảo tuân thủ Hiến pháp.
"""

from __future__ import annotations
import logging
from core.contracts.cognitive_contract import CognitiveRequest

logger = logging.getLogger("jkai.cognition.normalizer")


class CognitionNormalizer:
    """Chuẩn hóa và thẩm định tính hợp lệ của CognitiveRequest."""

    @classmethod
    def normalize(cls, request: CognitiveRequest) -> CognitiveRequest:
        # Đảm bảo không chứa model name hardcode
        clean_constraints = [c for c in request.constraints if not c.startswith("MODEL_")]
        
        return CognitiveRequest(
            identity=request.identity,
            goal=request.goal,
            intent=request.intent,
            deliverable=request.deliverable,
            constraints=clean_constraints,
            entities=request.entities,
            risk_level=request.risk_level,
            success_criteria=request.success_criteria,
            authority_required=request.authority_required,
            confidence=request.confidence
        )
