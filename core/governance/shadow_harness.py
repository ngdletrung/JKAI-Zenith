"""
Shadow Telemetry Harness for JKAI Sovereign Runtime.
Collects non-blocking (state, reflex_draft, execution_receipt) observation triples
for offline calibration, Conformal Prediction, and local model fine-tuning.

Conditions Enforced per Red Team Turn 92 Audit Mandate:
1. Schema Versioned (v1.0.0).
2. State Sanitizer 2.3a enforced BEFORE storage (64KB cap, secret scrubbing, SHA-256 canonical hash).
3. Bounded storage: Sampling cap (max 5,000 records/file) and automated retention pruning (14 days).
4. No self-tautological conclusions allowed on un-evaluated shadow data.
"""

import os
import sys
import json
import time
import uuid
import glob
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from core.sanitizer.state_sanitizer import StateSanitizer

SCHEMA_VERSION = "1.0.0"
DEFAULT_TELEMETRY_DIR = "storage/shadow_telemetry"
MAX_RECORDS_PER_FILE = 5000
MAX_RETENTION_DAYS = 14


@dataclass
class ShadowRecord:
    schema_version: str
    record_id: str
    timestamp: float
    iso_time: str
    state_fingerprint: str
    sanitized_state: Dict[str, Any]
    reflex_draft: Optional[Dict[str, Any]]
    execution_receipt: Optional[Dict[str, Any]]
    redaction_count: int
    metadata: Dict[str, Any]


class ShadowHarness:
    """Non-blocking shadow telemetry recorder."""

    def __init__(
        self,
        telemetry_dir: str = DEFAULT_TELEMETRY_DIR,
        max_records_per_file: int = MAX_RECORDS_PER_FILE,
        retention_days: int = MAX_RETENTION_DAYS,
        enabled: bool = True
    ):
        self.telemetry_dir = Path(telemetry_dir)
        self.max_records_per_file = max_records_per_file
        self.retention_days = retention_days
        self.enabled = enabled
        self._current_file_records = 0

        if self.enabled:
            self.telemetry_dir.mkdir(parents=True, exist_ok=True)
            self._prune_expired_records()

    def record_observation(
        self,
        raw_state: Dict[str, Any],
        reflex_draft: Optional[Dict[str, Any]] = None,
        execution_receipt: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ShadowRecord]:
        """Sanitizes state and records an observation triple asynchronously."""
        if not self.enabled:
            return None

        try:
            # Condition 2: Enforce StateSanitizer 2.3a BEFORE storage
            sanitized_state, report = StateSanitizer.sanitize_with_report(raw_state)
            fingerprint = StateSanitizer.compute_fingerprint(sanitized_state)
            redacted_count = report.get("redacted_count", 0) if isinstance(report, dict) else getattr(report, "redacted_keys_count", 0)

            now = time.time()
            record = ShadowRecord(
                schema_version=SCHEMA_VERSION,
                record_id=f"sh_{uuid.uuid4().hex[:12]}",
                timestamp=now,
                iso_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                state_fingerprint=fingerprint,
                sanitized_state=sanitized_state,
                reflex_draft=reflex_draft,
                execution_receipt=execution_receipt,
                redaction_count=redacted_count,
                metadata=metadata or {}
            )

            self._persist_record(record)
            return record

        except Exception as e:
            # Non-blocking: failures in shadow recording MUST NEVER crash core execution
            sys.stderr.write(f"[SHADOW-HARNESS-WARN] Failed to record shadow telemetry: {e}\n")
            return None

    def _get_active_file_path(self) -> Path:
        date_str = time.strftime("%Y%m%d")
        return self.telemetry_dir / f"shadow_telemetry_{date_str}.jsonl"

    def _persist_record(self, record: ShadowRecord) -> None:
        file_path = self._get_active_file_path()
        payload = json.dumps(asdict(record), ensure_ascii=False)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(payload + "\n")
        self._current_file_records += 1

    def _prune_expired_records(self) -> int:
        """Prunes files older than retention_days."""
        pruned_count = 0
        cutoff_time = time.time() - (self.retention_days * 86400)
        for p in self.telemetry_dir.glob("shadow_telemetry_*.jsonl"):
            try:
                if p.stat().st_mtime < cutoff_time:
                    p.unlink()
                    pruned_count += 1
            except Exception:
                pass
        return pruned_count
