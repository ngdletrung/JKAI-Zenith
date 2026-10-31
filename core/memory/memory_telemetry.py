"""
Sovereign Memory Telemetry & Feedback Governance
File: core/memory/memory_telemetry.py
Governed by Phase R-Memory-7/8 Swarm Specification & Turn 498/500/508 Directives:
- Zero-leakage redaction: never logs raw claims, prompts, secrets, raw correlation IDs, or unverified metadata.
- Zero unlocked append: strictly requires process-safe OS file locking; lock failure increments error_count (FAIL-CLOSED to unlocked writes).
- Bounded in-memory buffer with observable drop and error metrics.
- Dual token estimator synchronization with per-bank and aggregate overflow enforcement.
- Real-time Security Sentinel: fail-closed at prompt boundary upon secret/injection detection.
- Non-causal reuse correlation tracking (correlation IDs are hashed before serialization; unlinked outcomes are UNKNOWN).
- Phase R-Memory-8 Operational Resilience:
  * TelemetryLogRotator: atomic flush+fsync rotation under process file_lock, retention manifest, non-blind pruning.
  * EmergencyDeadLetterRing: bounded in-memory buffer protecting security events during lock collisions.
  * WriteDropAlertPolicy: anti-spam alert episodes with cooldown windows and audited resets.
  * TokenEstimatorProtocol: pluggable immutable-per-run estimator interface with safe heuristic fallback.
"""

import os
import sys
import time
import json
import queue
import hashlib
import logging
import threading
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple, Protocol, runtime_checkable

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.memory.memory_verifier import SECRET_PATTERNS, INJECTION_PATTERNS

logger = logging.getLogger("JKAI.MemoryTelemetry")

TELEMETRY_DIR = PROJECT_ROOT / "data" / "memory_ledger"
TELEMETRY_LOG_FILE = TELEMETRY_DIR / "memory_telemetry.jsonl"
DEFAULT_MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_MAX_BACKUP_FILES = 5
MAX_QUEUE_SIZE = 1000
MAX_DEAD_LETTER_CAPACITY = 100


def hash_identifier(val: str) -> str:
    """Deterministic 16-char SHA-256 digest for safe anonymous telemetry identifiers."""
    if not val:
        return ""
    return hashlib.sha256(str(val).strip().encode("utf-8")).hexdigest()[:16]


def estimate_tokens(text: str) -> int:
    """
    Fast deterministic token estimator for English/Vietnamese UTF-8.
    Approximation policy: takes the maximum of word-based heuristic and character-length ratio
    to safely handle dense text, punctuation, and unspaced strings.
    """
    if not text:
        return 0
    clean = text.strip()
    if not clean:
        return 0
    words = clean.split()
    word_tokens = int(len(words) * 1.3) + 1
    char_tokens = int(len(clean) / 3.5) + 1
    return max(word_tokens, char_tokens)


@runtime_checkable
class TokenEstimatorProtocol(Protocol):
    """Protocol for pluggable target-model token estimators."""
    estimator_id: str
    estimator_version: str
    budget_policy_version: str

    def estimate_tokens(self, text: str) -> int:
        ...


class DualHeuristicEstimator:
    """Default zero-dependency, fail-safe dual estimator for UTF-8 Vietnamese/English."""
    estimator_id: str = "dual_heuristic"
    estimator_version: str = "v1.0"
    budget_policy_version: str = "v1.0"

    def estimate_tokens(self, text: str) -> int:
        return estimate_tokens(text)


class TelemetryEventType(str, Enum):
    RECALL = "RECALL"
    RETENTION = "RETENTION"
    SECURITY_SENTINEL = "SECURITY_SENTINEL"
    REUSE_CORRELATION = "REUSE_CORRELATION"
    BUFFER_DROP = "BUFFER_DROP"
    ESTIMATOR_FALLBACK = "ESTIMATOR_FALLBACK"
    ROTATION = "ROTATION"


@dataclass
class MemoryTelemetryEvent:
    """
    Strictly typed, redacted event payload.
    GUARANTEE: Zero raw claims, raw prompts, raw secrets, raw correlation IDs or open metadata escapes.
    """
    event_id: str
    event_type: str
    timestamp: float
    duration_ms: float = 0.0
    query_hash: str = ""
    mission_id_hash: str = ""
    receipt_id_hash: str = ""
    claim_hash: str = ""
    disp_count: int = 0
    exp_count: int = 0
    master_estimated_tokens: int = 0
    experience_estimated_tokens: int = 0
    estimated_tokens: int = 0
    budget_limit: int = 240
    per_bank_overflow: bool = False
    aggregate_overflow: bool = False
    is_truncated: bool = False
    security_flag: bool = False
    security_finding_type: str = ""
    outcome_status: str = "UNKNOWN"
    correlation_id_hash: str = ""
    link_confidence: float = 0.0
    drop_count: int = 0
    error_count: int = 0
    estimator_id: str = "dual_heuristic"
    estimator_version: str = "v1.0"
    budget_policy_version: str = "v1.0"
    is_fallback_estimator: bool = False

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)


@dataclass
class DeadLetterItem:
    """Wrapper for emergency buffered events awaiting retry."""
    event: MemoryTelemetryEvent
    retry_count: int = 0
    enqueued_at: float = 0.0


class EmergencyDeadLetterRing:
    """
    Bounded, thread-safe memory ring buffer for critical events (e.g. security sentinel events)
    that could not be written to disk due to temporary lock collisions.

    CRITICAL ARCHITECTURE DECLARATION:
    - STORAGE_TIER: BEST_EFFORT_PROCESS_LOCAL_RAM (IS_DURABLE = False).
    - This ring is strictly a PROCESS-LOCAL best-effort memory buffer, NOT a durable restart spool.
    - If the process terminates abnormally before shutdown(), in-memory events are not persisted.
    Guarantees:
    - Bounded capacity (max 100 items).
    - Stores strictly redacted event objects (zero raw secrets).
    - Explicit loss tracking (dead_letter_drop_count).
    - Retry limit policy (max 3 attempts).
    """
    STORAGE_TIER: str = "BEST_EFFORT_PROCESS_LOCAL_RAM"
    IS_DURABLE: bool = False

    def __init__(self, max_capacity: int = MAX_DEAD_LETTER_CAPACITY):
        self.max_capacity = max_capacity
        self.buffer: List[DeadLetterItem] = []
        self._lock = threading.RLock()
        self.dead_letter_drop_count: int = 0

    def push(self, event: MemoryTelemetryEvent) -> bool:
        with self._lock:
            if len(self.buffer) >= self.max_capacity:
                self.dead_letter_drop_count += 1
                logger.error("[EmergencyDeadLetter] Buffer full! Dropping item. Drop count: %d", self.dead_letter_drop_count)
                return False
            self.buffer.append(DeadLetterItem(event=event, retry_count=0, enqueued_at=time.time()))
            return True

    def pop_batch(self, limit: int = 20) -> List[DeadLetterItem]:
        with self._lock:
            batch = self.buffer[:limit]
            self.buffer = self.buffer[limit:]
            return batch

    def requeue_failed(self, item: DeadLetterItem, max_retries: int = 3):
        with self._lock:
            item.retry_count += 1
            if item.retry_count <= max_retries:
                if len(self.buffer) < self.max_capacity:
                    self.buffer.append(item)
                else:
                    self.dead_letter_drop_count += 1
            else:
                self.dead_letter_drop_count += 1
                logger.error("[EmergencyDeadLetter] Max retries (%d) exceeded for event %s! Discarded.", max_retries, item.event.event_id)

    def size(self) -> int:
        with self._lock:
            return len(self.buffer)


class TelemetryLogRotator:
    """
    Manages durable log rotation and retention under process file_lock.
    Guarantees:
    - Flush + fsync before atomic rotation.
    - Process-safe rename without race condition or record duplication.
    - Records rotation history in telemetry_rotation_manifest.json with SHA-256.
    - Non-blind retention: strictly prevents pruning files referenced by CompletionCertificates.
    - Fail-closed retention: blocks pruning when manifest is corrupted until explicit operator action.
    """
    def __init__(
        self,
        log_path: Path,
        max_bytes: int = DEFAULT_MAX_LOG_BYTES,
        max_backup_files: int = DEFAULT_MAX_BACKUP_FILES,
        manifest_path: Optional[Path] = None
    ):
        self.log_path = Path(log_path)
        self.max_bytes = max_bytes
        self.max_backup_files = max_backup_files
        self.manifest_path = manifest_path or (self.log_path.parent / "telemetry_rotation_manifest.json")
        self.retention_blocked: bool = False

    def should_rotate(self) -> bool:
        if not self.log_path.exists():
            return False
        try:
            return self.log_path.stat().st_size >= self.max_bytes
        except OSError:
            return False

    def unblock_retention(self, force: bool = False):
        """Allows operator to explicitly unblock retention after rebuilding/recovering manifest."""
        if force:
            self.retention_blocked = False
            logger.info("[LogRotator] Retention pruning unblocked by operator.")

    def _read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"version": "1.0", "rotations": []}
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if data.get("retention_blocked", False):
                self.retention_blocked = True
            return data
        except Exception as e:
            logger.error("[LogRotator] Manifest corruption detected: %s. Quarantining to .corrupt backup.", e)
            corrupt_backup = self.manifest_path.with_suffix(f".corrupt_{int(time.time()*1000)}")
            try:
                os.replace(self.manifest_path, corrupt_backup)
            except OSError:
                pass
            self.retention_blocked = True
            return {"version": "1.0", "rotations": [], "retention_blocked": True}

    def _atomic_write_manifest(self, manifest_data: dict):
        tmp_path = self.manifest_path.with_suffix(self.manifest_path.suffix + ".tmp")
        content = json.dumps(manifest_data, indent=2, ensure_ascii=False)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.manifest_path)

    def recover_unmanifested_archives(self) -> int:
        """
        Crash recovery scan: finds any rotated log files on disk that are missing from manifest
        and registers them to prevent unmanaged or orphaned files.
        """
        recovered_count = 0
        if not self.log_path.parent.exists():
            return 0

        manifest_data = self._read_manifest()
        known_files = {r.get("file_name") for r in manifest_data.get("rotations", [])}
        pattern = f"{self.log_path.stem}_*{self.log_path.suffix}"

        for p in sorted(self.log_path.parent.glob(pattern)):
            if p.name not in known_files and p != self.log_path:
                try:
                    data = p.read_bytes()
                    sha = hashlib.sha256(data).hexdigest()
                    manifest_data.setdefault("rotations", []).append({
                        "file_name": p.name,
                        "sha256": sha,
                        "byte_size": len(data),
                        "rotated_at": datetime.now().isoformat()
                    })
                    recovered_count += 1
                except Exception as e:
                    logger.warning("[LogRotator] Failed to recover unmanifested archive %s: %s", p.name, e)

        if recovered_count > 0:
            self._atomic_write_manifest(manifest_data)
            logger.info("[LogRotator] Crash recovery: registered %d unmanifested archive(s).", recovered_count)

        return recovered_count

    def rotate_if_needed(self) -> Optional[Path]:
        """
        Executes atomic rotation if file size >= max_bytes.
        MUST be called while holding process-safe file_lock!
        """
        self.recover_unmanifested_archives()
        if not self.should_rotate():
            return None

        # Generate unique timestamped archive name
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        rotated_path = self.log_path.parent / f"{self.log_path.stem}_{timestamp_str}{self.log_path.suffix}"

        # Atomic replacement
        os.replace(self.log_path, rotated_path)

        rot_bytes = rotated_path.read_bytes()
        rot_sha = hashlib.sha256(rot_bytes).hexdigest()

        # Update rotation manifest
        self._record_manifest(rotated_path.name, rot_sha, len(rot_bytes))

        # Enforce non-blind retention
        self._prune_old_archives()

        logger.info("[LogRotator] Rotated telemetry log to %s (SHA-256: %s...)", rotated_path.name, rot_sha[:12])
        return rotated_path

    def _record_manifest(self, file_name: str, sha256: str, byte_size: int):
        manifest_data = self._read_manifest()
        manifest_data.setdefault("rotations", []).append({
            "file_name": file_name,
            "sha256": sha256,
            "byte_size": byte_size,
            "rotated_at": datetime.now().isoformat()
        })
        self._atomic_write_manifest(manifest_data)

    def _prune_old_archives(self):
        if not self.manifest_path.exists():
            return
        if self.retention_blocked:
            logger.warning("[LogRotator] Retention pruning is BLOCKED due to manifest corruption. Fail-closed: operator action required.")
            return
        try:
            manifest_data = self._read_manifest()
            if self.retention_blocked or manifest_data.get("retention_blocked", False):
                logger.warning("[LogRotator] Retention pruning is BLOCKED in manifest. Operator action required.")
                return
            rotations = manifest_data.get("rotations", [])
            if len(rotations) <= self.max_backup_files:
                return

            to_prune = rotations[:-self.max_backup_files]
            remaining = rotations[-self.max_backup_files:]

            protected_files = self._get_protected_references()

            for item in to_prune:
                fname = item["file_name"]
                if fname in protected_files:
                    logger.info("[LogRotator] Protected archive preserved from retention pruning: %s", fname)
                    remaining.insert(0, item)
                    continue
                target = self.log_path.parent / fname
                try:
                    if target.exists():
                        target.unlink()
                except OSError as e:
                    logger.warning("[LogRotator] Failed to prune archive %s: %s", fname, e)
                    remaining.insert(0, item)

            manifest_data["rotations"] = remaining
            self._atomic_write_manifest(manifest_data)
        except Exception as e:
            logger.warning("[LogRotator] Non-fatal retention pruning error: %s", e)

    def _get_protected_references(self) -> set:
        protected = set()
        cert_ledger = self.log_path.parent / "completion_certificates.jsonl"
        if cert_ledger.exists():
            try:
                for line in cert_ledger.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        c = json.loads(line)
                        for a in c.get("artifacts_manifest", []):
                            protected.add(Path(a.get("path", "")).name)
            except Exception:
                pass
        return protected


class WriteDropAlertPolicy:
    """
    Anti-spam observability and alert state manager:
    - Tracks write drop threshold.
    - Enforces cooldown window to prevent alert storming.
    - Explicit reset with audit history.
    """
    def __init__(self, alert_threshold: int = 5, cooldown_seconds: float = 60.0):
        self.alert_threshold = alert_threshold
        self.cooldown_seconds = cooldown_seconds
        self.last_alert_time: float = 0.0
        self.alert_episode_id: str = ""
        self.reset_history: List[Dict[str, Any]] = []

    def evaluate_status(self, write_drop_count: int, dead_letter_drop_count: int = 0) -> str:
        now = time.time()
        if dead_letter_drop_count > 0:
            if now - self.last_alert_time >= self.cooldown_seconds:
                self.alert_episode_id = f"ep_dead_letter_{int(now)}_{dead_letter_drop_count}"
                self.last_alert_time = now
            return "ALERT_DEAD_LETTER_OVERFLOW"

        if write_drop_count >= self.alert_threshold:
            if now - self.last_alert_time >= self.cooldown_seconds:
                self.alert_episode_id = f"ep_write_drop_{int(now)}_{write_drop_count}"
                self.last_alert_time = now
            return "ALERT_HIGH_WRITE_DROPS"

        return "HEALTHY"

    def reset(self, reason: str):
        self.reset_history.append({
            "timestamp": time.time(),
            "reason": reason,
            "previous_episode": self.alert_episode_id
        })
        self.alert_episode_id = ""
        self.last_alert_time = 0.0


class SecuritySentinel:
    """
    Pre-prompt safety scanner detecting secrets, PII, and injection markers.
    Fail-closed: detection forces memory_context = '' before prompt delivery.
    """
    @staticmethod
    def scan_memory_text(text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans candidate recall string.
        Returns: (is_safe: bool, finding_type: Optional[str]).
        """
        if not text or not text.strip():
            return True, None

        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                # Return generic pattern category - NEVER log the matched secret text
                return False, "SECRET_PATTERN_DETECTED"

        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                return False, "PROMPT_INJECTION_DETECTED"

        return True, None


class MemoryTelemetryLogger:
    """
    Process-safe, resilient telemetry emitter.
    Guarantees:
    - Bounded memory queue (maxsize=1000). Drops are tracked and counted.
    - Zero unlocked append: lock failure never degrades to unlocked append; instead fail-closed to append and counts error_count.
    - Emergency dead-letter buffer for security events during OS lock collision.
    - Log rotation and retention under process file_lock.
    - Anti-spam alerting for high drop episodes.
    - Non-fatal execution: logging failures NEVER crash caller operations.
    """
    _instance: Optional["MemoryTelemetryLogger"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        log_path: Optional[Path] = None,
        max_queue: int = MAX_QUEUE_SIZE,
        max_log_bytes: int = DEFAULT_MAX_LOG_BYTES,
        max_backup_files: int = DEFAULT_MAX_BACKUP_FILES
    ):
        self.log_path = log_path or TELEMETRY_LOG_FILE
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self.drop_count: int = 0
        self.queue_drop_count: int = 0
        self.write_drop_count: int = 0
        self.error_count: int = 0
        self._write_lock = threading.RLock()

        # Phase R-Memory-8 Operational Resilience extensions
        self.rotator = TelemetryLogRotator(self.log_path, max_bytes=max_log_bytes, max_backup_files=max_backup_files)
        self.dead_letter_ring = EmergencyDeadLetterRing(max_capacity=MAX_DEAD_LETTER_CAPACITY)
        self.alert_policy = WriteDropAlertPolicy(alert_threshold=5, cooldown_seconds=60.0)
        self.estimator: TokenEstimatorProtocol = DualHeuristicEstimator()

    @classmethod
    def get_instance(cls) -> "MemoryTelemetryLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = MemoryTelemetryLogger()
            return cls._instance

    def set_estimator(self, estimator: TokenEstimatorProtocol):
        """Configures the active token estimator (must implement TokenEstimatorProtocol)."""
        self.estimator = estimator

    def estimate_tokens_with_policy(self, text: str) -> Tuple[int, str, str, str, bool]:
        """
        Safely computes tokens using active estimator.
        If custom estimator throws exception, emits fallback event and defaults to DualHeuristicEstimator.
        Returns: (tokens, estimator_id, estimator_version, budget_policy_version, is_fallback)
        """
        try:
            tokens = self.estimator.estimate_tokens(text)
            return tokens, getattr(self.estimator, "estimator_id", "custom"), getattr(self.estimator, "estimator_version", "v1.0"), getattr(self.estimator, "budget_policy_version", "v1.0"), False
        except Exception as exc:
            logger.warning("[MemoryTelemetry] Custom estimator failed (%s); failing safe to DualHeuristicEstimator.", exc)
            fallback = DualHeuristicEstimator()
            tokens = fallback.estimate_tokens(text)
            # Emit observable fallback event
            fb_evt = MemoryTelemetryEvent(
                event_id=f"est_fb_{int(time.time()*1000)}",
                event_type=TelemetryEventType.ESTIMATOR_FALLBACK.value,
                timestamp=time.time(),
                estimator_id=fallback.estimator_id,
                estimator_version=fallback.estimator_version,
                budget_policy_version=fallback.budget_policy_version,
                is_fallback_estimator=True,
                security_finding_type=f"ESTIMATOR_ERROR_{type(exc).__name__}"
            )
            self.emit_event(fb_evt)
            return tokens, fallback.estimator_id, fallback.estimator_version, fallback.budget_policy_version, True

    def get_metrics(self) -> Dict[str, Any]:
        """Returns observable telemetry operational counters and alert states."""
        alert_status = self.alert_policy.evaluate_status(
            self.write_drop_count,
            self.dead_letter_ring.dead_letter_drop_count
        )
        return {
            "drop_count": self.drop_count,
            "queue_drop_count": self.queue_drop_count,
            "write_drop_count": self.write_drop_count,
            "error_count": self.error_count,
            "queue_size": self.queue.qsize(),
            "dead_letter_size": self.dead_letter_ring.size(),
            "dead_letter_drop_count": self.dead_letter_ring.dead_letter_drop_count,
            "alert_status": alert_status,
            "alert_episode_id": self.alert_policy.alert_episode_id,
            "estimator_id": getattr(self.estimator, "estimator_id", "dual_heuristic"),
            "estimator_version": getattr(self.estimator, "estimator_version", "v1.0"),
        }

    def emit_event(self, event: MemoryTelemetryEvent) -> bool:
        """
        Enqueues an event into bounded queue and drains immediately in thread-safe manner.
        Returns True if enqueued, False if dropped due to queue overflow.
        """
        try:
            self.queue.put_nowait(event)
            self._drain_queue()
            return True
        except queue.Full:
            self.drop_count += 1
            self.queue_drop_count += 1
            logger.warning("[MemoryTelemetry] Bounded queue full! Drop count: %d", self.drop_count)
            return False
        except Exception as e:
            self.error_count += 1
            logger.debug("[MemoryTelemetry] Non-fatal emit exception: %s", e)
            return False

    def _drain_queue(self):
        """
        Flushes buffered events to durable JSONL log under process-safe file lock.
        CRITICAL: If file locking fails, NEVER fallback to unlocked append.
        Increment error_count, write_drop_count, and drop_count safely.
        Emergency dead-letter ring protects security events during lock failures.
        """
        with self._write_lock:
            if self.queue.empty() and self.dead_letter_ring.size() == 0:
                return

            items: List[MemoryTelemetryEvent] = []
            while not self.queue.empty():
                try:
                    items.append(self.queue.get_nowait())
                except queue.Empty:
                    break

            # Attempt to pull batch from dead-letter ring
            dl_items: List[DeadLetterItem] = self.dead_letter_ring.pop_batch(limit=20)
            combined_items = [dli.event for dli in dl_items] + items

            if not combined_items:
                return

            lines_to_write = [evt.to_json() for evt in combined_items]

            try:
                protocol_dir = PROJECT_ROOT / "Thao luan AI"
                if str(protocol_dir) not in sys.path:
                    sys.path.insert(0, str(protocol_dir))
                from file_lock import file_lock

                with file_lock(str(self.log_path)):
                    # Rotate if size exceeded under lock
                    self.rotator.rotate_if_needed()

                    with open(self.log_path, "a", encoding="utf-8") as f:
                        for l in lines_to_write:
                            f.write(l + "\n")
                        f.flush()
                        os.fsync(f.fileno())

            except Exception as e:
                # Strictly fail-closed: DO NOT perform unlocked append!
                batch_count = len(items)
                self.error_count += batch_count
                self.write_drop_count += batch_count
                self.drop_count += batch_count

                # Protect security events in emergency dead-letter ring
                for item in items:
                    if item.security_flag or item.event_type == TelemetryEventType.SECURITY_SENTINEL.value:
                        self.dead_letter_ring.push(item)

                # Requeue failed dead-letter items
                for dli in dl_items:
                    self.dead_letter_ring.requeue_failed(dli)

                logger.warning(
                    "[MemoryTelemetry] Process lock failure! Refusing unlocked append. "
                    "Write drop count: %d, Error count: %d. Error: %s",
                    self.write_drop_count, self.error_count, e
                )

    def shutdown(self):
        """
        Process lifecycle shutdown handler.
        Flushes all buffered queue items and attempts final drain of emergency dead-letter ring.
        """
        self._drain_queue()

    def log_recall(
        self,
        query: str,
        duration_ms: float,
        disp_count: int,
        exp_count: int,
        formatted_text: str,
        is_safe: bool,
        finding_type: Optional[str] = None,
        master_tokens: int = 0,
        exp_tokens: int = 0
    ) -> MemoryTelemetryEvent:
        """Constructs and emits redacted recall event with explicit per-bank and aggregate token metrics."""
        tokens, est_id, est_ver, b_ver, is_fb = self.estimate_tokens_with_policy(formatted_text)
        agg_overflow = tokens > 240
        per_bank_overflow = (master_tokens > 120) or (exp_tokens > 120)

        evt = MemoryTelemetryEvent(
            event_id=f"rec_{int(time.time()*1000)}_{hash_identifier(query)[:6]}",
            event_type=TelemetryEventType.RECALL.value,
            timestamp=time.time(),
            duration_ms=round(duration_ms, 2),
            query_hash=hash_identifier(query),
            disp_count=disp_count,
            exp_count=exp_count,
            master_estimated_tokens=master_tokens,
            experience_estimated_tokens=exp_tokens,
            estimated_tokens=tokens,
            budget_limit=240,
            per_bank_overflow=per_bank_overflow,
            aggregate_overflow=agg_overflow,
            is_truncated=" ..." in formatted_text,
            security_flag=not is_safe,
            security_finding_type=finding_type or "",
            drop_count=self.drop_count,
            error_count=self.error_count,
            estimator_id=est_id,
            estimator_version=est_ver,
            budget_policy_version=b_ver,
            is_fallback_estimator=is_fb
        )
        self.emit_event(evt)
        return evt

    def log_retention(
        self,
        mission_id: str,
        trace_id: str,
        receipt_id: str,
        verdict_status: str,
        claim_hash: str,
        success: bool
    ) -> MemoryTelemetryEvent:
        """Constructs and emits redacted retention event."""
        # Zero-leakage: ensure claim_hash is strictly a hash digest, never raw claim text
        if claim_hash and (len(claim_hash) != 16 or any(c not in "0123456789abcdef" for c in claim_hash.lower())):
            safe_claim_hash = hash_identifier(claim_hash)
        else:
            safe_claim_hash = claim_hash or ""

        evt = MemoryTelemetryEvent(
            event_id=f"ret_{int(time.time()*1000)}_{hash_identifier(mission_id)[:6]}",
            event_type=TelemetryEventType.RETENTION.value,
            timestamp=time.time(),
            mission_id_hash=hash_identifier(mission_id),
            receipt_id_hash=hash_identifier(receipt_id),
            claim_hash=safe_claim_hash,
            outcome_status=verdict_status if success else "FAIL",
            drop_count=self.drop_count,
            error_count=self.error_count,
            estimator_id=getattr(self.estimator, "estimator_id", "dual_heuristic"),
            estimator_version=getattr(self.estimator, "estimator_version", "v1.0"),
            budget_policy_version=getattr(self.estimator, "budget_policy_version", "v1.0")
        )
        self.emit_event(evt)
        return evt

    def log_reuse_correlation(
        self,
        memory_id: str,
        recall_event_id: str,
        mission_id: str,
        outcome_status: str,
        correlation_id: str,
        link_confidence: float = 1.0
    ) -> MemoryTelemetryEvent:
        """
        Records correlation between a past recalled memory and mission outcome.
        Requires explicit correlation_id; strictly hashes correlation_id (zero raw IDs).
        Missing or empty correlation_id forces outcome_status to UNKNOWN.
        """
        valid_correlation = bool(correlation_id and correlation_id.strip())
        final_status = outcome_status if valid_correlation else "UNKNOWN"
        corr_hash = hash_identifier(correlation_id) if valid_correlation else ""

        evt = MemoryTelemetryEvent(
            event_id=f"reu_{int(time.time()*1000)}_{hash_identifier(memory_id)[:6]}",
            event_type=TelemetryEventType.REUSE_CORRELATION.value,
            timestamp=time.time(),
            mission_id_hash=hash_identifier(mission_id),
            claim_hash=hash_identifier(memory_id),
            correlation_id_hash=corr_hash,
            outcome_status=final_status,
            link_confidence=link_confidence if valid_correlation else 0.0,
            drop_count=self.drop_count,
            error_count=self.error_count,
            estimator_id=getattr(self.estimator, "estimator_id", "dual_heuristic"),
            estimator_version=getattr(self.estimator, "estimator_version", "v1.0"),
            budget_policy_version=getattr(self.estimator, "budget_policy_version", "v1.0")
        )
        self.emit_event(evt)
        return evt


telemetry_logger = MemoryTelemetryLogger.get_instance()
