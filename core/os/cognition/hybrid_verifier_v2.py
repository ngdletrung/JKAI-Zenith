"""
JKAI ZENITH AI OS — HYBRID VERIFICATION & CONTEXT FRESHNESS (PHASE 9)
File: core/os/cognition/hybrid_verifier_v2.py

Implements:
- Hybrid Critic Gate (D4, D10, D16)
- Verification Context Freshness (D19, D31, P0-3)
- Critic Non-Override Invariant (D16: LLM Semantic Audit CANNOT override deterministic failure)
"""

from __future__ import annotations
import logging
from typing import Dict, List, Any, Optional, Tuple

from core.os.cognition.deep_schemas import VerificationContextHash
from core.os.cognition.event_model import emit_contract_violation, event_store

logger = logging.getLogger("jkai.cognition.hybrid_verifier")


class HybridVerifierV2:
    """
    3-Stage Hybrid Verification Engine:
    Stage 1: Deterministic Layer (Tests, Compiler, Linter)
    Stage 2: Evidence Sufficiency Gate
    Stage 3: LLM Semantic Audit (Subordinate to Deterministic Layer)
    """

    @staticmethod
    def verify(
        deterministic_passed: bool,
        evidence_sufficient: bool,
        llm_semantic_approved: bool,
        deterministic_logs: str = "",
        mission_id: str = "m_default",
        trace_id: str = "trace_default"
    ) -> Tuple[bool, str]:
        # Stage 1: Deterministic check is SUPREME (D16)
        if not deterministic_passed:
            logger.warning("[D16-DETERMINISTIC-FAIL] Deterministic check failed: %s", deterministic_logs)
            if llm_semantic_approved:
                # LLM claimed PASS while tests failed -> Intercepted by D16
                emit_contract_violation(
                    contract_id="D16",
                    mission_id=mission_id,
                    trace_id=trace_id,
                    expected="Verdict follows deterministic failure",
                    actual="LLM Semantic Audit attempted PASS override",
                    recovery_policy="ABORT",
                    enforcement_point="HybridVerifierV2.verify"
                )
            return False, "DETERMINISTIC_VERIFICATION_FAILED"

        # Stage 2: Evidence Sufficiency
        if not evidence_sufficient:
            return False, "INSUFFICIENT_CORROBORATING_EVIDENCE"

        # Stage 3: LLM Semantic Audit
        if not llm_semantic_approved:
            return False, "SEMANTIC_AUDIT_REJECTED"

        return True, "VERIFIED_PASS"

    @staticmethod
    def check_context_freshness(
        verified_context_hash: str,
        current_context_hash: str,
        mission_id: str,
        trace_id: str
    ) -> bool:
        """D19 & D31: Prevents stale merge if target context changed after test execution."""
        if verified_context_hash != current_context_hash:
            logger.warning("[D19-STALE-CONTEXT] Verified hash %s != Current %s. Reverification required!",
                           verified_context_hash, current_context_hash)
            emit_contract_violation(
                contract_id="D19",
                mission_id=mission_id,
                trace_id=trace_id,
                expected=f"Context hash == {current_context_hash}",
                actual=verified_context_hash,
                recovery_policy="REVERIFY_REQUIRED",
                enforcement_point="HybridVerifierV2.check_context_freshness"
            )
            return False
        return True


# Global Hybrid Verifier instance
hybrid_verifier = HybridVerifierV2()
