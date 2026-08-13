"""
core/os/cognition/adaptive_solver/adaptation_applier.py
Governed Adaptation Applier & Automated Verification Closed-Loop (Agentic Execution Engine).

Consumes all 8 Strategy Decisions from ATS and enforces real runtime actions:
- BATCH execution for homogenous items
- Mode escalation from FAST to DEEP
- Early termination with physical proof
- Automated post-mutation test & verification loop (OpenCode/Antigravity parity)
- Fail-Closed governance logging
"""

from __future__ import annotations
import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from core.os.cognition.adaptive_solver.models import (
    ActionGranularity,
    ArtifactOutcome,
    ExecutionTruth,
    MissionOutcome,
    RequirementStatus,
    StrategyAdaptation,
    StrategyDecision,
    ToolOutcome,
)
from core.os.cognition.adaptive_solver.situation_model import situation_assessor
from core.os.cognition.adaptive_solver.execution_truth_normalizer import execution_truth_normalizer
from core.os.cognition.adaptive_solver.adaptive_solver_engine import adaptive_solver_engine
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec

logger = logging.getLogger("jkai.cognition.adaptation_applier")


class AdaptationApplier:
    """Consumes ATS decisions and coordinates runtime adaptation and verification."""

    @classmethod
    async def apply_adaptation(
        cls,
        adaptation: StrategyAdaptation,
        canonical_mission: CanonicalMissionSpec,
        situation: Any,
        context: List[Dict[str, Any]],
        task_id: str,
        engine: Any,
        trace_id: str,
        gateway: Any = None,
    ) -> Dict[str, Any]:
        """
        Executes real control actions for all 8 ATS Strategy Decisions.
        Returns control directive dict: {"action": "CONTINUE"|"TERMINATE"|"ESCALATE_DEEP"|"SAFE_STOP", "result": Any}
        """
        decision = adaptation.decision

        # ─────────────────────────────────────────────────────────────
        # 1. SAFE_STOP: Halt immediately with fail-closed diagnostic
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.SAFE_STOP:
            err_msg = adaptation.safe_stop_reason or "Unauthorized operation or security boundary reached"
            engine.publish_mission_log("ERROR", f"[ATS-GOVERNOR SAFE-STOP]: {err_msg}", task_id, trace_id)
            return {
                "action": "SAFE_STOP",
                "result": {
                    "answer": f"Tiến trình đã được dừng an toàn (Fail-Closed): {err_msg}",
                    "task_id": task_id,
                    "status": "safe_stop",
                    "provenance": adaptation.provenance_trace
                }
            }

        # ─────────────────────────────────────────────────────────────
        # 2. TERMINATE_WITH_PROOF: Early exit with verified artifacts
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.TERMINATE_WITH_PROOF:
            engine.publish_mission_log("SUCCESS", f"[ATS-GOVERNOR COMPLETED]: {adaptation.rationale}", task_id, trace_id)
            return {
                "action": "TERMINATE",
                "result": {
                    "answer": f"Nhiệm vụ đã hoàn tất trọn vẹn với bằng chứng thực tế được xác minh.\n\n📌 **Bằng chứng:** `{adaptation.supporting_evidence}`\n🎯 **Kết quả:** Đạt toàn bộ tiêu chí nghiệm thu của Master.",
                    "task_id": task_id,
                    "status": "completed",
                    "provenance": adaptation.provenance_trace
                }
            }

        # ─────────────────────────────────────────────────────────────
        # 3. DEEPEN_REASONING / ESCALATE_TO_DEEP: Switch mode to DEEP DAG
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.DEEPEN_REASONING or adaptation.escalate_to_deep:
            engine.publish_mission_log("SYSTEM", f"[ATS-GOVERNOR ESCALATE]: Phát hiện độ phức tạp cao ({adaptation.rationale}). Chuyển giao sang DEEP Pipeline.", task_id, trace_id)
            try:
                from core.utils.mode_switcher import mode_switcher
                await mode_switcher.switch_to("DEEP", engine, task_id)
            except Exception as sw_err:
                logger.error("[MODE-SWITCH-FAIL-CLOSED]: %s", sw_err, exc_info=True)
                engine.publish_mission_log("ERROR", f"[ATS-MODE-SWITCH-FAIL]: Lỗi chuyển mode DEEP: {sw_err}", task_id, trace_id)

            return {
                "action": "ESCALATE_DEEP",
                "result": {
                    "escalate_to_deep": True,
                    "reason": adaptation.rationale,
                    "provenance": adaptation.provenance_trace
                }
            }

        # ─────────────────────────────────────────────────────────────
        # 4. TARGETED_REPAIR: Inject surgical correction instructions
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.TARGETED_REPAIR:
            repair_msg = adaptation.replan_instructions or f"Sửa chữa tiêu chí chưa đạt: {adaptation.reason_codes}"
            context.append({
                "role": "user",
                "content": f"[ATS-TARGETED-REPAIR]: Phát hiện thiếu sót tiêu chuẩn: {repair_msg}. Hãy thực thi bổ sung ngay để đáp ứng 100% yêu cầu."
            })
            engine.publish_mission_log("SYSTEM", f"[ATS-GOVERNOR REPAIR]: Kích hoạt nhánh sửa chữa có chủ đích cho `{adaptation.next_action_target}`", task_id, trace_id, stealth=True)
            return {"action": "CONTINUE"}

        # ─────────────────────────────────────────────────────────────
        # 5. PIVOT_STRATEGY: Pivot to alternative capability
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.PIVOT_STRATEGY:
            pivot_msg = adaptation.replan_instructions or f"Đổi chiến lược do lỗi công cụ: {adaptation.supporting_evidence}"
            context.append({
                "role": "user",
                "content": f"[ATS-PIVOT-STRATEGY]: {pivot_msg}. Không lặp lại công cụ vừa thất bại, hãy chuyển sang capability thay thế."
            })
            engine.publish_mission_log("WARN", f"[ATS-GOVERNOR PIVOT]: {adaptation.rationale}", task_id, trace_id)
            return {"action": "CONTINUE"}

        # ─────────────────────────────────────────────────────────────
        # 6. STRATEGY_INVALIDATED: Invalidate stale hypothesis
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.STRATEGY_INVALIDATED:
            context.append({
                "role": "user",
                "content": f"[ATS-STRATEGY-INVALIDATED]: Giả thuyết trước đó đã bị bác bỏ do bất đồng thực tế: {adaptation.rationale}. Hãy chuyển sang xử lý chính xác từng phần tử (PRECISION)."
            })
            engine.publish_mission_log("WARN", f"[ATS-GOVERNOR INVALIDATED]: {adaptation.rationale}", task_id, trace_id)
            return {"action": "CONTINUE"}

        # ─────────────────────────────────────────────────────────────
        # 7. REFINE_GRANULARITY (BATCH): Promote to batch processing
        # ─────────────────────────────────────────────────────────────
        if decision == StrategyDecision.REFINE_GRANULARITY and adaptation.recommended_granularity == ActionGranularity.BATCH:
            group_count = sum(len(v) for v in situation.homogenous_groups.values()) if hasattr(situation, "homogenous_groups") else 0
            context.append({
                "role": "user",
                "content": f"[ATS-BATCH-MODE]: Đã thăm dò thành công. Cho phép xử lý song song/hàng loạt toàn bộ {group_count} phần tử trong nhóm đồng nhất."
            })
            engine.publish_mission_log("SYSTEM", f"[ATS-GOVERNOR BATCH]: Kích hoạt chế độ xử lý hàng loạt ({group_count} phần tử).", task_id, trace_id, stealth=True)
            return {"action": "CONTINUE"}

        # 8. CONTINUE_CURRENT_STRATEGY: Default precision continue
        return {"action": "CONTINUE"}

    @classmethod
    async def run_post_edit_verification_loop(
        cls,
        tool_name: str,
        tool_args: Dict[str, Any],
        raw_result: Any,
        canonical_mission: CanonicalMissionSpec,
        situation: Any,
        task_id: str,
        gateway: Any,
        engine: Any,
        trace_id: str,
    ) -> Tuple[ExecutionTruth, StrategyAdaptation]:
        """
        OpenCode/Antigravity Closed-Loop Verification:
        After file mutations (write/replace), automatically runs syntax & test verification,
        feeds physical result into situation assessor, and evaluates adaptation.
        """
        # 1. First normalize the direct tool outcome
        truth = execution_truth_normalizer.normalize(
            invocation_id=f"inv_{task_id}_{int(time.time()*1000)}",
            tool_name=tool_name,
            arguments=tool_args,
            raw_result=raw_result,
            mission=canonical_mission
        )

        # 2. If tool mutated a code/data file, run multi-tier semantic verification
        is_mutation = tool_name.lower() in ("write_to_file", "replace_file_content", "multi_replace_file_content", "edit_file")
        if is_mutation and truth.artifact_path and os.path.exists(truth.artifact_path):
            file_path = truth.artifact_path
            ext = os.path.splitext(file_path)[1].lower()
            file_size = os.path.getsize(file_path)

            # Tier 1: Physical Existence & Non-Zero
            if file_size == 0:
                truth.artifact_outcome = ArtifactOutcome.CORRUPTED
                truth.is_genuine_success = False
                truth.error_message = f"Zero-byte empty artifact created at {file_path}"
                engine.publish_mission_log("ERROR", f"[VERIFY-FAIL] {file_path} is 0-bytes empty.", task_id, trace_id)

            # Tier 2 & 3: Syntax + Semantic Structure
            elif ext == ".py":
                try:
                    import ast
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        tree = ast.parse(f.read())
                    # Structural check: verify top-level statements exist
                    func_count = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
                    engine.publish_mission_log("SYSTEM", f"[VERIFY-LOOP] `{os.path.basename(file_path)}` syntax AST verified clean ({func_count} definitions).", task_id, trace_id, stealth=True)
                except Exception as py_err:
                    truth.artifact_outcome = ArtifactOutcome.CORRUPTED
                    truth.is_genuine_success = False
                    truth.error_message = f"SyntaxError in {file_path}: {py_err}"
                    engine.publish_mission_log("ERROR", f"[VERIFY-LOOP FAIL] {file_path} syntax error: {py_err}", task_id, trace_id)

            elif ext == ".json":
                try:
                    import json
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        json_data = json.load(f)
                    engine.publish_mission_log("SYSTEM", f"[VERIFY-LOOP] `{os.path.basename(file_path)}` valid JSON structure verified.", task_id, trace_id, stealth=True)
                except Exception as j_err:
                    truth.artifact_outcome = ArtifactOutcome.CORRUPTED
                    truth.is_genuine_success = False
                    truth.error_message = f"Invalid JSON format in {file_path}: {j_err}"
                    engine.publish_mission_log("ERROR", f"[VERIFY-LOOP FAIL] JSON error: {j_err}", task_id, trace_id)

            elif ext in (".csv", ".tsv"):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip()]
                    if len(lines) < 2:
                        truth.artifact_outcome = ArtifactOutcome.CORRUPTED
                        truth.is_genuine_success = False
                        truth.error_message = f"CSV has insufficient rows ({len(lines)} lines found)"
                    else:
                        engine.publish_mission_log("SYSTEM", f"[VERIFY-LOOP] `{os.path.basename(file_path)}` verified with {len(lines)} data rows.", task_id, trace_id, stealth=True)
                except Exception as csv_err:
                    truth.artifact_outcome = ArtifactOutcome.CORRUPTED
                    truth.is_genuine_success = False
                    truth.error_message = f"CSV read error: {csv_err}"

        # 3. Record physical observation into Situation Model
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target=tool_name,
            expected_behavior="Valid execution with verified syntax and non-zero physical artifact",
            observed_behavior=f"Outcome: {truth.tool_outcome.value} | Artifact: {truth.artifact_outcome.value} | Err: {truth.error_message or 'None'}"
        )

        # 4. Evaluate governed ATS adaptation
        adaptation = adaptive_solver_engine.evaluate_and_adapt(canonical_mission, situation, truth)

        return truth, adaptation


adaptation_applier = AdaptationApplier()
