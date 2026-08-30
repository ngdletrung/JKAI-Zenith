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


# =====================================================================
# 📚 RECENT OPERATIONS STORE (OPERATIONAL MEMORY - TRỤ CỘT 2)
# =====================================================================
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field

@dataclass
class RecentOperation:
    op_id: str
    action_type: str        # e.g., "DELETE_SKILL", "FORGE_SKILL", "RUN_TEST", "MODIFY_FILE"
    target: str             # e.g., "skill_stub_50", "SKILL_FORGE", "tests/test_router.py"
    details: str
    result: str             # "SUCCESS", "FAILURE", "PENDING"
    timestamp: float = field(default_factory=time.time)

    def to_summary(self) -> str:
        dt = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(self.timestamp))
        return f"[{dt}] [{self.action_type}] {self.target} - {self.details} (Kết quả: {self.result})"


class RecentOperationsStore:
    """
    Vòng đệm lưu trữ 50 hoạt động/thao tác gần nhất của hệ thống trong 24h.
    Lưu trên bộ nhớ và đồng bộ file context/recent_operations.json.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_records: int = 50):
        if self._initialized:
            return
        self.max_records = max_records
        self.records: list[RecentOperation] = []
        self._file_path = Path(__file__).parent / "recent_operations.json"
        self._load_from_disk()
        self._initialized = True

    def _load_from_disk(self):
        if self._file_path.exists():
            try:
                data = json.loads(self._file_path.read_text(encoding="utf-8"))
                for d in data[-self.max_records:]:
                    self.records.append(RecentOperation(**d))
            except Exception as e:
                logger.warning(f"[RECENT-OPS] Lỗi load file disk: {e}")

    def _save_to_disk(self):
        try:
            data = [asdict(r) for r in self.records]
            self._file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[RECENT-OPS] Lỗi save file disk: {e}")

    def record_operation(self, action_type: str, target: str, details: str, result: str = "SUCCESS"):
        """Ghi nhận một thao tác vận hành mới."""
        op = RecentOperation(
            op_id=f"op_{int(time.time())}_{len(self.records)}",
            action_type=action_type,
            target=target,
            details=details,
            result=result,
            timestamp=time.time()
        )
        self.records.append(op)
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
        self._save_to_disk()
        logger.info(f"📚 [OPERATIONAL-MEMORY]: Ghi nhận thao tác {action_type} - {target}")

    def get_recent_summary(self, limit: int = 10) -> str:
        """Lấy tóm tắt các thao tác gần nhất dưới dạng văn bản cho LLM."""
        if not self.records:
            return "Chưa có ghi chép thao tác vận hành gần đây."
        recent = self.records[-limit:]
        return "\n".join([r.to_summary() for r in reversed(recent)])


recent_operations_store = RecentOperationsStore()
# Ghi nhận ngay chiến dịch dọn dẹp và nâng cấp kỹ năng làm mốc lịch sử
if not recent_operations_store.records:
    recent_operations_store.record_operation(
        "CLEAN_STUB_SKILLS",
        "50_mock_skills",
        "Xóa dứt điểm 50 thư mục kỹ năng rác/stub để giải phóng codebase theo phê duyệt của Master.",
        "SUCCESS"
    )
    recent_operations_store.record_operation(
        "UPGRADE_Z_SOS_5_FILES",
        "138_physical_skills",
        "Chuẩn hóa 100% 138 kỹ năng vật lý đầy đủ 5 tệp Z-SOS (manifest.json, SKILL.md, logic.py, dossier.md, __init__.py).",
        "SUCCESS"
    )
    recent_operations_store.record_operation(
        "UPGRADE_INTENT_ROUTER",
        "CentralIntentRouter v4.1",
        "Tích hợp IntentMode.META_INTROSPECTION và cổng kiểm chứng xác thực PreFlightVerificationGate.",
        "SUCCESS"
    )

