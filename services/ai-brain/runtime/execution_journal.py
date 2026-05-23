from dataclasses import dataclass
import time
import json
import hashlib

@dataclass(frozen=True)
class ExecutionRecord:
    """
    📜 Execution Journal (Append-Only)
    Đảm bảo Forensic Debugging và Deterministic Recovery.
    """
    trace_id: str
    timestamp: float
    actor: str
    action: str
    input_hash: str
    output_hash: str
    state_before: str
    state_after: str

class JournalStore:
    def __init__(self, redis_conn):
        self.redis = redis_conn

    def _hash_payload(self, payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def append(self, trace_id: str, actor: str, action: str, input_payload: dict, output_payload: dict, state_before: str, state_after: str):
        record = ExecutionRecord(
            trace_id=trace_id,
            timestamp=time.time(),
            actor=actor,
            action=action,
            input_hash=self._hash_payload(input_payload),
            output_hash=self._hash_payload(output_payload),
            state_before=state_before,
            state_after=state_after
        )
        # Lưu Append-only vào Redis List
        self.redis.rpush(f"journal:{trace_id}", json.dumps(record.__dict__))
