"""
JKAI Memory Contracts & Invariant Budgets
File: core/memory/memory_contracts.py
Governed by Master LeeTrung OS Architecture & Two-Agent Consensus Turn 469 & Turn 471.

Strict Deterministic Budgets (SLM 3B Envelope):
- retain input budget: 512 tokens (total serialized proposal input)
- retain output budget: 256 tokens (claim)
- recall fast path: <= 120 tokens
- reflect evidence: <= 6 records
- reflect output: <= 384 tokens
- max entities per event: 32
- max relations per event: 64
"""

import json
import hashlib
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class MemoryBankScope(str, Enum):
    MASTER_DISPOSITION = "bank_master_disposition"    # Policy, preferences, highest authority
    SYSTEM_WORLD = "bank_system_world"                # Facts, file trees, ports, tools
    VERIFIED_EXPERIENCE = "bank_verified_experience"  # Proven execution lessons with receipts


class ProposalStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    REJECTED = "REJECTED"
    APPROVED_OBSERVATION = "APPROVED_OBSERVATION"
    VERIFIED_EXPERIENCE = "VERIFIED_EXPERIENCE"
    PROMOTED_RULE = "PROMOTED_RULE"


class ReflectVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# Invariant token and capacity limits
BUDGET_RETAIN_INPUT_TOKENS = 512
BUDGET_RETAIN_OUTPUT_TOKENS = 256
BUDGET_RECALL_FAST_TOKENS = 120
BUDGET_REFLECT_EVIDENCE_RECORDS = 6
BUDGET_REFLECT_OUTPUT_TOKENS = 384
MAX_ENTITIES_PER_EVENT = 32
MAX_RELATIONS_PER_EVENT = 64


class MemoryBudgetExceededError(ValueError):
    """Raised when an operation attempts to exceed the strict SLM 3B token/record budget."""
    pass


class MemoryEntityLimitExceededError(ValueError):
    """Raised when an event exceeds the max entity count (32)."""
    pass


class MemoryRelationLimitExceededError(ValueError):
    """Raised when an event exceeds the max relation count (64)."""
    pass


class MemoryLedgerIntegrityError(ValueError):
    """Raised when the persistent observation ledger suffers from corruption, gap, or hash mismatch."""
    pass


@dataclass
class ExecutionReceipt:
    """Typed execution proof receipt."""
    id: str
    trace_id: str
    mission_id: str
    exit_code: int = 0
    output: str = ""
    timestamp: str = ""
    artifact_hash: str = ""


@dataclass
class VerificationVerdictContract:
    """Typed verification verdict emitted by authorized verifier."""
    status: str = "COMPLETE"
    mission_id: str = ""
    receipt_refs: List[str] = field(default_factory=list)
    verdict_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceContract:
    """
    Mandatory proof contract for verified experience.
    Prevents hallucinated / groundless memory retention.
    Governed by Turn 471 & Turn 473 Consensus.
    """
    source_mission: str
    trace_id: str
    execution_receipt: Any
    verification_verdict: Any
    evidence_records: List[str] = field(default_factory=list)
    evidence_memory_ids: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if self.evidence_records and self.evidence_memory_ids:
            if set(self.evidence_records) != set(self.evidence_memory_ids):
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Conflicting evidence namespace: evidence_records and evidence_memory_ids contain different values.")
        elif not self.evidence_records and self.evidence_memory_ids:
            self.evidence_records = list(self.evidence_memory_ids)
        elif not self.evidence_memory_ids and self.evidence_records:
            self.evidence_memory_ids = list(self.evidence_records)

    def validate_bounds(self, production_mode: bool = False):
        if not self.source_mission or not self.source_mission.strip():
            raise ValueError("BLOCKED_MEMORY_EVIDENCE: source_mission cannot be empty.")
        if not self.trace_id or not self.trace_id.strip():
            raise ValueError("BLOCKED_MEMORY_EVIDENCE: trace_id cannot be empty.")
        if not self.execution_receipt:
            raise ValueError("BLOCKED_MEMORY_EVIDENCE: execution_receipt is required.")
        if not self.verification_verdict:
            raise ValueError("BLOCKED_MEMORY_EVIDENCE: verification_verdict is required.")

        # Validate typed receipt or dict receipt
        rec = self.execution_receipt
        rec_trace = getattr(rec, "trace_id", None) if hasattr(rec, "trace_id") else (rec.get("trace_id") if isinstance(rec, dict) else None)
        rec_mission = getattr(rec, "mission_id", None) if hasattr(rec, "mission_id") else (rec.get("mission_id") if isinstance(rec, dict) else None)
        rec_exit = getattr(rec, "exit_code", None) if hasattr(rec, "exit_code") else (rec.get("exit_code") if isinstance(rec, dict) else None)
        rec_id = getattr(rec, "id", None) if hasattr(rec, "id") else (rec.get("id") if isinstance(rec, dict) else None)

        if rec_id is not None and not str(rec_id).strip():
            raise ValueError("BLOCKED_MEMORY_EVIDENCE: Receipt id cannot be empty.")

        if production_mode:
            if not isinstance(rec, ExecutionReceipt):
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Production mode requires typed ExecutionReceipt.")
            if not rec_id or not str(rec_id).strip():
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Receipt id cannot be empty in production.")
            if not rec_trace or not str(rec_trace).strip():
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Receipt trace_id cannot be empty in production.")
            if not rec_mission or not str(rec_mission).strip():
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Receipt mission_id cannot be empty in production.")

        if rec_trace and rec_trace != self.trace_id:
            raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Receipt trace_id '{rec_trace}' does not match contract trace_id '{self.trace_id}'.")
        if rec_mission and rec_mission != self.source_mission:
            raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Receipt mission_id '{rec_mission}' does not match contract source_mission '{self.source_mission}'.")
        if rec_exit is not None and rec_exit != 0:
            raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Receipt exit_code must be 0 for verified experience, got {rec_exit}.")

        # Validate typed verdict or dict verdict
        verd = self.verification_verdict
        if isinstance(verd, str):
            if production_mode:
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: String verdict rejected in production; requires typed VerificationVerdictContract.")
            if verd not in ["PASS", "COMPLETE"]:
                raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Invalid string verdict '{verd}'.")
        elif isinstance(verd, (VerificationVerdictContract, dict)):
            if production_mode and not isinstance(verd, VerificationVerdictContract):
                raise ValueError("BLOCKED_MEMORY_EVIDENCE: Production mode requires typed VerificationVerdictContract.")
            verd_status = getattr(verd, "status", None) or (verd.get("status") if isinstance(verd, dict) else None)
            verd_mission = getattr(verd, "mission_id", None) or (verd.get("mission_id") if isinstance(verd, dict) else None)
            verd_refs = getattr(verd, "receipt_refs", None) or (verd.get("receipt_refs") if isinstance(verd, dict) else [])

            if production_mode:
                if not verd_mission or not str(verd_mission).strip():
                    raise ValueError("BLOCKED_MEMORY_EVIDENCE: Verdict mission_id cannot be empty in production.")
                if not verd_refs:
                    raise ValueError("BLOCKED_MEMORY_EVIDENCE: Verdict receipt_refs cannot be empty in production.")

            if verd_status not in ["COMPLETE", "PASS"]:
                raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Verdict status must be 'COMPLETE' or 'PASS', got '{verd_status}'.")
            if verd_mission and verd_mission != self.source_mission:
                raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Verdict mission_id '{verd_mission}' does not match source_mission '{self.source_mission}'.")
            if rec_id and verd_refs and rec_id not in verd_refs:
                raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Verdict receipt_refs does not contain receipt ID '{rec_id}'.")
        else:
            raise ValueError(f"BLOCKED_MEMORY_EVIDENCE: Unsupported verification verdict type '{type(verd)}'.")


        if len(self.entities) > MAX_ENTITIES_PER_EVENT:
            raise MemoryEntityLimitExceededError(
                f"BLOCKED_MEMORY_ENTITY_LIMIT: Entities count ({len(self.entities)}) exceeds max {MAX_ENTITIES_PER_EVENT}."
            )
        if len(self.relations) > MAX_RELATIONS_PER_EVENT:
            raise MemoryRelationLimitExceededError(
                f"BLOCKED_MEMORY_RELATION_LIMIT: Relations count ({len(self.relations)}) exceeds max {MAX_RELATIONS_PER_EVENT}."
            )



@dataclass
class ObservationRevision:
    """
    Append-only revision for an observation.
    Guarantees zero in-place overwrites and complete audit provenance.
    Computes hash covering the entire payload.
    """
    observation_id: str
    revision: int
    claim: str
    supporting_memory_ids: List[str] = field(default_factory=list)
    contradicting_memory_ids: List[str] = field(default_factory=list)
    provenance: str = "RAW"
    previous_hash: str = ""
    current_hash: str = ""
    valid_from: str = ""
    valid_to: Optional[str] = None

    def compute_hash(self) -> str:
        payload_dict = {
            "observation_id": self.observation_id,
            "revision": self.revision,
            "claim": self.claim,
            "supporting_memory_ids": sorted(self.supporting_memory_ids),
            "contradicting_memory_ids": sorted(self.contradicting_memory_ids),
            "provenance": self.provenance,
            "previous_hash": self.previous_hash,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }
        canonical_json = json.dumps(payload_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]


@dataclass
class ObservationProposal:
    """
    Candidate observation proposed by SLM / runtime.
    Model CANNOT directly write to VERIFIED status.
    """
    id: str
    target_bank: MemoryBankScope
    claim: str
    source_mission: str
    evidence_payload: Dict[str, Any]
    evidence_contract: Optional[EvidenceContract] = None
    status: ProposalStatus = ProposalStatus.CANDIDATE
    rejection_reason: Optional[str] = None
    created_at: str = ""
