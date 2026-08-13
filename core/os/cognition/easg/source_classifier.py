"""
core/os/cognition/easg/source_classifier.py
EASG — Source Classifier & Provenance Inspector.

Classifies information sources into authoritative tiers and prevents LLM self-generated text
from masquerading as external or internal evidence.
"""

from __future__ import annotations
import re
from typing import Dict, Optional, Tuple
from core.os.cognition.easg.models import CandidateEvidence, SourceTier


TIER_AUTHORITY_WEIGHTS: Dict[SourceTier, float] = {
    SourceTier.INTERNAL_MASTER_DIRECTIVE: 1.00,
    SourceTier.INTERNAL_ORGANIZATION_POLICY: 0.95,
    SourceTier.INTERNAL_PROJECT_DOC: 0.85,
    SourceTier.EXTERNAL_OFFICIAL_DOCS: 0.90,
    SourceTier.EXTERNAL_ACADEMIC_PEER_REVIEWED: 0.85,
    SourceTier.EXTERNAL_VENDOR_KB: 0.80,
    SourceTier.EXTERNAL_COMMUNITY_VERIFIED: 0.60,
    SourceTier.EXTERNAL_UNTRUSTED_BLOG: 0.20,
    SourceTier.LLM_SYNTHESIZED_TEXT: 0.00,
}


class SourceClassifier:
    """Classifies sources and evaluates their innate authority."""

    def classify_source(
        self,
        source_uri: str,
        content: str = "",
        provenance_hint: Optional[str] = None,
    ) -> Tuple[SourceTier, float]:
        uri_low = source_uri.lower()
        hint_low = (provenance_hint or "").lower()

        # 1. Master Directives
        if "master" in hint_low or "user_prompt" in uri_low or "directive" in uri_low:
            return SourceTier.INTERNAL_MASTER_DIRECTIVE, TIER_AUTHORITY_WEIGHTS[SourceTier.INTERNAL_MASTER_DIRECTIVE]

        # 2. Internal Organization Policy / Local Official Files
        if any(k in uri_low for k in ["quy_che", "chinh_sach", "policy", "internal", "hueic", "quy_dinh"]):
            return SourceTier.INTERNAL_ORGANIZATION_POLICY, TIER_AUTHORITY_WEIGHTS[SourceTier.INTERNAL_ORGANIZATION_POLICY]

        if uri_low.startswith("file://") or uri_low.startswith("d:/") or uri_low.startswith("c:/"):
            return SourceTier.INTERNAL_PROJECT_DOC, TIER_AUTHORITY_WEIGHTS[SourceTier.INTERNAL_PROJECT_DOC]

        # 3. LLM Generated / Synthetic Text Detection
        if any(k in uri_low or k in hint_low for k in ["chatgpt", "llm", "synthetic", "ai_generated", "assistant"]):
            return SourceTier.LLM_SYNTHESIZED_TEXT, TIER_AUTHORITY_WEIGHTS[SourceTier.LLM_SYNTHESIZED_TEXT]

        # 4. External Official Documentation
        if any(dom in uri_low for dom in ["docs.", "documentation", "mikrotik.com/wiki", "microsoft.com/docs", "python.org", "ietf.org", "rfc-editor"]):
            return SourceTier.EXTERNAL_OFFICIAL_DOCS, TIER_AUTHORITY_WEIGHTS[SourceTier.EXTERNAL_OFFICIAL_DOCS]

        # 5. External Academic / Papers
        if any(dom in uri_low for dom in ["arxiv.org", "ieee.org", "acm.org", "nature.com", "springer.com"]):
            return SourceTier.EXTERNAL_ACADEMIC_PEER_REVIEWED, TIER_AUTHORITY_WEIGHTS[SourceTier.EXTERNAL_ACADEMIC_PEER_REVIEWED]

        # 6. Community Verified (StackOverflow, ServerFault)
        if any(dom in uri_low for dom in ["stackoverflow.com", "serverfault.com", "github.com/issues"]):
            return SourceTier.EXTERNAL_COMMUNITY_VERIFIED, TIER_AUTHORITY_WEIGHTS[SourceTier.EXTERNAL_COMMUNITY_VERIFIED]

        # 7. Untrusted Blog / Social Forums
        if any(dom in uri_low for dom in ["reddit.com", "quora.com", "medium.com", "blogspot.com", "wordpress.com", "blog"]):
            return SourceTier.EXTERNAL_UNTRUSTED_BLOG, TIER_AUTHORITY_WEIGHTS[SourceTier.EXTERNAL_UNTRUSTED_BLOG]

        # Default fallback
        return SourceTier.EXTERNAL_COMMUNITY_VERIFIED, 0.50


source_classifier = SourceClassifier()
