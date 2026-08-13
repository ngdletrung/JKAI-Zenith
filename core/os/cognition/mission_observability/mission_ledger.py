"""
core/os/cognition/mission_observability/mission_ledger.py
Mission Observability Ledger — The 10-Question Single Source of Epistemic & Execution Truth.

Enforces complete causal traceability across the 10 Backstage Layers:
Mission -> CanonicalGoal -> Requirements -> KnowledgeNeeds -> Sources -> Evidence -> Beliefs -> Capabilities -> Plan -> Prompt -> Model -> ToolCall -> ExecutionTruth -> Artifact -> Verification -> Proof.
"""

from __future__ import annotations
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from core.os.cognition.adaptive_solver.models import ExecutionTruth, StrategyAdaptation
from core.os.cognition.capability_fabric.models import CapabilitySpec
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec, SuccessCriterion
from core.os.cognition.knowledge_fabric.knowledge_need_planner import KnowledgeNeed


@dataclass
class MissionAuditRecord:
    """The complete 10-question audit record for a mission."""
    mission_id: str
    q1_master_intent: str
    q2_requirements: List[Dict[str, Any]]
    q3_knowledge_need: Optional[Dict[str, Any]] = None
    q4_authorized_sources: List[str] = field(default_factory=list)
    q5_admitted_evidence: List[Dict[str, Any]] = field(default_factory=list)
    q6_available_capabilities: List[str] = field(default_factory=list)
    q7_capability_mappings: Dict[str, str] = field(default_factory=dict) # req_id -> capability_id
    q8_tool_invocations: List[Dict[str, Any]] = field(default_factory=list)
    q9_execution_truths: List[Dict[str, Any]] = field(default_factory=list)
    q10_is_proven_completed: bool = False
    q10_proof_details: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class MissionObservabilityLedger:
    """Stores and audits full cognitive-execution traces for all JKAI missions."""

    def __init__(self):
        self._records: Dict[str, MissionAuditRecord] = {}

    def create_record(self, mission: CanonicalMissionSpec) -> MissionAuditRecord:
        reqs = [{"id": sc.criterion_id, "desc": sc.description, "target": sc.target_attribute, "expected": str(sc.expected_value)} for sc in mission.success_criteria]
        rec = MissionAuditRecord(
            mission_id=mission.mission_id,
            q1_master_intent=mission.raw_goal,
            q2_requirements=reqs
        )
        self._records[mission.mission_id] = rec
        return rec

    def record_knowledge_planning(self, mission_id: str, need: KnowledgeNeed, sources: List[str]):
        if mission_id in self._records:
            rec = self._records[mission_id]
            rec.q3_knowledge_need = {
                "domain": need.target_domain.value,
                "topics": need.required_topics,
                "prohibited": need.prohibited_noise
            }
            rec.q4_authorized_sources = sources

    def record_capabilities(self, mission_id: str, caps: List[CapabilitySpec], mappings: Dict[str, str]):
        if mission_id in self._records:
            rec = self._records[mission_id]
            rec.q6_available_capabilities = [c.capability_id for c in caps]
            rec.q7_capability_mappings = mappings

    def record_execution_truth(self, mission_id: str, truth: ExecutionTruth):
        if mission_id in self._records:
            rec = self._records[mission_id]
            rec.q8_tool_invocations.append({
                "invocation_id": truth.invocation_id,
                "tool": truth.tool_name,
                "args": truth.arguments,
                "time_ms": truth.execution_time_ms
            })
            rec.q9_execution_truths.append({
                "invocation_id": truth.invocation_id,
                "tool_outcome": truth.tool_outcome.value,
                "artifact_outcome": truth.artifact_outcome.value,
                "artifact_path": truth.artifact_path,
                "requirement_verdicts": {k: v.value for k, v in truth.requirement_verdicts.items()},
                "is_genuine_success": truth.is_genuine_success,
                "diagnostic": truth.diagnostic_details
            })

    def finalize_record(self, mission_id: str, is_proven: bool, proof_details: str):
        if mission_id in self._records:
            rec = self._records[mission_id]
            rec.q10_is_proven_completed = is_proven
            rec.q10_proof_details = proof_details
            rec.completed_at = time.time()

    def get_record(self, mission_id: str) -> Optional[MissionAuditRecord]:
        return self._records.get(mission_id)

    def export_audit_json(self, mission_id: str) -> str:
        rec = self.get_record(mission_id)
        if not rec:
            return "{}"
        return json.dumps(asdict(rec), ensure_ascii=False, indent=2)


mission_ledger = MissionObservabilityLedger()
