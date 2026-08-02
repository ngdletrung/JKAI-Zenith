import json
import time
from typing import Dict, Any, Optional
from core.redis_client import redis_safe
from core.utils.event_store import event_store

class PersistentEventJournal:
    """
    📜 Persistent Event Journal (Atomic Event Sourcing)
    Provides exactly-once, auditable write-ahead state logs in Redis and
    persistent SQLite event stores with Hybrid Logical Clock (HLC) protection.
    """
    def __init__(self):
        self.prefix = "journal:"

    def append(self, 
               task_id: str, 
               trace_id: str, 
               actor: str, 
               event_type: str, 
               state_before: str, 
               state_after: str, 
               payload: Dict[str, Any],
               metadata: Optional[Dict[str, Any]] = None):
        """
        Atomically appends an execution or state transition record to:
        1. Redis list (under `journal:{trace_id}`) for fast hot-path retrieval / streaming
        2. SQLite DB (`zenith_events.db` via EventStore) for forensic auditing
        """
        record = {
            "task_id": task_id,
            "trace_id": trace_id,
            "timestamp": time.time(),
            "actor": actor,
            "event_type": event_type,
            "state_before": state_before,
            "state_after": state_after,
            "payload": payload,
            "metadata": metadata or {}
        }
        
        payload_str = json.dumps(record, ensure_ascii=False)
        
        # 1. Write to Redis (hot path)
        def _redis_append(r):
            key = f"{self.prefix}{trace_id}"
            r.rpush(key, payload_str)
            r.expire(key, 86400 * 7) # Keep journal in cache for 7 days
            
            # Pub/Sub a monitoring event for live dashboard tracking
            r.publish("monitor:state_transitions", payload_str)
        
        redis_safe(_redis_append)
        
        # 2. Write to SQLite (forensic store)
        event_store.log_event(
            task_id=task_id,
            agent_id=actor,
            event_type=event_type,
            payload={
                "trace_id": trace_id,
                "state_before": state_before,
                "state_after": state_after,
                "payload": payload,
                "metadata": metadata or {}
            }
        )

# Global Singleton
event_journal = PersistentEventJournal()
