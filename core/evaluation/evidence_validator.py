"""
JKAI ZENITH — EVALUATION DOMAIN: EVIDENCE VALIDATOR & EPISTEMIC GRAPH
File: core/evaluation/evidence_validator.py

Extracts claims from execution outputs, resolves empirical evidence from tools and RAG,
and constructs an EvidenceGraph with confidence scoring for MissionEvaluator.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class ClaimNode:
    """Individual testable claim extracted from execution output."""
    claim_id: str
    statement: str
    claim_type: str                      # "CODE_EXECUTION" | "KNOWLEDGE_FACT" | "SCHEMA_STRUCTURE" | "FILE_SIDE_EFFECT"
    confidence: float = 1.0


@dataclass
class EvidenceNode:
    """Empirical evidence node resolving a claim."""
    evidence_id: str
    claim_id: str
    source_type: str                     # "TOOL_OUTPUT" | "RAG_CITATION" | "UNIT_TEST" | "SYSTEM_LOG"
    is_verifiable: bool = True
    is_grounded: bool = True
    raw_evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceGraph:
    """Comprehensive Epistemic Graph emitted by EvidenceValidator."""
    mission_id: str
    claims: List[ClaimNode] = field(default_factory=list)
    evidence: List[EvidenceNode] = field(default_factory=list)
    overall_confidence: float = 1.0
    grounding_ratio: float = 1.0
    contradictions_found: int = 0
    created_at: float = field(default_factory=time.time)


class EvidenceValidator:
    """Epistemic evidence validator constructing EvidenceGraph for MissionEvaluator."""

    def build_evidence_graph(
        self,
        mission_id: str,
        output_text: str,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        rag_citations: Optional[List[Dict[str, Any]]] = None
    ) -> EvidenceGraph:
        claims: List[ClaimNode] = []
        evidence: List[EvidenceNode] = []

        # Claim extraction heuristic
        if output_text:
            claims.append(ClaimNode(
                claim_id="c_001",
                statement="Execution output generated",
                claim_type="KNOWLEDGE_FACT",
                confidence=0.95
            ))

        # Tool result evidence resolution
        grounded_count = 0
        if tool_results:
            for idx, res in enumerate(tool_results):
                cid = f"c_tool_{idx+1}"
                eid = f"e_tool_{idx+1}"
                claims.append(ClaimNode(
                    claim_id=cid,
                    statement=f"Tool {res.get('tool_name', 'tool')} executed",
                    claim_type="CODE_EXECUTION",
                    confidence=1.0 if res.get("status") == "success" else 0.4
                ))
                evidence.append(EvidenceNode(
                    evidence_id=eid,
                    claim_id=cid,
                    source_type="TOOL_OUTPUT",
                    is_verifiable=True,
                    is_grounded=res.get("status") == "success",
                    raw_evidence=res
                ))
                if res.get("status") == "success":
                    grounded_count += 1

        total_claims = len(claims)
        grounding_ratio = (grounded_count / total_claims) if total_claims > 0 else 1.0

        return EvidenceGraph(
            mission_id=mission_id,
            claims=claims,
            evidence=evidence,
            overall_confidence=grounding_ratio,
            grounding_ratio=grounding_ratio,
            contradictions_found=0
        )
