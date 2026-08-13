"""
core/os/cognition/knowledge_fabric/source_strategy.py
Source Selection Strategy & EASG Gateway Binding.

Enforces:
- Source Priority != Source Truth (All retrieved evidence must pass EASG)
- Prioritizes authoritative sources by domain
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from core.os.cognition.knowledge_fabric.knowledge_need_planner import (
    KnowledgeDomain,
    KnowledgeNeed,
)
from core.os.cognition.easg.models import SourceTier


@dataclass
class SourceChannel:
    channel_name: str
    source_tier: SourceTier
    priority_rank: int               # 1 (Highest) to 5 (Lowest)
    description: str


class SourceSelectionStrategy:
    """Selects targeted retrieval channels and enforces EASG compliance."""

    def __init__(self):
        self._strategy_map: Dict[KnowledgeDomain, List[SourceChannel]] = {
            KnowledgeDomain.INTERNAL_REGULATION: [
                SourceChannel("internal_rag_authoritative", SourceTier.INTERNAL_ORGANIZATION_POLICY, 1, "Internal HR & Org Policies"),
                SourceChannel("tenant_local_drive", SourceTier.INTERNAL_PROJECT_DOC, 2, "Department Local Documents")
            ],
            KnowledgeDomain.INTERNAL_ACCOUNT: [
                SourceChannel("internal_vault_auth", SourceTier.INTERNAL_MASTER_DIRECTIVE, 1, "Sovereign Vault & Credentials")
            ],
            KnowledgeDomain.OFFICIAL_DOCS: [
                SourceChannel("official_vendor_docs", SourceTier.EXTERNAL_OFFICIAL_DOCS, 1, "Microsoft / Python / FastApi Official Documentation"),
                SourceChannel("github_official_repo", SourceTier.EXTERNAL_OFFICIAL_DOCS, 2, "Verified Upstream Source Repository")
            ],
            KnowledgeDomain.LEGAL_STATUTE: [
                SourceChannel("government_gazette_portal", SourceTier.EXTERNAL_OFFICIAL_DOCS, 1, "Official Legal Portal"),
                SourceChannel("ministry_circulars", SourceTier.EXTERNAL_OFFICIAL_DOCS, 2, "Ministry Official Circulars")
            ],
            KnowledgeDomain.TECHNICAL_BENCHMARK: [
                SourceChannel("official_release_notes", SourceTier.EXTERNAL_OFFICIAL_DOCS, 1, "Official Release Benchmarks"),
                SourceChannel("curated_technical_papers", SourceTier.EXTERNAL_ACADEMIC_PEER_REVIEWED, 2, "Curated Engineering Artifacts")
            ],
            KnowledgeDomain.COMMUNITY_DISCUSSION: [
                SourceChannel("community_forums", SourceTier.EXTERNAL_COMMUNITY_VERIFIED, 3, "StackOverflow / Discussions")
            ],
            KnowledgeDomain.BRAINSTORM_CREATIVE: [
                SourceChannel("internal_llm_cognition", SourceTier.LLM_SYNTHESIZED_TEXT, 4, "Pure Model Parametric Memory")
            ]
        }

    def select_channels(self, need: KnowledgeNeed) -> List[SourceChannel]:
        """Returns ordered source channels matching the specific knowledge need."""
        return self._strategy_map.get(need.target_domain, [
            SourceChannel("general_search_engine", SourceTier.EXTERNAL_COMMUNITY_VERIFIED, 3, "General Web Search")
        ])


source_selection_strategy = SourceSelectionStrategy()
