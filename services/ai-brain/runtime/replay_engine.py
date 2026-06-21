# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/replay_engine.py
# - Role: Deterministic Replay Engine
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Phuc hoi trang thai thuc thi tu du lieu payload dong bang trong JournalStore.
# - Dam bao 100% deterministic replay ma khong can goi lai LLM hoac cong cu thuc te.

import json

class ReplayEngine:
    """
    Co May Thoi Gian (Deterministic Replay Engine)
    Unit test toi cao cua toan bo he thong.
    """
    def __init__(self, journal_store):
        self.journal = journal_store

    def _get_frozen_payload(self, payload_hash: str) -> dict:
        """Lay lai payload goc da duoc dong bang tu Redis thong qua JournalStore."""
        try:
            raw = self.journal.redis.get(f"{self.journal.PAYLOAD_PREFIX}{payload_hash}")
            if raw:
                return json.loads(raw)
        except Exception as e:
            print(f"[REPLAY-WARN]: Failed to fetch frozen payload for hash '{payload_hash}': {e}")
        return {}

    def replay(self, trace_id: str, stop_at_state: str = None) -> str:
        """Replay lich su ma KHONG goi LLM hay Tool thuc te."""
        print(f"[REPLAY]: Bat dau Replay {trace_id}...")
        
        history = self.journal.get_history(trace_id)
        if not history:
            print("[REPLAY]: Khong tim thay trace_id trong Journal.")
            return "FAILED"

        # 1. Load Environment Fingerprint
        fingerprint = history.get("environment_fingerprint", {})
        print(f"[REPLAY]: Phuc hoi moi truong: Python {fingerprint.get('python_version')} - Policy {fingerprint.get('policy_hash')}")

        # 2. Bat dau Replay qua cac State Transitions
        current_state = "RECEIVED"
        
        for record in history.get("transitions", []):
            expected_next = record["state_after"]
            action = record["action"]
            
            # Lay lai payload thuc te da duoc dong bang
            input_payload = self._get_frozen_payload(record["input_hash"])
            output_payload = self._get_frozen_payload(record["output_hash"])
            
            # Phuc hoi va gia lap tung buoc chay logic ma khong invoke that
            print(f"[REPLAY-STEP]: Action: '{action}'")
            print(f"               Input  (Frozen): {input_payload}")
            print(f"               Output (Frozen): {output_payload}")
            
            print(f"[REPLAY-TRANSITION]: {current_state} -> {expected_next}")
            current_state = expected_next
            
            # Replay Time-Travel (Dung khan cap de Debug)
            if stop_at_state and current_state == stop_at_state:
                print(f"[REPLAY-STOP]: Time-Travel Stop tai state: {current_state}")
                break
                
        return current_state
