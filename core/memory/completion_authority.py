"""
Sovereign Completion Authority Store
File: core/memory/completion_authority.py
Governed by SOP V5.1 & Phase R-Memory-8 Directive:
- Immutable, tamper-evident hash-chain for CompletionCertificates.
- Independent CompletionAuthority gate: rejects unauthorized/spoofed certificate issuers.
- Process-safe append-only persistence under file_lock.
- Fail-closed tamper detection.
"""

import os
import sys
import json
import time
import hashlib
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROTOCOL_DIR = PROJECT_ROOT / "Thao luan AI"
if str(PROTOCOL_DIR) not in sys.path:
    sys.path.insert(0, str(PROTOCOL_DIR))

from file_lock import file_lock

logger = logging.getLogger("JKAI.CompletionAuthority")

DEFAULT_AUTHORITY_LEDGER = PROJECT_ROOT / "data" / "memory_ledger" / "completion_certificates.jsonl"
DEFAULT_AUTHORITY_TOKEN = os.environ.get("COMPLETION_AUTHORITY_KEY", "")


def canonical_json_dumps(data: Dict[str, Any]) -> str:
    """Deterministic, sorted JSON string for stable SHA-256 hashing."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class CompletionAuthorityStore:
    """
    Process-safe, append-only store for immutable CompletionCertificates.
    Guarantees:
    - Strict issuer authority gate: only callers presenting the valid authority token can issue certificates.
    - Tamper-evident hash chaining: each certificate links to the SHA-256 digest of the previous certificate.
    - Fail-closed integrity check: any file corruption or unauthorized modification halts verification.
    """

    def __init__(self, ledger_path: Optional[Path] = None, authority_token: Optional[str] = None):
        self.ledger_path = Path(ledger_path) if ledger_path else DEFAULT_AUTHORITY_LEDGER
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.authority_token = authority_token if authority_token is not None else DEFAULT_AUTHORITY_TOKEN
        self.key_version: int = 1
        self._rotation_receipts: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def set_authority_token(self, new_token: str) -> Dict[str, Any]:
        """
        Allows dynamic token rotation in a thread-safe manner without leaking secrets.
        Increments key_version and emits a rotation receipt containing version, timestamp,
        and truncated SHA-256 fingerprint (zero raw secrets).
        """
        if not new_token or not isinstance(new_token, str):
            raise ValueError("Authority token must be a non-empty string.")
        with self._lock:
            self.key_version += 1
            self.authority_token = new_token
            fingerprint = hashlib.sha256(new_token.encode("utf-8")).hexdigest()[:16]
            receipt = {
                "key_version": self.key_version,
                "rotated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "key_fingerprint": fingerprint,
            }
            self._rotation_receipts.append(receipt)
            return receipt

    def get_rotation_receipts(self) -> List[Dict[str, Any]]:
        """Returns copies of all key rotation receipts without revealing secrets."""
        with self._lock:
            return [dict(r) for r in self._rotation_receipts]

    def _get_last_certificate_hash_under_lock(self) -> str:
        """Assumes caller holds file_lock. Reads last certificate hash; returns GENESIS if empty."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return "GENESIS"

        lines = [l.strip() for l in self.ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return "GENESIS"

        try:
            last_record = json.loads(lines[-1])
            return last_record.get("certificate_hash", "GENESIS")
        except Exception as e:
            logger.error("[CompletionAuthority] Corrupted last line in ledger: %s", e)
            raise RuntimeError(f"Completion ledger corrupted, cannot resolve last hash: {e}") from e

    def _verify_ledger_integrity_under_lock(self) -> Tuple[bool, Optional[str]]:
        """Assumes caller holds file_lock. Scans entire ledger and verifies hash chain from GENESIS."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return True, None

        lines = [l.strip() for l in self.ledger_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        expected_prev_hash = "GENESIS"

        for idx, line in enumerate(lines):
            try:
                record = json.loads(line)
            except Exception as e:
                return False, f"JSON_CORRUPTION at line {idx+1}: {e}"

            stored_hash = record.get("certificate_hash")
            stored_prev = record.get("previous_certificate_hash")

            if stored_prev != expected_prev_hash:
                return False, f"HASH_CHAIN_BROKEN at line {idx+1}: expected prev {expected_prev_hash}, got {stored_prev}"

            payload_copy = {k: v for k, v in record.items() if k != "certificate_hash"}
            canonical_str = canonical_json_dumps(payload_copy)
            calculated_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

            if calculated_hash != stored_hash:
                return False, f"TAMPER_DETECTED at line {idx+1} (ID: {record.get('certificate_id')}): expected {calculated_hash}, found {stored_hash}"

            expected_prev_hash = stored_hash

        return True, None

    def _get_certificate_under_lock(self, certificate_id: str) -> Optional[Dict[str, Any]]:
        """Assumes caller holds file_lock. Searches ledger for certificate_id."""
        if not self.ledger_path.exists():
            return None
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    record = json.loads(line)
                    if record.get("certificate_id") == certificate_id:
                        return record
                except Exception:
                    continue
        return None

    def record_certificate(
        self,
        certificate_data: Dict[str, Any],
        token: str,
    ) -> Dict[str, Any]:
        """
        Public entrypoint: Acquires process file_lock, validates token, and delegates to *_under_lock methods.
        """
        # 1. Authority Issuer Gate
        with self._lock:
            current_token = self.authority_token
        if not current_token or not token or token != current_token:
            logger.warning("[CompletionAuthority] Unauthorized issuer attempt rejected.")
            raise PermissionError("Unauthorized completion certificate issuer: invalid or unconfigured authority key.")

        # 2. Mandatory Fields Validation
        required_fields = ["phase", "session_id", "gate_target", "artifacts_manifest", "evidence_verification"]
        for field in required_fields:
            if field not in certificate_data:
                raise ValueError(f"Missing mandatory certificate field: '{field}'")

        # 3. Process-safe Atomic Append
        with file_lock(str(self.ledger_path)):
            # Integrity check of pre-existing ledger: fail-closed if corrupted/tampered
            is_valid, err = self._verify_ledger_integrity_under_lock()
            if not is_valid:
                raise RuntimeError(f"Cannot append certificate: pre-existing ledger is tampered ({err})")

            # Duplicate certificate_id check
            cert_id = certificate_data.get("certificate_id")
            if cert_id:
                if self._get_certificate_under_lock(cert_id) is not None:
                    raise ValueError(f"Duplicate certificate_id '{cert_id}' rejected.")
            else:
                import uuid
                cert_id = f"cert_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}_{certificate_data['phase']}"

            prev_hash = self._get_last_certificate_hash_under_lock()
            issued_at = certificate_data.get("issued_at") or time.strftime("%Y-%m-%dT%H:%M:%S%z")

            record_payload = {
                "certificate_id": cert_id,
                "phase": certificate_data["phase"],
                "session_id": certificate_data["session_id"],
                "gate_target": certificate_data["gate_target"],
                "status": certificate_data.get("status", "SEALED_FOR_CONTROLLED_PILOT"),
                "governance": certificate_data.get("governance", "SOP V5.1"),
                "issuer": certificate_data.get("issuer", "CompletionAuthority"),
                "authority_key_version": self.key_version,
                "issued_at": issued_at,
                "parent_commit": certificate_data.get("parent_commit", ""),
                "artifacts_manifest": certificate_data["artifacts_manifest"],
                "evidence_verification": certificate_data["evidence_verification"],
                "production_readiness_guarantees": certificate_data.get("production_readiness_guarantees", {}),
                "previous_certificate_hash": prev_hash,
            }

            canonical_str = canonical_json_dumps(record_payload)
            cert_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
            record_payload["certificate_hash"] = cert_hash

            final_line = json.dumps(record_payload, ensure_ascii=False)

            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(final_line + "\n")
                f.flush()
                os.fsync(f.fileno())

            logger.info("[CompletionAuthority] Recorded certificate %s (Hash: %s...)", cert_id, cert_hash[:12])
            return record_payload

    def verify_ledger_integrity(self) -> Tuple[bool, Optional[str]]:
        """Public entrypoint: Acquires file_lock and verifies full hash chain."""
        if not self.ledger_path.exists() or self.ledger_path.stat().st_size == 0:
            return True, None
        with file_lock(str(self.ledger_path)):
            return self._verify_ledger_integrity_under_lock()

    def get_certificate(self, certificate_id: str) -> Optional[Dict[str, Any]]:
        """Public entrypoint: Acquires file_lock and retrieves certificate."""
        if not self.ledger_path.exists():
            return None
        with file_lock(str(self.ledger_path)):
            return self._get_certificate_under_lock(certificate_id)
