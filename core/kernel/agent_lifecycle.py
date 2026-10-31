"""
core/kernel/agent_lifecycle.py
==============================
Hệ thống Lifecycle Interceptors / Hooks theo kiến trúc Finite State Machine (FSM)
lấy cảm hứng từ DeepSeek-Harness và Meta CCA.

Tách rời hoàn toàn các quy tắc kiểm soát biên (Action Validation, Circuit Breaker,
Transaction Snapshot & Rollback, Coverage Tracking, Pre-Submission Reflexion)
ra khỏi lõi vòng lặp Agent Loop, triệt tiêu mã nguồn Spaghetti Monolith.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("jkai.agent_lifecycle")


@dataclass
class StepContext:
    """Bối cảnh trạng thái tại mỗi bước của vòng lặp Agent Loop."""
    task_id: str
    goal: str
    mode: str  # 'audit' hoặc 'fix'
    step: int
    max_steps: int
    messages: List[Dict[str, Any]]
    trace_id: str = "sys"
    scope_rel: str = ""
    last_obs: str = ""
    touched_files: List[str] = field(default_factory=list)
    viewed_files: Set[str] = field(default_factory=set)
    has_successful_view_file: bool = False
    guard_blocked_count: int = 0
    coverage_ledger: Any = None
    budget: Any = None
    tx_manager: Any = None
    active_tx_target: Optional[str] = None
    should_stop: bool = False
    stop_result: Optional[str] = None


@dataclass
class ToolInvocationContext:
    """Bối cảnh khi đặc vụ quyết định gọi một công cụ."""
    tool: str
    params: Dict[str, Any]
    thought: str = ""
    is_intercepted: bool = False
    interception_observation: Optional[str] = None
    is_idempotent_skip: bool = False


@dataclass
class ToolResultContext:
    """Bối cảnh sau khi công cụ được thực thi."""
    tool: str
    params: Dict[str, Any]
    raw_output: str
    processed_output: str
    outcome_ok: bool = True
    should_repeat_nudge: bool = False


class AgentLifecycleHook(ABC):
    """Lớp cơ sở trừu tượng cho tất cả các Lifecycle Hooks."""
    
    async def on_step_start(self, ctx: StepContext) -> None:
        """Kích hoạt ở đầu mỗi bước (Chuẩn bị bối cảnh, cắt tỉa token)."""
        pass

    async def before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        """Kích hoạt trước khi công cụ được thực thi (Policy Gate, Circuit Breaker, Transaction Begin)."""
        pass

    async def after_tool_executed(
        self, step_ctx: StepContext, result_ctx: ToolResultContext
    ) -> None:
        """Kích hoạt sau khi công cụ thực thi xong (Transaction Verify/Rollback, Working Memory Eviction, CoverageLedger)."""
        pass

    async def before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Kích hoạt khi Agent chuẩn bị xuất final_answer.
        Trả về: (is_approved, rejection_observation_if_any)
        """
        return True, None


class LifecycleManager:
    """Bộ điều phối toàn bộ Lifecycle Hooks theo thứ tự ưu tiên."""
    
    def __init__(self, hooks: Optional[List[AgentLifecycleHook]] = None):
        self.hooks: List[AgentLifecycleHook] = hooks or []

    def register_hook(self, hook: AgentLifecycleHook) -> None:
        self.hooks.append(hook)

    async def run_on_step_start(self, ctx: StepContext) -> None:
        for hook in self.hooks:
            await hook.on_step_start(ctx)

    async def run_before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        for hook in self.hooks:
            await hook.before_tool_dispatch(step_ctx, tool_ctx)
            if tool_ctx.is_intercepted:
                break

    async def run_after_tool_executed(
        self, step_ctx: StepContext, result_ctx: ToolResultContext
    ) -> None:
        for hook in self.hooks:
            await hook.after_tool_executed(step_ctx, result_ctx)

    async def run_before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        for hook in self.hooks:
            approved, rejection_msg = await hook.before_submission(step_ctx, thought, final_answer)
            if not approved:
                return False, rejection_msg
        return True, None


# ==============================================================================
# CÁC INTERCEPTOR CHUYÊN BIỆT (SPECIALIZED HOOKS)
# ==============================================================================

class StepPreparationHook(AgentLifecycleHook):
    """Quản lý bối cảnh & Cắt tỉa ngữ cảnh bảo vệ Token Budget ở đầu mỗi bước."""

    async def on_step_start(self, ctx: StepContext) -> None:
        from core.kernel.context_manager import context_manager
        ctx.messages = context_manager.prune_messages(ctx.messages, session_id=ctx.task_id)


class ActionValidationHook(AgentLifecycleHook):
    """Xác thực định dạng công cụ và tham số tại biên trước khi điều phối."""

    def __init__(self, known_tools: Set[str]):
        self.known_tools = known_tools

    async def before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        from core.kernel.action_validator import validate_action, ActionDecision

        verdict = validate_action(tool_ctx.tool, tool_ctx.params, known_tools=self.known_tools)
        if verdict.decision in (ActionDecision.UNKNOWN_TOOL, ActionDecision.SCHEMA_INVALID):
            tool_ctx.is_intercepted = True
            tool_ctx.interception_observation = (
                f"[OBSERVATION]\n🚧 Action không hợp lệ: {verdict.reason}\n"
                f"Các tool hợp lệ: {', '.join(sorted(self.known_tools))}\n"
                "Hãy phát hành lại JSON với tool hợp lệ và params đúng dạng object."
            )
        elif verdict.normalized_tool:
            tool_ctx.tool = verdict.normalized_tool


class CircuitBreakerHook(AgentLifecycleHook):
    """Chặn dao động lặp vô nghĩa (Circuit Breaker) và cung cấp Recovery Guidance."""

    async def before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        if tool_ctx.is_intercepted:
            return

        budget = step_ctx.budget
        if not budget:
            return

        sig = budget._signature(str(tool_ctx.tool), tool_ctx.params)
        rep_count = budget.history.count(sig)

        if tool_ctx.tool == "view_file" and rep_count >= 2:
            tool_ctx.is_intercepted = True
            step_ctx.guard_blocked_count += 1

            if step_ctx.guard_blocked_count >= 2:
                # Force finalization theo cơ chế RECOVERY-AFTER-GUARD
                cov_ledger = step_ctx.coverage_ledger
                if cov_ledger:
                    cov = cov_ledger.evaluate_coverage()
                    read_files = list(cov_ledger.read_files) if hasattr(cov_ledger, "read_files") else []
                    if read_files:
                        partial = f"PARTIAL_REPORT: Da doc {read_files}. Coverage: {cov.get('coverage_percent', 0)}%"
                    else:
                        partial = "KHONG_THE_DOC_TEP: Guard blocked after repeated oscillation. Using available data."
                else:
                    partial = "KHONG_THE_DOC_TEP: Guard blocked after repeated oscillation. Using available data."
                step_ctx.should_stop = True
                step_ctx.stop_result = partial
                tool_ctx.interception_observation = partial
                return

            # Cung cấp hướng dẫn phục hồi
            cov_complete = False
            missing = []
            if step_ctx.coverage_ledger:
                cov = step_ctx.coverage_ledger.evaluate_coverage()
                cov_complete = step_ctx.coverage_ledger.files_fully_read()
                missing = cov.get("missing_files", [])

            if cov_complete:
                read_str = ", ".join(list(step_ctx.coverage_ledger.read_files))
                tool_ctx.interception_observation = (
                    f"🛑 [CIRCUIT-BREAKER - RECOVERY GUIDE]: Bạn đã đọc xong tất cả các tệp bắt buộc ({read_str}).\n"
                    f"Dữ liệu đã có đầy đủ trong ngữ cảnh. TUYỆT ĐỐI KHÔNG GỌI LẠI 'view_file' NỮA!\n"
                    f"HÀNH ĐỘNG BẮT BUỘC: Hãy trả về câu trả lời cuối cùng ('final_answer') ngay bây giờ để hoàn tất báo cáo kiểm toán, "
                    f"gồm số dòng, mã băm SHA-256, danh sách class/hàm, giải thích cơ chế phối hợp và đính kèm mã Canary."
                )
            elif missing:
                tool_ctx.interception_observation = (
                    f"🛑 [CIRCUIT-BREAKER - RECOVERY GUIDE]: Bạn đã đọc tệp này {rep_count} lần rồi! Không đọc lại nữa.\n"
                    f"HÀNH ĐỘNG BẮT BUỘC: Hãy chuyển sang dùng 'view_file' đọc tệp tiếp theo còn thiếu: `{missing[0]}`."
                )
            else:
                tool_ctx.interception_observation = (
                    f"🛑 [CIRCUIT-BREAKER - RECOVERY GUIDE]: Bạn đã đọc tệp này {rep_count} lần. "
                    f"Hãy dừng gọi tool và xuất 'final_answer' tổng hợp báo cáo kiểm toán ngay lập tức."
                )

        elif tool_ctx.tool == "replace_file_content" and rep_count >= 2:
            tool_ctx.is_intercepted = True
            target_hint = tool_ctx.params.get("TargetContent") or tool_ctx.params.get("target") or ""
            path_hint = tool_ctx.params.get("path") or tool_ctx.params.get("TargetFile") or ""
            tool_ctx.interception_observation = (
                f"🚨 [CIRCUIT-BREAKER TRIP]: Bạn đang lặp lại lệnh replace_file_content với cùng TargetContent '{target_hint}' đã từng thất bại!\n"
                f"LÝ DO: TargetContent bạn đưa ra KHÔNG TỒN TẠI trong tệp `{path_hint}`. Bạn đang đoán mò.\n"
                f"HÀNH ĐỘNG BẮT BUỘC:\n"
                f"1. Dùng 'view_file' xem lại chính xác nội dung tệp `{path_hint}`.\n"
                f"2. Sao chép CHÍNH XÁC từng ký tự của dòng code cần sửa trên đĩa vào TargetContent, không tự bịa mã."
            )

        elif tool_ctx.tool == "query_repo_map" and rep_count >= 2:
            tool_ctx.is_intercepted = True
            tool_ctx.interception_observation = (
                f"🚨 [CIRCUIT-BREAKER TRIP]: Bạn đã gọi query_repo_map {rep_count} lần liên tiếp!\n"
                f"HÀNH ĐỘNG BẮT BUỘC: Không tra cứu repo map nữa. Hãy chuyển ngay sang dùng 'view_file' với 'path' của tệp cần đọc!"
            )


class ScopeLockAndCoverageCompletionHook(AgentLifecycleHook):
    """
    GAP-014: Khóa cứng phạm vi mục tiêu (Strict Scope Lockdown) & Khóa hoàn tất (Completion Lock).
    Triệt tiêu dứt điểm hiện tượng đọc lan man ngoài mục tiêu của mô hình.
    """

    async def before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        if tool_ctx.is_intercepted or step_ctx.mode != "audit":
            return

        cov_ledger = step_ctx.coverage_ledger
        if not cov_ledger or not cov_ledger.required_files:
            return

        target_path = str(tool_ctx.params.get("path") or "").lower().replace("\\", "/")
        req_files = [f.lower().replace("\\", "/") for f in cov_ledger.required_files]
        is_req = any(rf in target_path or target_path in rf for rf in req_files)

        # Lớp 1: Khóa hoàn tất — Đã đọc đủ 100% tệp mục tiêu
        cov = cov_ledger.evaluate_coverage()
        if cov_ledger.files_fully_read():
            if tool_ctx.tool in ("view_file", "list_dir", "grep_search"):
                tool_ctx.is_intercepted = True
                read_str = ", ".join(list(cov_ledger.read_files))
                tool_ctx.interception_observation = (
                    f"🛑 [EVIDENCE COLLECTION 100% COMPLETE]: Bạn đã đọc đầy đủ tất cả các tệp mục tiêu bắt buộc ({read_str})!\n"
                    f"Hệ thống KHÓA TOÀN BỘ CÔNG CỤ ĐỌC (`{tool_ctx.tool}`). Bạn không được phép đọc thêm bất kỳ tệp nào.\n"
                    f"HÀNH ĐỘNG BẮT BUỘC NGAY BÂY GIỜ: Hãy phát hành JSON với trường 'final_answer' để nộp Báo Cáo Kiểm Toán Kỹ Thuật "
                    f"đầy đủ gồm (Số dòng, SHA-256, Class/Hàm, Cơ chế phối hợp) kèm mã Canary. TUYỆT ĐỐI KHÔNG GỌI TOOL NỮA."
                )
                return

        # Lớp 2: Khóa phạm vi mục tiêu — Cấm đọc tệp lạ ngoài danh sách yêu cầu của Master
        if tool_ctx.tool == "view_file" and not is_req:
            tool_ctx.is_intercepted = True
            req_str = ", ".join(cov_ledger.required_files)
            tool_ctx.interception_observation = (
                f"🛑 [SCOPE-VIOLATION BLOCKED]: Tệp `{tool_ctx.params.get('path')}` NẰM NGOÀI PHẠM VI MỤC TIÊU CỦA MASTER!\n"
                f"Mục tiêu của Master CHỈ YÊU CẦU kiểm toán các tệp: `{req_str}`.\n"
                f"Hệ thống TỪ CHỐI THỰC THI lệnh đọc tệp ngoài phạm vi.\n"
                f"HÀNH ĐỘNG BẮT BUỘC: Hãy dùng 'view_file' để đọc đúng tệp mục tiêu còn thiếu, hoặc xuất 'final_answer' nếu đã đọc xong."
            )



class TransactionalMutationHook(AgentLifecycleHook):
    """
    Vũ khí 4 (OpenAI Sandbox Agents): Quản lý giao dịch mutation tệp.
    Tự động chụp Snapshot trước khi sửa tệp và Rollback ngay lập tức nếu làm hỏng cú pháp.
    """

    async def before_tool_dispatch(
        self, step_ctx: StepContext, tool_ctx: ToolInvocationContext
    ) -> None:
        if tool_ctx.is_intercepted or tool_ctx.tool not in ("replace_file_content", "write_to_file"):
            return

        raw_target = tool_ctx.params.get("path") or tool_ctx.params.get("TargetFile") or tool_ctx.params.get("target")
        if raw_target:
            from core.utils.project_workspace import resolve_container_or_workspace_path
            resolved_t = resolve_container_or_workspace_path(str(raw_target))
            if resolved_t:
                from core.kernel.transaction_manager import get_transaction_manager
                tx_mgr = get_transaction_manager()
                step_ctx.tx_manager = tx_mgr
                step_ctx.active_tx_target = resolved_t
                tx_mgr.begin_transaction(step_ctx.task_id, [resolved_t])

    async def after_tool_executed(
        self, step_ctx: StepContext, result_ctx: ToolResultContext
    ) -> None:
        tx_mgr = step_ctx.tx_manager
        tx_target = step_ctx.active_tx_target
        if not (tx_mgr and tx_target):
            return

        is_valid, syn_err = tx_mgr.verify_transaction([tx_target])
        if not is_valid:
            tx_mgr.rollback(step_ctx.task_id)
            logger.warning("⏪ [TRANSACTION-ROLLBACK] Sửa tệp gãy cú pháp (%s). Đã hoàn tác tệp.", syn_err)
            result_ctx.outcome_ok = False
            result_ctx.processed_output = (
                f"❌ [TRANSACTION-ROLLBACK-TRIGGERED]: Thao tác sửa tệp `{Path(tx_target).name}` làm GÃY CÚ PHÁP Python ({syn_err})!\n"
                f"Kernel đã TỰ ĐỘNG HOÀN TÁC (Rollback) tệp về trạng thái sạch ban đầu để chống cascade failure.\n"
                f"HÀNH ĐỘNG BẮT BUỘC: Bạn không được đoán mò. Hãy dùng 'view_file' kiểm tra lại chính xác cấu trúc tệp trước khi sửa lại!"
            )
        else:
            tx_mgr.commit(step_ctx.task_id)

        # Xóa cờ giao dịch hiện thời
        step_ctx.tx_manager = None
        step_ctx.active_tx_target = None


class CoverageAndWorkingMemoryHook(AgentLifecycleHook):
    """
    Cập nhật CoverageLedger và kích hoạt Working Memory Eviction (Vũ khí 1 - Meta CCA).
    """

    async def after_tool_executed(
        self, step_ctx: StepContext, result_ctx: ToolResultContext
    ) -> None:
        if result_ctx.tool != "view_file" or not result_ctx.outcome_ok:
            return

        step_ctx.has_successful_view_file = True

        # 1. Cập nhật CoverageLedger nếu đang ở chế độ audit
        if step_ctx.mode == "audit" and step_ctx.coverage_ledger:
            cov_check = step_ctx.coverage_ledger.evaluate_coverage()
            if not cov_check.get("missing_files"):
                read_str = ", ".join(list(step_ctx.coverage_ledger.read_files))
                result_ctx.processed_output += (
                    f"\n\n🎯 [COVERAGE-COMPLETE]: Bạn đã đọc đầy đủ tất cả các tệp bắt buộc ({read_str}).\n"
                    f"HÀNH ĐỘNG BẮT BUỘC BƯỚC TIẾP THEO: DỪNG GỌI TOOL! Hãy chuyển ngay sang bước xuất 'final_answer' để hoàn tất báo cáo kiểm toán cùng mã Canary!"
                )


class TracebackDistillerHook(AgentLifecycleHook):
    """
    Rút trích các dòng lỗi chính của Pytest lên đầu log quan sát để SLM dễ chú ý.
    """

    async def after_tool_executed(
        self, step_ctx: StepContext, result_ctx: ToolResultContext
    ) -> None:
        if result_ctx.tool == "run_command" and any(k in result_ctx.processed_output for k in ["FAIL", "AssertionError", "assert "]):
            fail_summary = [
                l.strip()
                for l in result_ctx.processed_output.splitlines()
                if any(l.strip().startswith(p) for p in [">", "E ", "FAILED"])
            ]
            if fail_summary:
                result_ctx.processed_output = (
                    f"🔍 [LỖI CHÍNH]:\n" + "\n".join(fail_summary[:5]) + f"\n\n[CHI TIẾT LOG TEST]:\n{result_ctx.processed_output}"
                )


# ==============================================================================
# CÁC INTERCEPTOR KIỂM ĐỊNH TRƯỚC BÀN GIAO (PRE-SUBMISSION HOOKS)
# ==============================================================================

class NoFabricationGuardHook(AgentLifecycleHook):
    """Chặn chế tạo dữ liệu giả mạo khi chưa đọc được tệp nào trên đĩa."""

    async def before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        if step_ctx.mode == "audit" and not step_ctx.has_successful_view_file:
            refusal_payload = {
                "verdict": "needs_validation",
                "status": "KHONG_THE_DOC_TEP",
                "target": step_ctx.scope_rel,
                "unresolved_fact": f"Không thể đọc được tệp mục tiêu trên đĩa: {step_ctx.scope_rel}",
                "evidence": "view_file không thành công trên đĩa thực tế; kích hoạt cơ chế chặn chế tạo dữ liệu giả lập.",
                "severity": None,
                "source_trace": None,
            }
            refusal = json.dumps(refusal_payload, ensure_ascii=False, indent=2)
            step_ctx.should_stop = True
            step_ctx.stop_result = refusal
            return False, refusal

        return True, None


class MultiFileCoverageGuardHook(AgentLifecycleHook):
    """Đảm bảo đọc đủ tất cả các tệp mã nguồn yêu cầu trong mục tiêu."""

    async def before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        if step_ctx.mode != "audit":
            return True, None

        req_files = [f for f in re.findall(r"\b[\w/\\-]+\.py\b", step_ctx.goal.lower()) if not f.startswith("test_")]
        if len(req_files) >= 2 and step_ctx.step < step_ctx.max_steps:
            missing_files = [rf for rf in req_files if not any(rf in vf.lower().replace("\\", "/") for vf in step_ctx.viewed_files)]
            if missing_files:
                rejection = (
                    f"[OBSERVATION]\n🚨 CẢNH BÁO KIỂM TOÁN ĐA TỆP (MULTI-FILE GUARD):\n"
                    f"Mục tiêu yêu cầu kiểm toán cả 2 tệp, nhưng bạn chưa đọc tệp: `{', '.join(missing_files)}`!\n"
                    f"HÀNH ĐỘNG BẮT BUỘC: Hãy phát hành JSON gọi 'view_file' để đọc tệp `{missing_files[0]}` trước khi nộp báo cáo."
                )
                return False, rejection

        return True, None


class PreSubmissionReflexionHook(AgentLifecycleHook):
    """
    Tự thẩm định tính toàn vẹn của báo cáo cuối cùng trước khi chuyển tới Critic.
    (Kiểm tra Canary, SHA-256, dòng, hàm, cơ chế phối hợp).
    """

    async def before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        if step_ctx.step >= step_ctx.max_steps:
            return True, None

        from core.kernel.project_agent_loop import ProjectAgentLoop
        # Gọi phương thức kiểm định của AgentLoop
        dummy_loop = ProjectAgentLoop.__new__(ProjectAgentLoop)
        is_ready, missing_reqs = dummy_loop._pre_submission_check(str(final_answer), step_ctx.goal)
        if not is_ready:
            if all("Canary" in m for m in missing_reqs):
                nudge = "HÀNH ĐỘNG BẮT BUỘC: Hãy sao chép chuỗi mã Canary từ đề bài dán vào dòng cuối cùng của báo cáo và phát hành final_answer ngay (TUYỆT ĐỐI KHÔNG gọi view_file tìm Canary)."
            else:
                nudge = "HÀNH ĐỘNG BẮT BUỘC: Hãy dùng 'run_command' hoặc 'view_file' để lấy đầy đủ các thông tin trên và phát hành lại final_answer hoàn chỉnh."

            rejection = (
                f"[OBSERVATION]\n⚠️ TỰ THẨM ĐỊNH NỘI BỘ (PRE-SUBMISSION REFLEXION):\n"
                f"Báo cáo của bạn sắp nộp nhưng phát hiện THIẾU các yêu cầu cốt lõi sau:\n"
                + "\n".join(f"- {m}" for m in missing_reqs) + "\n\n"
                + nudge
            )
            return False, rejection

        return True, None


class TddVerificationHook(AgentLifecycleHook):
    """Chạy kiểm thử xác minh chất lượng code sau khi sửa (chế độ Fix)."""

    async def before_submission(
        self, step_ctx: StepContext, thought: str, final_answer: str
    ) -> Tuple[bool, Optional[str]]:
        has_py = any(f.endswith(".py") for f in step_ctx.touched_files)
        if step_ctx.mode == "fix" and has_py and step_ctx.step < step_ctx.max_steps:
            try:
                from core.utils.post_patch_verify import verify_after_repair
                from core.utils.executor_cache import invalidate_all_executors_sync

                ok, vmsg = verify_after_repair(
                    touched_rel_paths=step_ctx.touched_files,
                    run_compileall=False,
                    run_tests=False,
                )
                invalidate_all_executors_sync()
                if not ok:
                    rejection = (
                        f"[OBSERVATION]\n🚨 Lỗi kiểm thử xác minh (Verification Test Failed):\n{vmsg}\n\n"
                        f"Mã nguồn bạn vừa viết không vượt qua được bài kiểm tra cú pháp. Hãy tự sửa lại lỗi logic hoặc lỗi test này trước khi nộp bài."
                    )
                    return False, rejection
            except Exception as verify_err:
                logger.warning("Kiểm thử xác minh lỗi hệ thống: %s", verify_err)

        return True, None
