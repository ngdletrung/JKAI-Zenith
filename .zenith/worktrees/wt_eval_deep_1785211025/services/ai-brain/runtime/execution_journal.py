# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/execution_journal.py
# - Role: Append-Only Execution Journal Store
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Luu tru append-only xich thoi gian giao dich thuc thi an toan.
# - Ho tro luu tru anh xa payload goc va khôi phuc lich su trace phuc vu deterministic replay.

from dataclasses import dataclass
import time
import json
import hashlib

@dataclass(frozen=True)
class ExecutionRecord:
    """
    Execution Journal (Append-Only)
    Dam bao Forensic Debugging va Deterministic Recovery.
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
        self.PAYLOAD_PREFIX = "journal:payload:"

    def _hash_payload(self, payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def append(self, trace_id: str, actor: str, action: str, input_payload: dict, output_payload: dict, state_before: str, state_after: str):
        input_hash = self._hash_payload(input_payload)
        output_hash = self._hash_payload(output_payload)
        
        record = ExecutionRecord(
            trace_id=trace_id,
            timestamp=time.time(),
            actor=actor,
            action=action,
            input_hash=input_hash,
            output_hash=output_hash,
            state_before=state_before,
            state_after=state_after
        )
        
        # Luu tru mapping tu hash sang payload phuc vu Replay Engine
        try:
            self.redis.set(f"{self.PAYLOAD_PREFIX}{input_hash}", json.dumps(input_payload))
            self.redis.set(f"{self.PAYLOAD_PREFIX}{output_hash}", json.dumps(output_payload))
        except Exception as e:
            print(f"[JOURNAL-WARN]: Failed to store payload mappings in Redis: {e}")

        # Luu Append-only vao Redis List
        self.redis.rpush(f"journal:{trace_id}", json.dumps(record.__dict__))

    def get_history(self, trace_id: str) -> dict:
        """Doc va cau truc lai toan bo lich su trace phuc vu cho replay."""
        try:
            records_raw = self.redis.lrange(f"journal:{trace_id}", 0, -1)
        except Exception as e:
            print(f"[JOURNAL-ERR]: Failed to read list journal:{trace_id} from Redis: {e}")
            records_raw = []
            
        if not records_raw:
            return {}
        
        transitions = []
        for r_raw in records_raw:
            try:
                record = json.loads(r_raw)
                transitions.append(record)
            except Exception:
                pass
                
        # Giả định fingerprint cơ bản vì Redis không lưu thẳng fingerprint trong list
        fingerprint_raw = None
        try:
            fingerprint_raw = self.redis.get(f"journal:{trace_id}:metadata")
        except Exception:
            pass
            
        fingerprint = {}
        if fingerprint_raw:
            try:
                fingerprint = json.loads(fingerprint_raw)
            except Exception:
                pass
        else:
            import sys
            fingerprint = {
                "python_version": sys.version.split()[0],
                "policy_hash": "DEFAULT_POLICY"
            }
            
        return {
            "trace_id": trace_id,
            "environment_fingerprint": fingerprint,
            "transitions": transitions
        }
