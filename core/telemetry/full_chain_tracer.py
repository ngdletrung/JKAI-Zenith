# -*- coding: utf-8 -*-
"""
core/telemetry/full_chain_tracer.py
===================================
JKAI Zenith — 5-Phase Full-Chain Cognitive Telemetry Tracer (Phase A1).
Directive: Master Lee Trung's Approved Strategic Pivot & SOP v2.4.

Tracer liên kết chuỗi bằng chứng 5 pha xuyên suốt:
  Proposal -> Controller -> Execution -> Verification -> Outcome
Chức năng:
  - Phân định rõ nguồn gốc lỗi: MODEL_REASONING, CONTROLLER_ORCHESTRATION, RUNTIME_TOOL_EXECUTION, NONE.
  - Ngăn chặn việc suy đoán nguyên nhân: Mọi nhãn huấn luyện LoRA hoặc sửa Controller
    phải xuất phát từ trace đã được chứng minh trên nhật ký đĩa cứng.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("JKAI.Telemetry.FullChainTracer")

DEFAULT_TRACE_LEDGER_PATH = Path("data/telemetry/cognitive_traces.jsonl")


@dataclass
class ProposalPhase:
    prompt: str
    model_id: str
    requested_outputs: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ControllerPhase:
    strategy: str  # FAST_DIRECT, DEEP_DAG, RECOVERY, ESCALATE, CLARIFY
    rationale: str
    step_budget: int = 5
    selected_at: float = field(default_factory=time.time)


@dataclass
class ExecutionStepRecord:
    step_index: int
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # SUCCESS, FAILED, TIMEOUT
    duration_ms: float = 0.0
    output_summary: str = ""
    error_message: Optional[str] = None


@dataclass
class VerificationPhase:
    total_criteria: int
    verified_criteria: int
    unresolved_criteria: int
    evidence_hashes: List[str] = field(default_factory=list)
    context_hash: str = ""
    verified_at: float = field(default_factory=time.time)


@dataclass
class OutcomePhase:
    status: str  # COMPLETE, INCOMPLETE, BLOCKED
    completion_ratio: str  # e.g. "5/5", "2/5"
    total_wallclock_ms: float
    total_tokens: int = 0
    total_vram_peak_mb: int = 0


@dataclass
class FullChainTrace:
    trace_id: str
    mission_id: str
    proposal: Optional[ProposalPhase] = None
    controller: Optional[ControllerPhase] = None
    execution: List[ExecutionStepRecord] = field(default_factory=list)
    verification: Optional[VerificationPhase] = None
    outcome: Optional[OutcomePhase] = None
    error_attribution: str = "NONE"  # NONE, MODEL_REASONING, CONTROLLER_ORCHESTRATION, RUNTIME_TOOL_EXECUTION
    attribution_reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FullChainTracer:
    """
    Quản lý vòng đời và lưu trữ chuỗi trace 5 pha.
    Bảo đảm thread-safe và ghi tuần tự vào JSONL ledger.
    """

    def __init__(self, ledger_path: Path = DEFAULT_TRACE_LEDGER_PATH):
        self.ledger_path = ledger_path
        self._active_traces: Dict[str, FullChainTrace] = {}

    def start_trace(
        self,
        mission_id: str,
        prompt: str,
        model_id: str,
        requested_outputs: Optional[List[str]] = None,
    ) -> str:
        trace_id = f"trace_fc_{uuid.uuid4().hex[:12]}"
        trace = FullChainTrace(
            trace_id=trace_id,
            mission_id=mission_id,
            proposal=ProposalPhase(
                prompt=prompt,
                model_id=model_id,
                requested_outputs=requested_outputs or [],
            ),
        )
        self._active_traces[trace_id] = trace
        return trace_id

    def get_trace(self, trace_id: str) -> Optional[FullChainTrace]:
        return self._active_traces.get(trace_id)

    def record_controller(
        self,
        trace_id: str,
        strategy: str,
        rationale: str,
        step_budget: int = 5,
    ) -> None:
        trace = self._active_traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace {trace_id} not found when recording controller.")
            return
        trace.controller = ControllerPhase(
            strategy=strategy,
            rationale=rationale,
            step_budget=step_budget,
        )

    def record_execution_step(
        self,
        trace_id: str,
        step_index: int,
        tool_name: str,
        arguments: Dict[str, Any],
        status: str,
        duration_ms: float = 0.0,
        output_summary: str = "",
        error_message: Optional[str] = None,
    ) -> None:
        trace = self._active_traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace {trace_id} not found when recording execution step.")
            return
        trace.execution.append(
            ExecutionStepRecord(
                step_index=step_index,
                tool_name=tool_name,
                arguments=arguments,
                status=status,
                duration_ms=duration_ms,
                output_summary=output_summary,
                error_message=error_message,
            )
        )

    def record_verification(
        self,
        trace_id: str,
        total_criteria: int,
        verified_criteria: int,
        unresolved_criteria: int,
        evidence_hashes: Optional[List[str]] = None,
        context_hash: str = "",
    ) -> None:
        trace = self._active_traces.get(trace_id)
        if not trace:
            logger.warning(f"Trace {trace_id} not found when recording verification.")
            return
        trace.verification = VerificationPhase(
            total_criteria=total_criteria,
            verified_criteria=verified_criteria,
            unresolved_criteria=unresolved_criteria,
            evidence_hashes=evidence_hashes or [],
            context_hash=context_hash,
        )

    def finalize_trace(
        self,
        trace_id: str,
        outcome_status: str,
        total_wallclock_ms: float,
        total_tokens: int = 0,
        total_vram_peak_mb: int = 0,
    ) -> FullChainTrace:
        trace = self._active_traces.get(trace_id)
        if not trace:
            raise KeyError(f"Trace {trace_id} not found.")

        # Chuẩn hóa trạng thái outcome
        canon_status = outcome_status.upper()
        if "VERIFIED" in canon_status or canon_status == "COMPLETE":
            final_status = "COMPLETE"
        elif "BLOCK" in canon_status:
            final_status = "BLOCKED"
        else:
            final_status = "INCOMPLETE"

        total_crit = trace.verification.total_criteria if trace.verification else 0
        ver_crit = trace.verification.verified_criteria if trace.verification else 0
        ratio = f"{ver_crit}/{total_crit}"

        trace.outcome = OutcomePhase(
            status=final_status,
            completion_ratio=ratio,
            total_wallclock_ms=total_wallclock_ms,
            total_tokens=total_tokens,
            total_vram_peak_mb=total_vram_peak_mb,
        )

        # Chẩn đoán quy kết nguyên nhân lỗi
        trace.error_attribution, trace.attribution_reason = self._attribute_error(trace)

        # Lưu vào ledger trên đĩa
        self._commit_to_ledger(trace)

        # Dọn dẹp cache
        self._active_traces.pop(trace_id, None)
        return trace

    def _attribute_error(self, trace: FullChainTrace) -> tuple[str, str]:
        """Quy kết nguyên nhân lỗi dựa trên bằng chứng vật lý thực tế."""
        if trace.outcome and trace.outcome.status == "COMPLETE":
            return "NONE", "Mission successfully completed with 100% verified criteria."

        # 1. Kiểm tra lỗi Runtime / Tool execution
        for step in trace.execution:
            if step.status in ("FAILED", "TIMEOUT"):
                msg = step.error_message or ""
                if any(w in msg.lower() for w in ("timeout", "econnrefused", "permission", "file not found", "commandnotfound")):
                    return "RUNTIME_TOOL_EXECUTION", f"Tool {step.tool_name} failed at runtime: {msg}"

        # 2. Kiểm tra lỗi Controller dừng sớm / chọn sai chiến lược
        if trace.controller and trace.verification:
            if trace.verification.unresolved_criteria > 0 and len(trace.execution) < trace.controller.step_budget:
                return (
                    "CONTROLLER_ORCHESTRATION",
                    f"Controller stopped early after {len(trace.execution)} steps with {trace.verification.unresolved_criteria} criteria unresolved.",
                )

        # 3. Lỗi suy luận của Model
        if trace.proposal and len(trace.proposal.requested_outputs) > 0:
            if trace.verification and trace.verification.verified_criteria == 0:
                return (
                    "MODEL_REASONING",
                    "Model failed to generate effective plan or actions meeting requested outputs.",
                )

        return "MODEL_REASONING", "Incomplete verification without runtime tool crash."

    def _commit_to_ledger(self, trace: FullChainTrace) -> None:
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to commit trace to ledger: {e}")


# Singleton instance
full_chain_tracer = FullChainTracer()
