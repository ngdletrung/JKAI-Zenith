"""
Deterministic Memory Safety Gate (formerly MemoryVerifier)
File: core/memory/memory_verifier.py
Enforces Turn 469 & Turn 471 Rules:
- Accurately named DeterministicMemorySafetyGate (no inflated claim of semantic verifier).
- Master Authority Gate: authorizes mutation/disposition, does NOT grant empirical truth.
- Mandatory Evidence Contract for VERIFIED_EXPERIENCE (receipt + verdict + trace_id).
- Secret/PII and Prompt Injection scan.
- Cross-bank evidence reference blocking.
"""

import re
from typing import Tuple, Optional
from core.memory.memory_contracts import ObservationProposal, MemoryBankScope, ProposalStatus, ExecutionReceipt


# Expanded deterministic secret/PII patterns (API keys, JWT, AWS, private keys)
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|bearer\s+[a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*"),  # JWT pattern
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE),
]

# Prompt injection markers
INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"(?i)system\s*:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"(?i)bypass\s+governance", re.IGNORECASE),
]


class DeterministicMemorySafetyGate:
    """
    Deterministic gatekeeper verifying observation proposals.
    Named accurately to reflect its role as a safety gate, not a semantic judge.
    """
    @staticmethod
    def verify_proposal(
        proposal: ObservationProposal,
        authorized_by_master: bool = False,
        store: Optional[Any] = None,
        execution_ledger: Optional[Any] = None,
        production_mode: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Runs comprehensive deterministic verification on a candidate observation proposal.
        Returns (is_approved: bool, rejection_reason: Optional[str]).
        """
        # 1. Authority Gate: Master disposition protection
        if proposal.target_bank == MemoryBankScope.MASTER_DISPOSITION and not authorized_by_master:
            return False, "AUTHORITY_VIOLATION: Cannot modify bank_master_disposition without explicit Master authority."

        # 2. Source mission mandatory check
        if not proposal.source_mission or not proposal.source_mission.strip():
            return False, "EVIDENCE_VIOLATION: source_mission cannot be empty."

        # 3. Mandatory Evidence Contract for VERIFIED_EXPERIENCE
        if proposal.target_bank == MemoryBankScope.VERIFIED_EXPERIENCE:
            if not proposal.evidence_contract:
                return False, "EVIDENCE_CONTRACT_REQUIRED: bank_verified_experience requires an EvidenceContract (receipt + verdict)."
            try:
                proposal.evidence_contract.validate_bounds(production_mode=production_mode)
            except Exception as e:
                return False, f"EVIDENCE_CONTRACT_INVALID: {e}"

            # Check execution receipt in execution ledger
            rec = proposal.evidence_contract.execution_receipt
            rec_id = getattr(rec, "id", None) or (rec.get("id") if isinstance(rec, dict) else None)
            
            if production_mode and execution_ledger is None:
                return False, "EXECUTION_LEDGER_MANDATORY: bank_verified_experience requires a valid execution_ledger in production mode."

            if execution_ledger is not None:
                ledger_rec = None
                if hasattr(execution_ledger, "get_receipt"):
                    ledger_rec = execution_ledger.get_receipt(rec_id)
                elif hasattr(execution_ledger, "get"):
                    ledger_rec = execution_ledger.get(rec_id)
                elif isinstance(execution_ledger, dict):
                    ledger_rec = execution_ledger.get(rec_id)
                elif isinstance(execution_ledger, (set, list, tuple)):
                    if rec_id in execution_ledger:
                        ledger_rec = rec  # Identity membership fallback

                if not ledger_rec:
                    return False, f"EXECUTION_RECEIPT_NOT_FOUND: Execution receipt '{rec_id}' not found in execution ledger."

                # Verify payload match against resolved ledger record
                if isinstance(ledger_rec, (ExecutionReceipt, dict)):
                    led_trace = getattr(ledger_rec, "trace_id", None) or (ledger_rec.get("trace_id") if isinstance(ledger_rec, dict) else None)
                    led_mission = getattr(ledger_rec, "mission_id", None) or (ledger_rec.get("mission_id") if isinstance(ledger_rec, dict) else None)
                    led_exit = getattr(ledger_rec, "exit_code", None) if hasattr(ledger_rec, "exit_code") else (ledger_rec.get("exit_code") if isinstance(ledger_rec, dict) else None)
                    led_hash = getattr(ledger_rec, "artifact_hash", None) or (ledger_rec.get("artifact_hash") if isinstance(ledger_rec, dict) else None)

                    rec_trace = getattr(rec, "trace_id", None) or (rec.get("trace_id") if isinstance(rec, dict) else None)
                    rec_mission = getattr(rec, "mission_id", None) or (rec.get("mission_id") if isinstance(rec, dict) else None)
                    rec_exit = getattr(rec, "exit_code", None) if hasattr(rec, "exit_code") else (rec.get("exit_code") if isinstance(rec, dict) else None)
                    rec_hash = getattr(rec, "artifact_hash", None) or (rec.get("artifact_hash") if isinstance(rec, dict) else None)

                    if led_trace != rec_trace:
                        return False, f"EXECUTION_RECEIPT_MISMATCH: trace_id mismatch between proposal ('{rec_trace}') and ledger ('{led_trace}')."
                    if led_mission != rec_mission:
                        return False, f"EXECUTION_RECEIPT_MISMATCH: mission_id mismatch between proposal ('{rec_mission}') and ledger ('{led_mission}')."
                    if led_exit != rec_exit:
                        return False, f"EXECUTION_RECEIPT_MISMATCH: exit_code mismatch between proposal ({rec_exit}) and ledger ({led_exit})."
                    if led_hash and rec_hash and led_hash != rec_hash:
                        return False, f"EXECUTION_RECEIPT_MISMATCH: artifact_hash mismatch between proposal ('{rec_hash}') and ledger ('{led_hash}')."
                    if led_hash and not rec_hash:
                        return False, f"EXECUTION_RECEIPT_MISMATCH: artifact_hash missing in proposal receipt."

            # Check cross-bank evidence leakage and existence via public store API
            for rec_id_ref in proposal.evidence_contract.evidence_records:
                if "disposition" in rec_id_ref.lower():
                    return False, "CROSS_BANK_LEAKAGE: bank_verified_experience cannot reference master disposition as evidence."

                if store is not None:
                    # Public API resolution
                    resolved = store.resolve_evidence(proposal.target_bank.value, rec_id_ref)
                    if not resolved:
                        # Check whether it exists in any other known bank
                        leakage_bank = None
                        for other_scope in MemoryBankScope:
                            if other_scope != proposal.target_bank:
                                if store.resolve_evidence(other_scope.value, rec_id_ref):
                                    leakage_bank = other_scope.value
                                    break
                        if leakage_bank:
                            return False, f"CROSS_BANK_LEAKAGE: Evidence record '{rec_id_ref}' belongs to '{leakage_bank}', not '{proposal.target_bank.value}'."
                        return False, f"EVIDENCE_RECORD_NOT_FOUND: Evidence record '{rec_id_ref}' does not exist in store."

        # 4. Secret / PII Scan
        for pattern in SECRET_PATTERNS:
            if pattern.search(proposal.claim):
                return False, "SECURITY_VIOLATION: Secret or PII pattern detected in claim."

        # 5. Prompt Injection Defense
        for pattern in INJECTION_PATTERNS:
            if pattern.search(proposal.claim):
                return False, "SECURITY_VIOLATION: Potential prompt injection pattern detected."

        # 6. Empty / malformed claim check
        if not proposal.claim or len(proposal.claim.strip()) < 3:
            return False, "MALFORMED_CLAIM: Claim is empty or too short."

        return True, None



# Backward-compatible alias
MemoryVerifier = DeterministicMemorySafetyGate
