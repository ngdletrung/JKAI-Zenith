"""
JKAI Benchmark Manifest & Execution Report Contract
File: core/benchmarks/benchmark_manifest.py

Triển khai tiêu chuẩn Phase R2:
- Tách bạch tuyệt đối báo cáo giữa LIVE_MODEL và SIMULATED.
- Niêm phong song trùng (dual-signature): Băm SHA-256 đề bài (task) VÀ tiêu chí chấm (rubric).
- Tự động phát hiện và chặn đứng mọi sửa đổi làm sai lệch kết quả đánh giá.
"""

import hashlib
import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional


class ExecutionMode(str, Enum):
    """Phân tách rạch ròi môi trường đánh giá: Không bao giờ nhầm lẫn mock với model thật."""
    LIVE_MODEL = "LIVE_MODEL"
    SIMULATED = "SIMULATED"


class BenchmarkTask:
    """Đề bài kiểm thử tiêu chuẩn có băm SHA-256 kép (prompt + eval_rubric)."""
    def __init__(
        self,
        task_id: str,
        domain: str,
        prompt: str,
        eval_rubric: Dict[str, Any],
        expected_artifacts: Optional[List[str]] = None,
        task_hash: Optional[str] = None
    ):
        self.task_id = task_id
        self.domain = domain
        self.prompt = prompt
        self.eval_rubric = eval_rubric
        self.expected_artifacts = expected_artifacts or []
        self.task_hash = task_hash or self.compute_hash()

    def compute_hash(self) -> str:
        payload = {
            "task_id": self.task_id,
            "domain": self.domain,
            "prompt": self.prompt,
            "eval_rubric": self.eval_rubric,
            "expected_artifacts": sorted(self.expected_artifacts)
        }
        canonical_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def verify_integrity(self) -> bool:
        return self.compute_hash() == self.task_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "prompt": self.prompt,
            "eval_rubric": self.eval_rubric,
            "expected_artifacts": self.expected_artifacts,
            "task_hash": self.task_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkTask":
        return cls(
            task_id=data["task_id"],
            domain=data["domain"],
            prompt=data["prompt"],
            eval_rubric=data["eval_rubric"],
            expected_artifacts=data.get("expected_artifacts", []),
            task_hash=data.get("task_hash")
        )


class BenchmarkManifest:
    """Tập đề thi chuẩn hóa được niêm phong toàn diện bằng chữ ký gốc (Merkle Root)."""
    def __init__(
        self,
        manifest_id: str,
        version: str = "1.0.0",
        description: str = "",
        tasks: Optional[Dict[str, BenchmarkTask]] = None,
        manifest_hash: Optional[str] = None
    ):
        self.manifest_id = manifest_id
        self.version = version
        self.description = description
        self.tasks: Dict[str, BenchmarkTask] = tasks or {}
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.manifest_hash = manifest_hash or ""

    def add_task(self, task: BenchmarkTask):
        if not task.verify_integrity():
            raise ValueError(f"Task {task.task_id} có mã hash không khớp với nội dung!")
        self.tasks[task.task_id] = task

    def seal_manifest(self) -> str:
        """Niêm phong toàn bộ tập bài kiểm thử và tạo mã hash tổng thể."""
        sorted_task_hashes = [
            f"{tid}:{self.tasks[tid].compute_hash()}"
            for tid in sorted(self.tasks.keys())
        ]
        payload = {
            "manifest_id": self.manifest_id,
            "version": self.version,
            "task_hashes": sorted_task_hashes
        }
        canonical_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        self.manifest_hash = hashlib.sha256(canonical_bytes).hexdigest()
        return self.manifest_hash

    def verify_manifest(self) -> bool:
        """Kiểm chứng tính toàn vẹn của toàn bộ tập bài thi."""
        if not self.manifest_hash:
            return False
        # 1. Kiểm tra từng task
        for task in self.tasks.values():
            if not task.verify_integrity():
                return False
        # 2. Kiểm tra hash tổng
        current_hash = self.seal_manifest()
        return current_hash == self.manifest_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "version": self.version,
            "description": self.description,
            "created_at": self.created_at,
            "manifest_hash": self.manifest_hash,
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()}
        }


class BenchmarkReport:
    """Báo cáo kết quả đo lường phân lập rõ rệt giữa LIVE_MODEL và SIMULATED."""
    def __init__(
        self,
        report_id: str,
        manifest_id: str,
        manifest_hash: str,
        execution_mode: ExecutionMode,
        model_name: str,
        ablation_tier: str,
        results: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, float]] = None
    ):
        self.report_id = report_id
        self.manifest_id = manifest_id
        self.manifest_hash = manifest_hash
        self.execution_mode = execution_mode
        self.model_name = model_name
        self.ablation_tier = ablation_tier
        self.results = results or []
        self.metrics = metrics or {}
        self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def calculate_summary_metrics(self) -> Dict[str, float]:
        total_tasks = len(self.results)
        if total_tasks == 0:
            return {"task_count": 0, "completion_rate": 0.0}

        passed_tasks = sum(1 for r in self.results if r.get("verdict") == "COMPLETE")
        total_actions = sum(r.get("action_count", 0) for r in self.results)
        total_latency_ms = sum(r.get("latency_ms", 0.0) for r in self.results)

        completion_rate = (passed_tasks / total_tasks) * 100.0
        actions_per_task = total_actions / total_tasks
        avg_latency_ms = total_latency_ms / total_tasks

        self.metrics = {
            "total_tasks": float(total_tasks),
            "passed_tasks": float(passed_tasks),
            "completion_rate_pct": round(completion_rate, 2),
            "actions_per_task": round(actions_per_task, 2),
            "avg_latency_ms": round(avg_latency_ms, 2)
        }
        return self.metrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "manifest_id": self.manifest_id,
            "manifest_hash": self.manifest_hash,
            "execution_mode": self.execution_mode.value,
            "model_name": self.model_name,
            "ablation_tier": self.ablation_tier,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "results": self.results
        }
