"""
core/os/cognition/easg/provenance_engine.py
EASG — Provenance Engine & Anti-Evidence-Laundering Guardian (D13/D20).

Prevents Echo-Chamber Inflation:
If Agent A, Agent B, and Agent C all cite the same underlying Blog A,
they are collapsed into independence_cluster = 1.
"""

from __future__ import annotations
import hashlib
from typing import Dict, List, Set, Tuple
from core.os.cognition.easg.models import CandidateEvidence, LineageRecord, SourceTier


class ProvenanceEngine:
    """Tracks root provenance and enforces epistemic independence clustering."""

    def __init__(self):
        self._clusters: Dict[str, Set[str]] = {} # cluster_id -> set of candidate_ids

    def register_and_cluster(self, candidate: CandidateEvidence) -> Tuple[LineageRecord, str]:
        lineage = candidate.get_lineage()
        cluster_id = lineage.compute_cluster_id()

        # Check for Evidence Laundering: LLM or Agent claiming unverified source as internal policy
        if candidate.source_tier == SourceTier.INTERNAL_ORGANIZATION_POLICY:
            if any("blog" in step.lower() or "reddit" in step.lower() for step in lineage.derivation_chain):
                lineage.is_laundered = True
                # Downgrade source tier to untrusted blog
                candidate.source_tier = SourceTier.EXTERNAL_UNTRUSTED_BLOG

        if cluster_id not in self._clusters:
            self._clusters[cluster_id] = set()
        self._clusters[cluster_id].add(candidate.candidate_id)

        return lineage, cluster_id

    def get_cluster_count(self) -> int:
        return len(self._clusters)

    def get_independent_clusters_for_candidates(self, candidate_ids: List[str], candidates_map: Dict[str, CandidateEvidence]) -> int:
        seen_clusters: Set[str] = set()
        for cid in candidate_ids:
            cand = candidates_map.get(cid)
            if cand:
                seen_clusters.add(cand.get_lineage().root_cluster_id)
        return len(seen_clusters)


provenance_engine = ProvenanceEngine()
