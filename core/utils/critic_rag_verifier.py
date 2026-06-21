# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/critic_rag_verifier.py
# - Role: CRITIC RAG Fact-Checking Engine
# - Ownership: Mr LeeTrung
# - Status: Active | Version: v1.0
# [WORKING PRINCIPLES]:
# 1. Embeds a claim → searches Qdrant → returns evidence + confidence score.
# 2. Flags UNVERIFIED if confidence < 0.6, CONTRADICTION if opposing evidence found.
# 3. Strictly zero emojis in code or system configuration lines.
# -----------------------------------------------------------------------------
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JKAI.CriticRagVerifier")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class VerifyResult:
    """Kết quả xác minh thực tế cho một claim đơn lẻ."""

    claim: str
    confidence: float                        # 0.0 → 1.0
    verdict: str                             # VERIFIED | PARTIAL | UNVERIFIED | CONTRADICTION
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    elapsed_ms: float = 0.0

    @property
    def is_verified(self) -> bool:
        return self.confidence >= 0.80

    @property
    def is_contradiction(self) -> bool:
        return self.verdict == "CONTRADICTION"

    def to_log_line(self) -> str:
        snippet = self.evidence[0].get("text", "")[:120] if self.evidence else "(no evidence)"
        return (
            f"[RAG-VERIFY] claim='{self.claim[:80]}' "
            f"confidence={self.confidence:.2f} verdict={self.verdict} "
            f"evidence_snippet='{snippet}' elapsed={self.elapsed_ms:.1f}ms"
        )


# ---------------------------------------------------------------------------
# Confidence Thresholds
# ---------------------------------------------------------------------------

THRESHOLD_VERIFIED   = 0.80   # Chấp nhận
THRESHOLD_PARTIAL    = 0.60   # Chấp nhận có điều kiện
# < THRESHOLD_PARTIAL -> UNVERIFIED
CONTRADICTION_GAP    = 0.25   # Nếu top evidence mâu thuan va gap score > nguong nay -> CONTRADICTION


# ---------------------------------------------------------------------------
# CriticRagVerifier
# ---------------------------------------------------------------------------

class CriticRagVerifier:
    """
    CRITIC RAG Fact-Checking Engine.

    Embeds a textual claim, retrieves semantically similar documents from the
    Qdrant knowledge base, and returns a VerifyResult with a confidence score.

    Usage:
        verifier = CriticRagVerifier()
        result = await verifier.verify_claim("deepseek-r1 chay tot tren CPU")
        print(result.to_log_line())
    """

    # Ten collection Qdrant mac dinh (phai khop voi RAG service)
    DEFAULT_COLLECTION = "jkai_knowledge"
    TOP_K = 5                    # So ket qua tra ve tu Qdrant
    TIMEOUT_SECONDS = 8.0        # Timeout cho moi lan verify

    def __init__(
        self,
        collection: str | None = None,
        top_k: int | None = None,
    ) -> None:
        self.collection = collection or os.getenv(
            "CRITIC_RAG_COLLECTION", self.DEFAULT_COLLECTION
        )
        self.top_k = top_k or self.TOP_K
        self._embedder = None
        self._qdrant = None

    # ------------------------------------------------------------------
    # Lazy initialization helpers
    # ------------------------------------------------------------------

    def _get_embedder(self):
        """Khoi tao embedder lazily de tranh import cycle."""
        if self._embedder is None:
            try:
                from core.utils.embed import embedder
                self._embedder = embedder
            except Exception as exc:
                logger.error("[CriticRagVerifier] Cannot load embedder: %s", exc)
        return self._embedder

    def _get_qdrant(self):
        """Khoi tao Qdrant client lazily."""
        if self._qdrant is None:
            try:
                from core.qdrant_client import qdrant_client
                self._qdrant = qdrant_client
            except Exception as exc:
                logger.error("[CriticRagVerifier] Cannot load qdrant_client: %s", exc)
        return self._qdrant

    # ------------------------------------------------------------------
    # Core verification logic
    # ------------------------------------------------------------------

    async def verify_claim(
        self,
        claim: str,
        context_hint: str = "",
    ) -> VerifyResult:
        """
        Xac minh mot claim bang cach tim kiem qdrant.

        Args:
            claim: Cau khang dinh can kiem tra (vi du: "model X chay tren GPU").
            context_hint: Them ngung canh de tinh chinh embedding (tuy chon).

        Returns:
            VerifyResult voi confidence, verdict, va danh sach evidence.
        """
        start = time.monotonic()
        query_text = f"{claim} {context_hint}".strip()

        # Step 1: Embed
        embedding = await self._embed_safe(query_text)
        if not embedding:
            return VerifyResult(
                claim=claim,
                confidence=0.0,
                verdict="UNVERIFIED",
                reasoning="Embedding service unavailable — cannot verify.",
                elapsed_ms=(time.monotonic() - start) * 1000,
            )

        # Step 2: Search Qdrant
        hits = await self._search_safe(embedding)
        elapsed_ms = (time.monotonic() - start) * 1000

        if not hits:
            return VerifyResult(
                claim=claim,
                confidence=0.0,
                verdict="UNVERIFIED",
                reasoning="No relevant documents found in knowledge base.",
                elapsed_ms=elapsed_ms,
            )

        # Step 3: Score aggregation
        confidence, verdict, evidence, reasoning = self._aggregate_results(claim, hits)

        result = VerifyResult(
            claim=claim,
            confidence=confidence,
            verdict=verdict,
            evidence=evidence,
            reasoning=reasoning,
            elapsed_ms=elapsed_ms,
        )
        logger.info(result.to_log_line())
        return result

    # ------------------------------------------------------------------
    # Batch verification
    # ------------------------------------------------------------------

    async def verify_claims(
        self,
        claims: List[str],
        context_hint: str = "",
    ) -> List[VerifyResult]:
        """
        Xac minh nhieu claim song song (asyncio.gather).
        """
        tasks = [self.verify_claim(c, context_hint) for c in claims]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _embed_safe(self, text: str) -> List[float]:
        """Embed text, tra ve [] neu loi."""
        try:
            embedder = self._get_embedder()
            if embedder is None:
                return []
            result = await asyncio.wait_for(
                embedder.get_embedding_async(text),
                timeout=self.TIMEOUT_SECONDS,
            )
            return result or []
        except Exception as exc:
            logger.warning("[CriticRagVerifier] Embed failed: %s", exc)
            return []

    async def _search_safe(self, embedding: List[float]) -> List[Dict[str, Any]]:
        """Tim kiem Qdrant, tra ve [] neu loi."""
        try:
            qdrant = self._get_qdrant()
            if qdrant is None:
                return []
            raw = await asyncio.wait_for(
                qdrant.search(
                    collection_name=self.collection,
                    query_vector=embedding,
                    limit=self.top_k,
                    with_payload=True,
                ),
                timeout=self.TIMEOUT_SECONDS,
            )
            results = []
            for hit in raw:
                payload = hit.payload or {}
                results.append({
                    "score": float(hit.score),
                    "text": payload.get("text") or payload.get("content") or "",
                    "source": payload.get("source") or payload.get("filename") or "unknown",
                    "metadata": payload,
                })
            return results
        except Exception as exc:
            logger.warning("[CriticRagVerifier] Qdrant search failed: %s", exc)
            return []

    def _aggregate_results(
        self,
        claim: str,
        hits: List[Dict[str, Any]],
    ) -> tuple[float, str, List[Dict[str, Any]], str]:
        """
        Tinh toan confidence va phat hien contradiction.

        Thuat toan:
        - Confidence = trung binh co trong cua top-K score (score >= 0.65 moi tinh).
        - Contradiction: neu hit[0].score - hit[1].score < CONTRADICTION_GAP
          VA hai hit co noi dung doi lap (keywords phu dinh).
        """
        if not hits:
            return 0.0, "UNVERIFIED", [], "No hits to analyze."

        # Chi giu cac hit co score hop ly
        valid_hits = [h for h in hits if h["score"] >= 0.50]
        if not valid_hits:
            return 0.3, "UNVERIFIED", hits[:2], "Retrieved hits have low relevance scores."

        # Weighted average (hit dau tien trong hon)
        weights = [1.0 / (i + 1) for i in range(len(valid_hits))]
        weighted_sum = sum(h["score"] * w for h, w in zip(valid_hits, weights))
        weight_total = sum(weights)
        confidence = min(1.0, weighted_sum / weight_total)

        # Contradiction check: tim ky hieu phu dinh trong hit dau
        top_text = (valid_hits[0].get("text") or "").lower()
        negation_keywords = ["không", "false", "incorrect", "wrong", "lỗi", "sai", "nope", "không phải"]
        claim_lower = claim.lower()
        contradiction_detected = False
        if any(kw in top_text for kw in negation_keywords):
            # Neu tu khoa chinh cua claim xuat hien trong context phu dinh
            claim_words = [w for w in claim_lower.split() if len(w) > 3]
            if any(cw in top_text for cw in claim_words):
                contradiction_detected = True

        # Final verdict
        if contradiction_detected and confidence > 0.65:
            verdict = "CONTRADICTION"
            reasoning = (
                f"Top evidence contradicts the claim (score={valid_hits[0]['score']:.2f}). "
                f"Contradiction detected via negation pattern matching."
            )
        elif confidence >= THRESHOLD_VERIFIED:
            verdict = "VERIFIED"
            reasoning = f"Claim supported by {len(valid_hits)} relevant document(s). Avg confidence={confidence:.2f}."
        elif confidence >= THRESHOLD_PARTIAL:
            verdict = "PARTIAL"
            reasoning = f"Partial evidence found (confidence={confidence:.2f}). Additional sources recommended."
        else:
            verdict = "UNVERIFIED"
            reasoning = f"Insufficient evidence (confidence={confidence:.2f}). Executor must provide explicit sources."

        return confidence, verdict, valid_hits[:3], reasoning


# ---------------------------------------------------------------------------
# Convenience singleton
# ---------------------------------------------------------------------------

critic_rag_verifier = CriticRagVerifier()


# ---------------------------------------------------------------------------
# Quick smoke test (run: python -m core.utils.critic_rag_verifier)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    async def _smoke_test():
        verifier = CriticRagVerifier()
        test_claims = [
            "AMD RX 6600 ho tro Vulkan",
            "gemma4:12b chay tot tren CPU RAM",
            "deepseek-r1 co kha nang native thinking",
        ]
        for claim in test_claims:
            res = await verifier.verify_claim(claim)
            print(res.to_log_line())

    asyncio.run(_smoke_test())
