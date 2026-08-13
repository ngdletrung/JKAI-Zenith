"""
core/os/cognition/adaptive_solver/execution_truth_normalizer.py
3-Tier Execution Truth Normalizer & Ground Truth Evaluator.

Enforces:
ToolOutcome -> ArtifactOutcome -> MissionOutcome.
Rejects untyped fake success. A tool can succeed (exit 0) while artifact fails (0 bytes/corrupted).
"""

from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional
from core.os.cognition.adaptive_solver.models import (
    ArtifactOutcome,
    ExecutionTruth,
    MissionOutcome,
    RequirementStatus,
    ToolOutcome,
)
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class ExecutionTruthNormalizer:
    """Normalizes raw execution outputs into the 3-Tier Truth hierarchy."""

    def normalize(
        self,
        invocation_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        raw_result: Any,
        mission: CanonicalMissionSpec,
        execution_time_ms: float = 0.0,
    ) -> ExecutionTruth:
        raw_str = str(raw_result)
        stdout = ""
        stderr = ""
        err_msg = None
        target_path = arguments.get("file_path") or arguments.get("path") or arguments.get("target_file") or arguments.get("filepath")

        # Tier 1: Determine ToolOutcome
        if isinstance(raw_result, dict):
            status_val = str(raw_result.get("status", "")).lower()
            stdout = str(raw_result.get("stdout", raw_result.get("output", "")))
            stderr = str(raw_result.get("stderr", raw_result.get("error", "")))
            if status_val in ["success", "ok", "completed"] and not stderr:
                t_outcome = ToolOutcome.SUCCEEDED
            elif "permission" in stderr.lower() or "denied" in stderr.lower():
                t_outcome = ToolOutcome.PERMISSION_DENIED
                err_msg = stderr
            elif "timeout" in stderr.lower() or "timed out" in stderr.lower():
                t_outcome = ToolOutcome.TIMEOUT
                err_msg = stderr
            else:
                t_outcome = ToolOutcome.FAILED
                err_msg = stderr or "Tool execution error"
        else:
            if "error" in raw_str.lower() or "failed" in raw_str.lower() or "exception" in raw_str.lower():
                t_outcome = ToolOutcome.FAILED
                err_msg = raw_str
            else:
                t_outcome = ToolOutcome.SUCCEEDED
                stdout = raw_str

        # Tier 2: Determine ArtifactOutcome (Physical reality on disk)
        a_outcome = ArtifactOutcome.NONE
        if target_path:
            if os.path.exists(target_path):
                try:
                    size = os.path.getsize(target_path)
                    if size == 0:
                        a_outcome = ArtifactOutcome.CORRUPTED # 0-byte file is invalid/corrupted
                    else:
                        a_outcome = ArtifactOutcome.CREATED
                except Exception:
                    a_outcome = ArtifactOutcome.CORRUPTED
            else:
                a_outcome = ArtifactOutcome.NONE

        # Tier 3: Determine Requirement Verdicts & MissionOutcome
        req_verdicts: Dict[str, RequirementStatus] = {}
        for crit in mission.success_criteria:
            crit_lower = crit.description.lower()
            if "chart" in crit_lower or "biểu đồ" in crit_lower:
                if target_path and target_path.endswith(".xlsx"):
                    has_chart = self._check_excel_chart(target_path)
                    req_verdicts[crit.criterion_id] = RequirementStatus.SATISFIED if has_chart else RequirementStatus.UNSATISFIED
                else:
                    req_verdicts[crit.criterion_id] = RequirementStatus.PENDING
            elif "exist" in crit_lower or "tồn tại" in crit_lower or "file" in crit_lower:
                req_verdicts[crit.criterion_id] = RequirementStatus.SATISFIED if (a_outcome in [ArtifactOutcome.CREATED, ArtifactOutcome.MODIFIED]) else RequirementStatus.UNSATISFIED
            else:
                req_verdicts[crit.criterion_id] = RequirementStatus.SATISFIED if (t_outcome == ToolOutcome.SUCCEEDED and a_outcome != ArtifactOutcome.CORRUPTED) else RequirementStatus.PENDING

        all_reqs_satisfied = all(v == RequirementStatus.SATISFIED for v in req_verdicts.values()) if req_verdicts else False
        is_genuine = (t_outcome == ToolOutcome.SUCCEEDED) and (a_outcome != ArtifactOutcome.CORRUPTED) and all_reqs_satisfied

        if is_genuine:
            m_outcome = MissionOutcome.COMPLETED
        elif t_outcome == ToolOutcome.PERMISSION_DENIED:
            m_outcome = MissionOutcome.SAFE_STOP
        elif a_outcome == ArtifactOutcome.CORRUPTED or any(v == RequirementStatus.UNSATISFIED for v in req_verdicts.values()):
            m_outcome = MissionOutcome.RECOVERY
        else:
            m_outcome = MissionOutcome.RECOVERY

        diagnostic = ""
        if not is_genuine:
            failed_reqs = [k for k, v in req_verdicts.items() if v == RequirementStatus.UNSATISFIED]
            if a_outcome == ArtifactOutcome.CORRUPTED:
                diagnostic = f"ARTIFACT_CORRUPTED: File '{target_path}' has 0 bytes on storage."
            elif failed_reqs:
                diagnostic = f"REQUIREMENT_UNSATISFIED: Criteria {failed_reqs} failed physical verification."
            elif t_outcome != ToolOutcome.SUCCEEDED:
                diagnostic = f"TOOL_FAILED: {err_msg}"

        return ExecutionTruth(
            invocation_id=invocation_id,
            tool_name=tool_name,
            arguments=arguments,
            tool_outcome=t_outcome,
            artifact_outcome=a_outcome,
            mission_outcome=m_outcome,
            artifact_path=target_path,
            stdout=stdout,
            stderr=stderr,
            error_message=err_msg,
            execution_time_ms=execution_time_ms,
            requirement_verdicts=req_verdicts,
            is_genuine_success=is_genuine,
            diagnostic_details=diagnostic,
            timestamp=time.time()
        )

    def _check_excel_chart(self, xlsx_path: str) -> bool:
        """Inspects openpyxl workbook structure for embedded charts."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path, data_only=True)
            for sheet in wb.worksheets:
                if len(sheet._charts) > 0:
                    return True
            return False
        except Exception:
            return False


execution_truth_normalizer = ExecutionTruthNormalizer()
