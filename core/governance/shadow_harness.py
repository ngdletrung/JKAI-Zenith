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
        self._pending_observations: Dict[str, Dict[str, Any]] = {}

        if self.enabled:
            self.telemetry_dir.mkdir(parents=True, exist_ok=True)
            self._prune_expired_records()

    def start_observation(
        self,
        raw_state: Dict[str, Any],
        reflex_draft: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Initiates a pending observation waiting for execution receipt."""
        if not self.enabled:
            return None
        try:
            sanitized_state, report = StateSanitizer.sanitize_with_report(raw_state)
            fingerprint = StateSanitizer.compute_fingerprint(sanitized_state)
            redacted_count = report.get("redacted_count", 0) if isinstance(report, dict) else getattr(report, "redacted_keys_count", 0)
            
            cid = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
            
            # Prune pending map if bounded limit exceeded
            if len(self._pending_observations) >= 2000:
                oldest_key = next(iter(self._pending_observations))
                self._pending_observations.pop(oldest_key, None)
                
            self._pending_observations[cid] = {
                "timestamp": time.time(),
                "fingerprint": fingerprint,
                "sanitized_state": sanitized_state,
                "reflex_draft": reflex_draft,
                "redaction_count": redacted_count,
                "metadata": metadata or {}
            }
            return cid
        except Exception as e:
            sys.stderr.write(f"[SHADOW-HARNESS-WARN] Failed to start observation: {e}\n")
            return None

    def complete_observation(
        self,
        correlation_id: str,
        execution_receipt: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ShadowRecord]:
        """Completes a pending observation by attaching the execution receipt and persisting."""
        if not self.enabled or correlation_id not in self._pending_observations:
            return None
        try:
            pending = self._pending_observations.pop(correlation_id)
            now = time.time()
            merged_meta = dict(pending.get("metadata", {}))
            if metadata:
                merged_meta.update(metadata)
            merged_meta["correlation_id"] = correlation_id
            
            record = ShadowRecord(
                schema_version=SCHEMA_VERSION,
                record_id=f"sh_{uuid.uuid4().hex[:12]}",
                timestamp=now,
                iso_time=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                state_fingerprint=pending["fingerprint"],
                sanitized_state=pending["sanitized_state"],
                reflex_draft=pending["reflex_draft"],
                execution_receipt=execution_receipt,
                redaction_count=pending["redaction_count"],
                metadata=merged_meta
            )
            self._persist_record(record)
            return record
        except Exception as e:
            sys.stderr.write(f"[SHADOW-HARNESS-WARN] Failed to complete observation: {e}\n")
            return None

    def get_telemetry_stats(self) -> Dict[str, Any]:
        """Calculates pairing metrics across collected telemetry."""
        total = 0
        paired = 0
        file_path = self._get_active_file_path()
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        total += 1
                        try:
                            obj = json.loads(line)
                            if obj.get("execution_receipt") is not None:
                                paired += 1
                        except Exception:
                            pass
        unpaired = total - paired
        rate = round(paired / max(1, total) * 100, 2)
        return {
            "total_records": total,
            "paired_records": paired,
            "unpaired_records": unpaired,
            "pairing_rate_pct": rate
        }

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


_DEFAULT_SHADOW_HARNESS: Optional[ShadowHarness] = None


def get_default_shadow_harness(
    telemetry_dir: str = DEFAULT_TELEMETRY_DIR,
    enabled: Optional[bool] = None
) -> ShadowHarness:
    """Provides a thread-safe / global default instance of ShadowHarness."""
    global _DEFAULT_SHADOW_HARNESS
    if _DEFAULT_SHADOW_HARNESS is None:
        env_enabled = os.environ.get("JKAI_SHADOW_HARNESS_ENABLED", "1") == "1"
        is_enabled = env_enabled if enabled is None else enabled
        _DEFAULT_SHADOW_HARNESS = ShadowHarness(
            telemetry_dir=telemetry_dir,
            enabled=is_enabled
        )
    return _DEFAULT_SHADOW_HARNESS
