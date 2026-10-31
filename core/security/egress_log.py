# -*- coding: utf-8 -*-
"""
JKAI Egress Log Hash-Chain Ledger.
Provides tamper-evident cryptographic auditability of all outbound egress events.
Chains: prev_hash -> entry_hash = sha256(prev_hash + timestamp + mission_id + model + payload_hash + tokens).
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class EgressLogEntry:
    index: int
    prev_hash: str
    timestamp: str
    mission_id: str
    model: str
    payload_hash: str
    token_count: int
    entry_hash: str


class EgressLogLedger:
    """
    Append-only cryptographically linked audit ledger for cloud egress calls.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, ledger_path: Optional[str] = None):
        self.ledger_path = (
            ledger_path or os.getenv("JKAI_EGRESS_LEDGER_PATH") or "data/telemetry/egress_hash_chain.jsonl"
        )
        self.entries: List[EgressLogEntry] = []
        self._load_or_init()

    def _load_or_init(self):
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            self.entries.append(EgressLogEntry(**data))
                        except Exception:
                            pass

    @staticmethod
    def compute_payload_hash(payload_text: str) -> str:
        return hashlib.sha256(payload_text.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_entry_hash(
        prev_hash: str,
        timestamp: str,
        mission_id: str,
        model: str,
        payload_hash: str,
        token_count: int,
    ) -> str:
        raw = f"{prev_hash}|{timestamp}|{mission_id}|{model}|{payload_hash}|{token_count}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def record_egress(
        self,
        mission_id: str,
        model: str,
        sanitized_payload: str,
        token_count: int,
    ) -> EgressLogEntry:
        """Appends a new verified entry to the hash chain."""
        prev_hash = (
            self.entries[-1].entry_hash if self.entries else self.GENESIS_HASH
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        payload_hash = self.compute_payload_hash(sanitized_payload)
        entry_hash = self.compute_entry_hash(
            prev_hash, timestamp, mission_id, model, payload_hash, token_count
        )

        entry = EgressLogEntry(
            index=len(self.entries) + 1,
            prev_hash=prev_hash,
            timestamp=timestamp,
            mission_id=mission_id,
            model=model,
            payload_hash=payload_hash,
            token_count=token_count,
            entry_hash=entry_hash,
        )

        self.entries.append(entry)

        # Persist with pure LF line endings
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

        return entry

    def verify_chain_integrity(self) -> bool:
        """Verifies the unbroken cryptographic integrity of the entire ledger."""
        if not self.entries:
            return True

        expected_prev_hash = self.GENESIS_HASH
        for entry in self.entries:
            if entry.prev_hash != expected_prev_hash:
                return False  # Chain broken

            recomputed_hash = self.compute_entry_hash(
                entry.prev_hash,
                entry.timestamp,
                entry.mission_id,
                entry.model,
                entry.payload_hash,
                entry.token_count,
            )
            if recomputed_hash != entry.entry_hash:
                return False  # Tampered entry

            expected_prev_hash = entry.entry_hash

        return True

    def rotate_ledger(self, reason: str = "ARCHIVE") -> str:
        """
        Safely rotates current ledger to a backup file without data loss.
        Preserves chain of custody: records a tombstone rotation entry in old file,
        renames to .bak.<ts>, and re-initializes an empty active ledger.
        """
        import shutil
        import time
        if not os.path.exists(self.ledger_path):
            return self.ledger_path

        ts = int(time.time())
        backup_path = f"{self.ledger_path}.bak.{ts}"
        if self.entries:
            self.record_egress(
                mission_id="ROTATION_TOMBSTONE",
                model="SYSTEM",
                sanitized_payload=f"ROTATION_REASON: {reason} | BACKUP: {backup_path}",
                token_count=0,
            )

        shutil.move(self.ledger_path, backup_path)
        self.entries = []
        return backup_path


egress_ledger = EgressLogLedger()
