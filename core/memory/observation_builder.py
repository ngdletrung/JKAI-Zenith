"""
Observation Builder & Append-Only Revision Manager
File: core/memory/observation_builder.py
Enforces Turn 469 & 471 mandates:
- Append-only revision chaining with full payload SHA-256 hash.
- Persistence across restarts via persistent JSON lines ledger.
- Strict input token budget (512 tokens) and output token budget (256 tokens).
"""

import os
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.memory.memory_contracts import (
    ObservationProposal, ObservationRevision, EvidenceContract,
    MemoryBankScope, ProposalStatus,
    BUDGET_RETAIN_INPUT_TOKENS, BUDGET_RETAIN_OUTPUT_TOKENS,
    BUDGET_REFLECT_EVIDENCE_RECORDS,
    MemoryBudgetExceededError, MemoryLedgerIntegrityError
)


def estimate_tokens(text: str) -> int:
    """Fast deterministic token estimator for English/Vietnamese UTF-8."""
    words = (text or "").strip().split()
    return int(len(words) * 1.3) + 1


import threading
import contextlib

LEDGER_DIR = Path("data/memory_ledger")
DEFAULT_LEDGER_FILE = LEDGER_DIR / "observation_revisions.jsonl"
_APPEND_LOCK = threading.RLock()


@contextlib.contextmanager
def _os_process_lock(lock_path: Path):
    """
    Acquires an exclusive OS-level file lock.
    Supports Windows (msvcrt.locking) and POSIX (fcntl.flock).
    Guarantees cross-process serialization for persistent ledger writes.
    """
    lock_file = lock_path.with_suffix(lock_path.suffix + ".lock")
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    has_msvcrt = False
    try:
        import msvcrt
        has_msvcrt = True
    except ImportError:
        pass

    has_fcntl = False
    try:
        import fcntl
        has_fcntl = True
    except ImportError:
        pass

    fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o666)
    start_t = time.time()
    try:
        while True:
            if has_msvcrt:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except (BlockingIOError, OSError):
                    if time.time() - start_t > 15.0:
                        raise TimeoutError(f"Could not acquire ledger lock on {lock_file} after 15s")
                    time.sleep(0.01)
            elif has_fcntl:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (BlockingIOError, OSError):
                    if time.time() - start_t > 15.0:
                        raise TimeoutError(f"Could not acquire ledger lock on {lock_file} after 15s")
                    time.sleep(0.01)
            else:
                raise RuntimeError("PROCESS_LOCK_UNSUPPORTED: System lacks msvcrt and fcntl; fail closed on cross-process lock.")
        yield
    finally:
        try:
            if has_msvcrt:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            elif has_fcntl:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass


class ObservationBuilder:
    """
    Constructs and versions observation proposals.
    Guarantees that revisions are strictly chained with cryptographic hashes,
    persisted durably, synchronized across concurrent threads/writers,
    and fails closed upon any ledger integrity error.
    """
    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file or DEFAULT_LEDGER_FILE
        self.revisions_history: Dict[str, List[ObservationRevision]] = {}
        self._load_ledger()

    def _load_ledger(self):
        """
        Loads and verifies existing revisions from persistent ledger on startup.
        Strictly fails closed on corrupted JSON, hash tampering, revision gaps, or broken chains.
        If a trailing partial line is detected, writes it to a .quarantine artifact before failing.
        """
        self.revisions_history = {}
        if not self.ledger_file.exists():
            return

        raw_bytes = self.ledger_file.read_bytes()
        if raw_bytes and not raw_bytes.endswith(b"\n"):
            # Identify the trailing partial line
            last_newline = raw_bytes.rfind(b"\n")
            corrupted_tail = raw_bytes[last_newline + 1:] if last_newline != -1 else raw_bytes

            quarantine_path = self.ledger_file.with_name(self.ledger_file.name + ".quarantine")
            if quarantine_path.exists():
                quarantine_path = self.ledger_file.with_name(
                    f"{self.ledger_file.name}.quarantine.{int(time.time() * 1000)}_{os.getpid()}"
                )
            with open(quarantine_path, "wb") as qf:
                qf.write(corrupted_tail)
                qf.flush()
                os.fsync(qf.fileno())

            raise MemoryLedgerIntegrityError(
                f"MEMORY_LEDGER_INTEGRITY_FAILURE: Partial/unclosed trailing line detected in ledger '{self.ledger_file.resolve()}'. "
                f"Corrupted tail isolated to quarantine artifact: '{quarantine_path.resolve()}'."
            )

        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:

                    data = json.loads(line)
                except Exception as e:
                    raise MemoryLedgerIntegrityError(
                        f"MEMORY_LEDGER_INTEGRITY_FAILURE: Malformed JSON at line {line_idx} in ledger '{self.ledger_file}': {e}"
                    )

                for required_key in ["observation_id", "revision", "claim", "current_hash", "previous_hash"]:
                    if required_key not in data:
                        raise MemoryLedgerIntegrityError(
                            f"MEMORY_LEDGER_INTEGRITY_FAILURE: Missing required key '{required_key}' at line {line_idx} in ledger."
                        )

                rev = ObservationRevision(
                    observation_id=data["observation_id"],
                    revision=data["revision"],
                    claim=data["claim"],
                    supporting_memory_ids=data.get("supporting_memory_ids", []),
                    contradicting_memory_ids=data.get("contradicting_memory_ids", []),
                    provenance=data.get("provenance", "RAW"),
                    previous_hash=data["previous_hash"],
                    current_hash=data["current_hash"],
                    valid_from=data.get("valid_from", ""),
                    valid_to=data.get("valid_to")
                )

                # 1. Verify computed hash against current_hash (Tamper Detection)
                expected_hash = rev.compute_hash()
                if rev.current_hash != expected_hash:
                    raise MemoryLedgerIntegrityError(
                        f"MEMORY_LEDGER_INTEGRITY_FAILURE: Hash mismatch at line {line_idx} for observation '{rev.observation_id}' (rev {rev.revision}). Expected {expected_hash}, got {rev.current_hash}."
                    )

                history = self.revisions_history.setdefault(rev.observation_id, [])
                prev_rev = history[-1] if history else None

                # 2. Verify chain continuity
                if prev_rev is None:
                    if rev.revision != 1 or rev.previous_hash != "0" * 16:
                        raise MemoryLedgerIntegrityError(
                            f"MEMORY_LEDGER_INTEGRITY_FAILURE: Invalid genesis revision {rev.revision} or previous_hash '{rev.previous_hash}' for observation '{rev.observation_id}'."
                        )
                else:
                    if rev.revision != prev_rev.revision + 1:
                        raise MemoryLedgerIntegrityError(
                            f"MEMORY_LEDGER_INTEGRITY_FAILURE: Revision gap detected for '{rev.observation_id}'. Expected {prev_rev.revision + 1}, got {rev.revision}."
                        )
                    if rev.previous_hash != prev_rev.current_hash:
                        raise MemoryLedgerIntegrityError(
                            f"MEMORY_LEDGER_INTEGRITY_FAILURE: Broken hash chain for '{rev.observation_id}'. Expected prev_hash '{prev_rev.current_hash}', got '{rev.previous_hash}'."
                        )

                history.append(rev)

    def _persist_revision(self, rev: ObservationRevision):
        """Appends revision durably with fsync to persistent jsonl ledger."""
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "observation_id": rev.observation_id,
            "revision": rev.revision,
            "claim": rev.claim,
            "supporting_memory_ids": rev.supporting_memory_ids,
            "contradicting_memory_ids": rev.contradicting_memory_ids,
            "provenance": rev.provenance,
            "previous_hash": rev.previous_hash,
            "current_hash": rev.current_hash,
            "valid_from": rev.valid_from,
            "valid_to": rev.valid_to
        }
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


    def create_proposal(
        self,
        target_bank: MemoryBankScope,
        claim: str,
        source_mission: str,
        evidence_payload: Dict[str, Any],
        evidence_contract: Optional[EvidenceContract] = None
    ) -> ObservationProposal:
        """
        Creates a proposal. Enforces:
        - Output budget (claim <= 256 tokens)
        - Input budget (total serialized input <= 512 tokens)
        - Evidence bounds
        """
        claim_tokens = estimate_tokens(claim)
        if claim_tokens > BUDGET_RETAIN_OUTPUT_TOKENS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Claim tokens ({claim_tokens}) exceeds output limit ({BUDGET_RETAIN_OUTPUT_TOKENS})."
            )

        serialized_input = json.dumps(
            {"claim": claim, "mission": source_mission, "payload": evidence_payload},
            ensure_ascii=False
        )
        total_input_tokens = estimate_tokens(serialized_input)
        if total_input_tokens > BUDGET_RETAIN_INPUT_TOKENS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Total input tokens ({total_input_tokens}) exceeds retain input limit ({BUDGET_RETAIN_INPUT_TOKENS})."
            )

        evidence_items = evidence_payload.get("records", [])
        if len(evidence_items) > BUDGET_REFLECT_EVIDENCE_RECORDS:
            raise MemoryBudgetExceededError(
                f"BLOCKED_MEMORY_BUDGET: Evidence records ({len(evidence_items)}) exceeds limit ({BUDGET_REFLECT_EVIDENCE_RECORDS})."
            )

        if evidence_contract:
            evidence_contract.validate_bounds()

        return ObservationProposal(
            id=f"prop_{uuid.uuid4().hex[:8]}",
            target_bank=target_bank,
            claim=claim.strip(),
            source_mission=source_mission,
            evidence_payload=evidence_payload,
            evidence_contract=evidence_contract,
            status=ProposalStatus.CANDIDATE,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

    def append_revision(
        self,
        observation_id: str,
        claim: str,
        supporting_memory_ids: Optional[List[str]] = None,
        contradicting_memory_ids: Optional[List[str]] = None,
        provenance: str = "RAW",
        valid_to: Optional[str] = None,
        explicit_revision: Optional[int] = None
    ) -> ObservationRevision:
        """Appends a new revision with chained SHA-256 hash and persists it under atomic lock."""
        with _APPEND_LOCK:
            with _os_process_lock(self.ledger_file):
                self._load_ledger()
                history = self.revisions_history.setdefault(observation_id, [])
                prev_rev = history[-1] if history else None

            if explicit_revision is not None:
                if any(r.revision == explicit_revision for r in history):
                    raise MemoryLedgerIntegrityError(
                        f"DUPLICATE_REVISION_BLOCKED: Revision {explicit_revision} already exists for observation '{observation_id}'."
                    )
                rev_num = explicit_revision
            else:
                rev_num = (prev_rev.revision + 1) if prev_rev else 1

            if any(r.revision == rev_num for r in history):
                raise MemoryLedgerIntegrityError(
                    f"DUPLICATE_REVISION_BLOCKED: Revision {rev_num} already exists for observation '{observation_id}'."
                )

            prev_hash = prev_rev.current_hash if prev_rev else "0" * 16

            rev = ObservationRevision(
                observation_id=observation_id,
                revision=rev_num,
                claim=claim.strip(),
                supporting_memory_ids=supporting_memory_ids or [],
                contradicting_memory_ids=contradicting_memory_ids or [],
                provenance=provenance,
                previous_hash=prev_hash,
                valid_from=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                valid_to=valid_to
            )
            rev.current_hash = rev.compute_hash()
            history.append(rev)
            self._persist_revision(rev)
            return rev


    def get_revisions(self, observation_id: str) -> List[ObservationRevision]:
        return list(self.revisions_history.get(observation_id, []))
