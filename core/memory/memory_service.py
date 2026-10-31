"""
Unified Memory Service Facade
File: core/memory/memory_service.py
Governed by Turn 469 Consensus:
- Coordinates SovereignHindsightStore, ObservationBuilder, and MemoryVerifier.
- Guarantees zero cross-bank leakage.
- Enforces strict token and offline execution limits.
"""

from typing import Dict, Any, List, Optional
from core.memory.memory_contracts import (
    MemoryBankScope, ProposalStatus, MemoryBudgetExceededError,
    EvidenceContract, ReflectVerdict,
    BUDGET_RECALL_FAST_TOKENS, BUDGET_REFLECT_EVIDENCE_RECORDS, BUDGET_REFLECT_OUTPUT_TOKENS
)
from core.memory.canonical_memory_schema import MemoryStatus, ProvenanceType
from core.memory.observation_builder import ObservationBuilder
from core.memory.memory_verifier import MemoryVerifier, DeterministicMemorySafetyGate
from core.memory.sovereign_hindsight_store import (
    SovereignHindsightStore, MemoryBankType
)


class MemoryService:
    """
    Facade over sovereign memory subsystems.
    Provides standard retain / recall / reflect API with strict governance.
    Governed by Turn 469, 471 & 473 Consensus.
    """
    def __init__(
        self,
        store: Optional[SovereignHindsightStore] = None,
        builder: Optional[ObservationBuilder] = None,
        execution_ledger: Optional[Any] = None,
        production_mode: bool = False
    ):
        self.store = store or SovereignHindsightStore()
        self.builder = builder or ObservationBuilder()
        self.verifier = DeterministicMemorySafetyGate()
        self.execution_ledger = execution_ledger
        self.production_mode = production_mode


    def retain_observation(
        self,
        bank: MemoryBankScope,
        claim: str,
        source_mission: str,
        evidence: Optional[Dict[str, Any]] = None,
        evidence_contract: Optional[EvidenceContract] = None,
        authorized_by_master: bool = False,
        production_mode: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Retains an observation via the proposal -> verification -> storage pipeline.
        Separates Master disposition authority (MASTER_AUTHORED) from empirical truth verification.
        """
        is_prod = self.production_mode if production_mode is None else production_mode

        proposal = self.builder.create_proposal(
            target_bank=bank,
            claim=claim,
            source_mission=source_mission,
            evidence_payload=evidence or {},
            evidence_contract=evidence_contract
        )

        approved, reason = self.verifier.verify_proposal(
            proposal,
            authorized_by_master=authorized_by_master,
            store=self.store,
            execution_ledger=self.execution_ledger,
            production_mode=is_prod
        )
        if not approved:
            proposal.status = ProposalStatus.REJECTED
            proposal.rejection_reason = reason
            return {
                "success": False,
                "proposal_id": proposal.id,
                "status": proposal.status.value,
                "reason": reason
            }

        # Set status & provenance: Master authority produces MASTER_AUTHORED, never empirically VERIFIED
        if bank == MemoryBankScope.VERIFIED_EXPERIENCE and evidence_contract:
            proposal.status = ProposalStatus.VERIFIED_EXPERIENCE
            provenance = ProvenanceType.VERIFIED
            confidence = 1.0
        elif bank == MemoryBankScope.MASTER_DISPOSITION and authorized_by_master:
            proposal.status = ProposalStatus.APPROVED_OBSERVATION
            provenance = ProvenanceType.MASTER_AUTHORED
            confidence = 1.0
        else:
            proposal.status = ProposalStatus.APPROVED_OBSERVATION
            provenance = ProvenanceType.RAW
            confidence = 0.8

        evidence_refs = evidence_contract.evidence_records if evidence_contract else []

        # Store in underlying sovereign store
        rec = self.store.retain(
            bank_id=bank.value,
            claim=claim,
            source=source_mission,
            provenance=provenance,
            confidence=confidence,
            evidence_refs=evidence_refs
        )

        # Append audit revision with full payload hash chaining
        rev = self.builder.append_revision(
            observation_id=rec.id,
            claim=claim,
            supporting_memory_ids=[rec.id],
            provenance=provenance.value
        )

        return {
            "success": True,
            "proposal_id": proposal.id,
            "memory_id": rec.id,
            "revision": rev.revision,
            "hash": rev.current_hash,
            "status": proposal.status.value,
            "provenance": provenance.value
        }

    def recall(
        self,
        bank: MemoryBankScope,
        query: str,
        top_k: int = 1,
        max_tokens: int = BUDGET_RECALL_FAST_TOKENS,
        allow_unverified: bool = True
    ) -> List[str]:
        """
        Fast recall primitive with hard token cap (<= 120 tokens default).
        """
        records = self.store.recall(
            bank_id=bank.value,
            query=query,
            top_k=top_k,
            token_budget=max_tokens,
            allow_unverified=allow_unverified
        )
        return [r.claim for r in records]

    def reflect(
        self,
        bank: MemoryBankScope,
        offline_mode: bool = False,
        verifier_actor: str = "OFFLINE_AUDITOR",
        topic: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reflect primitive. Strictly requires offline_mode=True.
        Returns operation_status, semantic ReflectVerdict (SUPPORTED | CONFLICTED | INSUFFICIENT_EVIDENCE),
        claims, evidence refs, and revision IDs.
        Enforces topic grounding, evidence records budget (<=6), and output budget (<=384 tokens).
        """
        if not offline_mode:
            raise PermissionError("BLOCKED_ONLINE_REFLECT: reflect() is only permitted during offline audit cycles.")

        # 1. Preflight budget & topic policy: use public scoped store API BEFORE materialization/store reflect
        active_count_fn = getattr(self.store, "count_scoped_records", None)
        if callable(active_count_fn):
            total_active = active_count_fn(bank.value)
        else:
            total_active = len(self.store.list_scoped_records(bank.value))

        if topic is None and total_active > BUDGET_REFLECT_EVIDENCE_RECORDS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Topic is required when bank contains more than {BUDGET_REFLECT_EVIDENCE_RECORDS} records."
            )

        target_records = self.store.list_scoped_records(bank.value, topic=topic)

        # Budget enforcement on reflect output and evidence BEFORE materialization
        claims = [r.claim for r in target_records]
        total_text = " ".join(claims)
        estimated_output_tokens = int(len(total_text.split()) * 1.3) + 1
        if estimated_output_tokens > BUDGET_REFLECT_OUTPUT_TOKENS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Reflect output tokens ({estimated_output_tokens}) exceeds budget ({BUDGET_REFLECT_OUTPUT_TOKENS})."
            )

        evidence_refs: List[str] = []
        for r in target_records:
            evidence_refs.extend(r.evidence_refs)
        unique_evidence_refs = sorted(list(set(evidence_refs)))

        if len(unique_evidence_refs) > BUDGET_REFLECT_EVIDENCE_RECORDS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Reflect evidence records count ({len(unique_evidence_refs)}) exceeds limit ({BUDGET_REFLECT_EVIDENCE_RECORDS})."
            )

        # 2. Execute offline store reflection after preflight budget pass
        try:
            store_result = self.store.reflect(bank_id=bank.value, verifier_actor=verifier_actor, target_records=target_records)
        except TypeError:
            store_result = self.store.reflect(bank_id=bank.value, verifier_actor=verifier_actor)

        # 3. Query conflicted records using public scoped store API
        conflicted_records = self.store.list_scoped_records(bank.value, status=MemoryStatus.CONFLICTED)


        # Grounded semantic verdict determination
        if conflicted_records:
            verdict = ReflectVerdict.CONFLICTED
        elif not target_records:
            verdict = ReflectVerdict.INSUFFICIENT_EVIDENCE
        else:
            # Check grounding for verified experience: must have evidence
            if bank == MemoryBankScope.VERIFIED_EXPERIENCE and not unique_evidence_refs:
                verdict = ReflectVerdict.INSUFFICIENT_EVIDENCE
            else:
                verdict = ReflectVerdict.SUPPORTED

        revision_ids: List[str] = []
        for r in target_records:
            revs = self.builder.get_revisions(r.id)
            revision_ids.extend([f"{rev.observation_id}_v{rev.revision}" for rev in revs])

        return {
            "operation_status": "SUCCEEDED",
            "status": "SUCCEEDED",
            "verdict": verdict.value,

            "bank_id": bank.value,
            "topic": topic,
            "audited_by": verifier_actor,
            "claims": claims,
            "evidence_refs": unique_evidence_refs,
            "revision_ids": sorted(list(set(revision_ids))),
            "metrics": store_result
        }


class ProductionMemoryService(MemoryService):
    """
    Production Memory Service Facade.
    Enforces strict production_mode=True default-deny boundary:
    - Mandatory typed ExecutionReceipt and VerificationVerdictContract
    - Mandatory execution ledger backing in bank_verified_experience
    - Rejection of free string verdicts and untyped dictionaries
    """
    def __init__(
        self,
        store: Optional[SovereignHindsightStore] = None,
        builder: Optional[ObservationBuilder] = None,
        execution_ledger: Optional[Any] = None,
        production_mode: bool = True
    ):
        super().__init__(
            store=store,
            builder=builder,
            execution_ledger=execution_ledger,
            production_mode=production_mode
        )



