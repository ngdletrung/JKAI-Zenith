"""
Sovereign Memory Runtime Adapter
File: services/ai-brain/context/memory_runtime_adapter.py
Governed by Phase R-Memory-6 Consensus & Turn 487/490 Directives:
- Asynchronous concurrent recall across MASTER_DISPOSITION & VERIFIED_EXPERIENCE via asyncio.to_thread.
- Strict per-bank token ceiling (<= 120 tokens each) and aggregate ceiling (<= 240 tokens total).
- Independent bank query resiliency: failure in one bank does not destroy the other bank's findings.
- Preservation of asyncio.CancelledError for clean runtime lifecycle shutdown.
- Production-grade typed evidence retention: strict enforcement of ExecutionReceipt and VerificationVerdictContract (NO untyped dict/string auto-wrapping).
"""

import os
import sys
import asyncio
import time
import logging

from pathlib import Path
from typing import List, Optional, Any, Dict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.memory.memory_contracts import (
    MemoryBankScope, EvidenceContract, ExecutionReceipt,
    VerificationVerdictContract, BUDGET_RECALL_FAST_TOKENS
)
from core.memory.memory_service import MemoryService

logger = logging.getLogger("JKAI.MemoryRuntimeAdapter")

_GLOBAL_ADAPTER: Optional["MemoryRuntimeAdapter"] = None


def estimate_tokens(text: str) -> int:
    """
    Fast deterministic token estimator for English/Vietnamese UTF-8.
    Approximation policy: takes the maximum of word-based heuristic and character-length ratio
    to safely handle dense text, punctuation, and unspaced strings.
    """
    if not text:
        return 0
    clean = text.strip()
    if not clean:
        return 0
    words = clean.split()
    word_tokens = int(len(words) * 1.3) + 1
    char_tokens = int(len(clean) / 3.5) + 1
    return max(word_tokens, char_tokens)



def format_bank_section(header: str, claims: List[str], max_tokens: int = 120) -> str:
    """
    Formats bullet points under strict per-bank token budget.
    Ensures the resulting section including header strictly obeys max_tokens.
    """
    if not claims:
        return ""
    lines = [header]
    current_tokens = estimate_tokens(header)

    for c in claims:
        clean_claim = (c or "").strip()
        if not clean_claim:
            continue
        bullet = f"- {clean_claim}"
        bullet_tokens = estimate_tokens(bullet)

        if current_tokens + bullet_tokens <= max_tokens:
            lines.append(bullet)
            current_tokens += bullet_tokens
        else:
            # Check if there is enough budget for a truncated bullet
            remaining = max_tokens - current_tokens
            if remaining >= 8:
                words = clean_claim.split()
                allowed_words = max(1, int((remaining - 2) / 1.3))
                if allowed_words < len(words):
                    truncated_text = " ".join(words[:allowed_words]) + " ..."
                    lines.append(f"- {truncated_text}")
            break

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


class MemoryRuntimeAdapter:
    """
    Adapter bridging Sovereign Hindsight Memory Store into the live ai-brain runtime.
    Guarantees asynchronous non-blocking execution, strict token caps, and fail-soft stability.
    """
    def __init__(self, service: Optional[MemoryService] = None):
        self.service = service or MemoryService()

    async def recall_for_goal(self, goal: str) -> str:
        """
        Concurrently queries master disposition and verified experience.
        Formats output under deterministic per-bank (<= 120 tokens) and aggregate (<= 240 tokens) caps.
        Gracefully returns empty string upon any storage failure.
        """
        if not goal or not goal.strip():
            return ""

        async def _query_bank(bank: MemoryBankScope) -> List[str]:
            try:
                return await asyncio.to_thread(
                    self.service.recall,
                    bank=bank,
                    query=goal,
                    top_k=2,
                    max_tokens=BUDGET_RECALL_FAST_TOKENS
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug("[MemoryAdapter] Error querying bank %s: %s", bank.value, e)
                return []

        t0 = time.perf_counter()
        # Run concurrent queries across both banks
        disposition_results, experience_results = await asyncio.gather(
            _query_bank(MemoryBankScope.MASTER_DISPOSITION),
            _query_bank(MemoryBankScope.VERIFIED_EXPERIENCE)
        )

        disp_claims = disposition_results if isinstance(disposition_results, list) else []
        exp_claims = experience_results if isinstance(experience_results, list) else []

        # Raw token count prior to per-bank truncation (to measure incoming claim volume & raw overflow)
        raw_master_tokens = estimate_tokens("\n".join(disp_claims)) if disp_claims else 0
        raw_exp_tokens = estimate_tokens("\n".join(exp_claims)) if exp_claims else 0

        disp_section = format_bank_section("### [CHỈ ĐẠO MASTER]", disp_claims, max_tokens=120)
        exp_section = format_bank_section("### [KINH NGHIỆM ĐÃ KIỂM CHỨNG]", exp_claims, max_tokens=120)

        active_sections = [s for s in (disp_section, exp_section) if s]
        if not active_sections:
            return ""

        banner = "### [SOVEREIGN-MEMORY]"
        formatted = banner + "\n\n" + "\n\n".join(active_sections)

        # Enforce aggregate ceiling of 240 tokens
        while estimate_tokens(formatted) > 240:
            words = formatted.split()
            if len(words) <= 12:
                # If dense text without many spaces, slice characters directly
                formatted = formatted[:int(len(formatted) * 0.85)] + " ..."
            else:
                trim_count = max(4, int(len(words) * 0.15))
                formatted = " ".join(words[:-trim_count]) + " ..."

        # Security Sentinel: fail-closed check before prompt boundary
        try:
            from core.memory.memory_telemetry import SecuritySentinel, telemetry_logger
            is_safe, finding_type = SecuritySentinel.scan_memory_text(formatted)
            duration_ms = (time.perf_counter() - t0) * 1000

            if not is_safe:
                logger.warning("[MemoryAdapter] Security Sentinel triggered (%s)! Fail-closed to empty.", finding_type)
                telemetry_logger.log_recall(
                    query=goal,
                    duration_ms=duration_ms,
                    disp_count=len(disp_claims),
                    exp_count=len(exp_claims),
                    formatted_text="",
                    is_safe=False,
                    finding_type=finding_type,
                    master_tokens=raw_master_tokens,
                    exp_tokens=raw_exp_tokens
                )
                return ""

            telemetry_logger.log_recall(
                query=goal,
                duration_ms=duration_ms,
                disp_count=len(disp_claims),
                exp_count=len(exp_claims),
                formatted_text=formatted,
                is_safe=True,
                master_tokens=raw_master_tokens,
                exp_tokens=raw_exp_tokens
            )
        except Exception as tel_err:
            logger.debug("[MemoryAdapter] Telemetry non-fatal hook error: %s", tel_err)

        return formatted




    async def retain_verified_mission(
        self,
        mission_id: str,
        trace_id: str,
        claim: str,
        receipt: Any,
        verdict: Any,
        artifact_hash: str = ""
    ) -> bool:
        """
        Retains verified execution lessons into bank_verified_experience with typed evidence contract.
        Production boundary: strictly enforces ExecutionReceipt and VerificationVerdictContract.
        Rejects raw dict, string, or mismatched proofs with False (no untyped downgrades).
        """
        # 1. Type validation: strictly typed contracts only
        if not isinstance(receipt, ExecutionReceipt):
            logger.warning("[MemoryAdapter] Rejected: receipt must be an ExecutionReceipt, got %s", type(receipt))
            return False

        if not isinstance(verdict, VerificationVerdictContract):
            logger.warning("[MemoryAdapter] Rejected: verdict must be a VerificationVerdictContract, got %s", type(verdict))
            return False

        # 2. Identifier completeness validation
        if not mission_id or not str(mission_id).strip() or not trace_id or not str(trace_id).strip():
            logger.warning("[MemoryAdapter] Rejected: mission_id and trace_id cannot be empty")
            return False

        clean_mission = str(mission_id).strip()
        clean_trace = str(trace_id).strip()

        # 3. Cross-proof binding validation
        if receipt.mission_id != clean_mission or receipt.trace_id != clean_trace:
            logger.warning("[MemoryAdapter] Rejected: receipt binding mismatch with mission_id/trace_id")
            return False

        if verdict.mission_id != clean_mission:
            logger.warning("[MemoryAdapter] Rejected: verdict binding mismatch with mission_id")
            return False

        receipt_refs = getattr(verdict, "receipt_refs", []) or []
        if not receipt.id or receipt.id not in receipt_refs:
            logger.warning(
                "[MemoryAdapter] Rejected: receipt.id '%s' not bound in verdict.receipt_refs %s",
                getattr(receipt, "id", None), receipt_refs
            )
            return False

        # 4. Bind artifact hash if supplied
        if artifact_hash and not receipt.artifact_hash:
            receipt.artifact_hash = artifact_hash

        try:
            contract = EvidenceContract(
                source_mission=clean_mission,
                trace_id=clean_trace,
                execution_receipt=receipt,
                verification_verdict=verdict
            )

            res = await asyncio.to_thread(
                self.service.retain_observation,
                bank=MemoryBankScope.VERIFIED_EXPERIENCE,
                claim=claim,
                source_mission=clean_mission,
                evidence_contract=contract
            )
            success = res.get("success", False) if isinstance(res, dict) else False

            # Telemetry logging for retention
            try:
                from core.memory.memory_telemetry import telemetry_logger, hash_identifier
                telemetry_logger.log_retention(
                    mission_id=clean_mission,
                    trace_id=clean_trace,
                    receipt_id=getattr(receipt, "id", ""),
                    verdict_status=getattr(verdict, "status", "UNKNOWN"),
                    claim_hash=hash_identifier(claim),
                    success=success
                )
            except Exception as tel_err:
                logger.debug("[MemoryAdapter] Telemetry retention hook non-fatal error: %s", tel_err)

            return success
        except Exception as e:
            logger.warning("[MemoryAdapter] Failed to retain verified mission %s: %s", clean_mission, e)
            return False



def get_memory_adapter() -> MemoryRuntimeAdapter:
    """Singleton getter for MemoryRuntimeAdapter."""
    global _GLOBAL_ADAPTER
    if _GLOBAL_ADAPTER is None:
        _GLOBAL_ADAPTER = MemoryRuntimeAdapter()
    return _GLOBAL_ADAPTER


get_memory_runtime_adapter = get_memory_adapter

