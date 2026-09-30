"""
🏛️ JKAI Zenith — Stage-Tagged Failure Logging Module
File: core/os/observability/stage_failure_tagger.py
Purpose: Chốt chặn 1 theo chỉ đạo Master & Opencode: Ghi nhận chính xác kết quả và
         chủ thể sở hữu (owner) cho từng stage trong vòng đời nhiệm vụ.
"""

import time
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("JKAI.StageFailureTagger")


class StageName(str, Enum):
    INGRESS = "INGRESS"
    INTENT = "INTENT"
    ROUTING = "ROUTING"
    CONTEXT = "CONTEXT"
    MODEL = "MODEL"
    DECISION = "DECISION"
    AUTHORITY = "AUTHORITY"
    TOOL = "TOOL"
    MUTATION = "MUTATION"
    OBSERVATION = "OBSERVATION"
    VERIFICATION = "VERIFICATION"
    COMPLETION = "COMPLETION"


class StageOwner(str, Enum):
    RUNTIME = "RUNTIME"
    CONTROLLER = "CONTROLLER"
    ROUTER = "ROUTER"
    RAG = "RAG"
    MODEL = "MODEL"
    POLICY_KERNEL = "POLICY_KERNEL"
    EXECUTOR = "EXECUTOR"
    VERIFIER = "VERIFIER"


class StageOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


# Ánh xạ mặc định stage -> owner chuẩn mực theo kiến trúc
DEFAULT_STAGE_OWNERS: Dict[StageName, StageOwner] = {
    StageName.INGRESS: StageOwner.RUNTIME,
    StageName.INTENT: StageOwner.CONTROLLER,
    StageName.ROUTING: StageOwner.ROUTER,
    StageName.CONTEXT: StageOwner.RAG,
    StageName.MODEL: StageOwner.MODEL,
    StageName.DECISION: StageOwner.CONTROLLER,
    StageName.AUTHORITY: StageOwner.POLICY_KERNEL,
    StageName.TOOL: StageOwner.EXECUTOR,
    StageName.MUTATION: StageOwner.EXECUTOR,
    StageName.OBSERVATION: StageOwner.RUNTIME,
    StageName.VERIFICATION: StageOwner.VERIFIER,
    StageName.COMPLETION: StageOwner.RUNTIME,
}


@dataclass
class StageRecord:
    stage: str
    owner: str
    outcome: str
    error_code: Optional[str] = None
    latency_ms: float = 0.0
    detail: Optional[str] = None
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class StageFailureTagger:
    """
    Quản lý thu thập, gắn nhãn owner và kết xuất thống kê lỗi theo stage.
    """

    def __init__(self):
        self._in_memory_logs: Dict[str, List[StageRecord]] = {}

    def record_stage(
        self,
        task_id: str,
        stage: StageName,
        outcome: StageOutcome,
        owner: Optional[StageOwner] = None,
        error_code: Optional[str] = None,
        latency_ms: float = 0.0,
        detail: Optional[str] = None,
    ) -> StageRecord:
        """Ghi nhận vết thực thi có cấu trúc cho 1 stage."""
        resolved_owner = owner or DEFAULT_STAGE_OWNERS.get(stage, StageOwner.RUNTIME)
        record = StageRecord(
            stage=stage.value if hasattr(stage, "value") else str(stage),
            owner=resolved_owner.value if hasattr(resolved_owner, "value") else str(resolved_owner),
            outcome=outcome.value if hasattr(outcome, "value") else str(outcome),
            error_code=error_code,
            latency_ms=round(latency_ms, 2),
            detail=detail,
            timestamp=time.time(),
        )

        if task_id not in self._in_memory_logs:
            self._in_memory_logs[task_id] = []
        self._in_memory_logs[task_id].append(record)

        # Lưu trữ an toàn vào Redis nếu có kết nối
        try:
            from core.redis_client import redis_safe
            r_key = f"telemetry:stage_log:{task_id}"
            redis_safe(lambda r: r.rpush(r_key, json.dumps(record.to_dict())))
            redis_safe(lambda r: r.expire(r_key, 86400))
        except Exception:
            pass

        if outcome == StageOutcome.FAIL:
            logger.warning(
                f"[STAGE-FAIL] Task={task_id} | Stage={record.stage} | Owner={record.owner} | Error={error_code} | Latency={latency_ms}ms"
            )
        return record

    def get_task_records(self, task_id: str) -> List[StageRecord]:
        """Truy xuất toàn bộ danh sách records của một task."""
        if task_id in self._in_memory_logs:
            return self._in_memory_logs[task_id]
        
        # Thử lấy từ Redis
        try:
            from core.redis_client import redis_safe
            r_key = f"telemetry:stage_log:{task_id}"
            raw_list = redis_safe(lambda r: r.lrange(r_key, 0, -1))
            if raw_list:
                records = []
                for item in raw_list:
                    data = json.loads(item)
                    records.append(StageRecord(**data))
                return records
        except Exception:
            pass
        return []

    def get_failure_distribution(self, task_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Tổng hợp tỷ lệ phân bố lỗi theo từng Owner:
        Returns: {
            "total_failures": int,
            "owner_counts": {Owner: count},
            "owner_percentages": {Owner: percentage},
            "model_failure_percentage": float
        }
        """
        all_records: List[StageRecord] = []
        target_ids = task_ids or list(self._in_memory_logs.keys())

        for tid in target_ids:
            all_records.extend(self.get_task_records(tid))

        failures = [r for r in all_records if r.outcome == StageOutcome.FAIL.value]
        total_failures = len(failures)

        owner_counts: Dict[str, int] = {}
        for f in failures:
            owner_counts[f.owner] = owner_counts.get(f.owner, 0) + 1

        owner_pct: Dict[str, float] = {}
        for owner, count in owner_counts.items():
            owner_pct[owner] = round((count / total_failures * 100), 2) if total_failures > 0 else 0.0

        model_fail_pct = owner_pct.get(StageOwner.MODEL.value, 0.0)

        return {
            "total_failures": total_failures,
            "owner_counts": owner_counts,
            "owner_percentages": owner_pct,
            "model_failure_percentage": model_fail_pct,
            "should_trigger_labeling": model_fail_pct >= 30.0,
        }


# Singleton instance
stage_failure_tagger = StageFailureTagger()
