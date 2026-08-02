import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("JKAI.Context.WorkingMemory")

_TTL = 1800
_ENGINE = None


def _get_engine_redis():
    global _ENGINE
    if _ENGINE is None:
        try:
            from core.utils.engine import engine as _e
            _ENGINE = _e
        except Exception:
            return None
    try:
        return _ENGINE._get_redis()
    except Exception:
        return None


class WorkingRecord:
    def __init__(self, record_id: str, record_type: str, owner: str, data: Any, scope: str = "MISSION", ttl: int = _TTL):
        self.id = record_id
        self.type = record_type
        self.owner = owner
        self.data = data
        self.scope = scope
        self.ts = time.time()
        self.ttl = ttl

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "owner": self.owner, "data": self.data, "scope": self.scope, "ts": self.ts}


class WorkingMemory:
    def _wm_key(self, mission_id: str) -> str:
        return f"wm:{mission_id}"

    def push(self, mission_id: str, record: WorkingRecord):
        r = _get_engine_redis()
        if not r:
            return
        try:
            key = self._wm_key(mission_id)
            r.rpush(key, json.dumps(record.to_dict(), ensure_ascii=False))
            r.expire(key, record.ttl)
        except Exception as e:
            logger.warning(f"[WM] push error: {e}")

    def query(self, mission_id: str, record_type: str = "", scope: str = "", limit: int = 20) -> list[WorkingRecord]:
        r = _get_engine_redis()
        if not r:
            return []
        try:
            raw_list = r.lrange(self._wm_key(mission_id), -limit, -1)
        except Exception:
            return []
        results = []
        for raw in raw_list:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            if record_type and d.get("type") != record_type:
                continue
            if scope and d.get("scope") != scope:
                continue
            rec = WorkingRecord(d["id"], d["type"], d["owner"], d["data"], d.get("scope", "MISSION"))
            rec.ts = d.get("ts", 0)
            results.append(rec)
        return results

    def get_latest(self, mission_id: str, record_type: str = "") -> Optional[WorkingRecord]:
        results = self.query(mission_id, record_type=record_type, limit=1)
        return results[0] if results else None

    def clear(self, mission_id: str):
        r = _get_engine_redis()
        if not r:
            return
        try:
            r.delete(self._wm_key(mission_id))
        except Exception:
            pass

    def push_tool_result(self, mission_id: str, tool: str, result: Any, owner: str = "executor"):
        rec = WorkingRecord(record_id=f"tool:{tool}:{int(time.time())}", record_type="tool_result", owner=owner, data={"tool": tool, "result": result}, scope="MISSION")
        self.push(mission_id, rec)

    def get_tool_results(self, mission_id: str) -> list[dict]:
        return [r.data for r in self.query(mission_id, record_type="tool_result")]

    def push_critic_verdict(self, mission_id: str, verdict: dict, owner: str = "critic"):
        rec = WorkingRecord(record_id=f"critic:{int(time.time())}", record_type="critic_verdict", owner=owner, data=verdict, scope="MISSION")
        self.push(mission_id, rec)

    def get_critic_verdict(self, mission_id: str) -> Optional[dict]:
        rec = self.get_latest(mission_id, record_type="critic_verdict")
        return rec.data if rec else None

    def push_planner_note(self, mission_id: str, note: dict, owner: str = "planner"):
        rec = WorkingRecord(record_id=f"planner:{int(time.time())}", record_type="planner_note", owner=owner, data=note, scope="MISSION")
        self.push(mission_id, rec)
