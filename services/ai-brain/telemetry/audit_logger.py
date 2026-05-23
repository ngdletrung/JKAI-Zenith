import hashlib
import json
import time

class AuditLogger:
    """
    📜 Sổ Bìa Đen (Immutable Hash-Chain Audit)
    Không overwrite, Không mutate. Bằng chứng thép.
    """
    def __init__(self, redis_conn):
        self.redis = redis_conn
        self.LAST_HASH_KEY = "audit:last_hash"

    def _hash(self, payload: str) -> str:
        return hashlib.sha256(payload.encode()).hexdigest()

    def append(self, action: str, subject: str, details: dict):
        prev_hash = self.redis.get(self.LAST_HASH_KEY) or "GENESIS_HASH"
        
        payload_dict = {
            "ts": time.time(),
            "action": action,
            "subject": subject,
            "details": details
        }
        payload_str = json.dumps(payload_dict, sort_keys=True)
        payload_hash = self._hash(payload_str)
        
        # entry_hash = sha256(prev_hash + payload_hash)
        entry_hash = self._hash(prev_hash + payload_hash)
        
        entry = {
            "entry_hash": entry_hash,
            "prev_hash": prev_hash,
            "payload": payload_dict
        }
        
        # Lưu vào Redis List hoặc DB bất biến
        self.redis.rpush("audit_chain", json.dumps(entry))
        self.redis.set(self.LAST_HASH_KEY, entry_hash)
        
        return entry_hash
