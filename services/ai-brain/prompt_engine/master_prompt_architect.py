import os
import sys
import yaml
import logging
from typing import Optional, List, Union, Dict, Any

from core.guardrails.rules_loader import load_rules, get_behavioral_rules, get_agent_defaults

logger = logging.getLogger("MasterPromptArchitect")


class MasterPromptArchitect:
    """
    🏛️ Primary System Prompt Architect for JKAI Zenith OS (v50.0).
    Features:
      1. Dynamic Mode Selection: FULL (Deep Reasoner), MID (3B-7B Fast Model), LEAN (Sub-second Reflex).
      2. Dynamic Truncation: truncate_to_limit() with attention preservation.
      3. YAML-Driven Administrative Templates: Decoupled document standards.
      4. Tag-based Task Types: Multi-intent support.
      5. Robust Fallback Cognition on compiler degradation.
    """
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "D:\\Docker\\JKAI")
        self._admin_templates = self._load_administrative_templates()

    def _load_administrative_templates(self) -> Dict[str, Any]:
        """Nạp cấu hình biểu mẫu hành chính từ file YAML ngoài."""
        yaml_path = os.path.join(os.path.dirname(__file__), "..", "templates", "administrative_documents.yaml")
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"[PROMPT-ARCHITECT] Cannot load administrative YAML: {e}")
        return {}

    def build_master_system_prompt(
        self,
        role: str = "RECEPTIONIST",
        task_type: Union[str, List[str]] = "CHAT",
        task_id: str = "sys",
        goal: str = "",
        extra_tools: list = None,
        prompt_variant: str = "MID",
        max_tokens_limit: int = 4000,
        **kwargs
    ) -> str:
        """
        Xây dựng System Prompt tối ưu theo biến thể: FULL, MID, hoặc LEAN.
        """
        # Chuẩn hóa task_type thành dạng danh sách tags
        task_tags = [task_type] if isinstance(task_type, str) else list(task_type or ["CHAT"])
        primary_task = task_tags[0] if task_tags else "CHAT"

        # 🧠 [COGNITIVE-CONTEXT-COMPILER]: Compile cognition prompt
        compiled_cognition = ""
        context_degraded = False
        try:
            from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
            mode = "PLANNING" if "DEEP_PLAN" in task_tags else ("EXECUTION" if extra_tools else "REACTIVE")
            compiler = CognitiveContextCompiler(mission_id=task_id)
            compiled_cognition = compiler.compile(role=role, cognitive_mode=mode)
        except Exception as c_err:
            context_degraded = True
            compiled_cognition = (
                "[COGNITIVE FALLBACK]: You are JKAI Zenith OS acting in resilient baseline mode. "
                "Maintain strict factual accuracy, state machine discipline, and empirical verification."
            )
            logger.warning(
                "[CONTEXT-COMPILER-FALLBACK] Task '%s': Compiler failed (%s). Active Fallback Cognition applied.",
                task_id, c_err
            )

        # 1. BIẾN THỂ LEAN (~100-150 tokens) - Dành cho Phản Xạ Nhanh Sub-second
        if prompt_variant == "LEAN":
            lean_p = self._build_lean_prompt(role, primary_task)
            full_lean = f"{compiled_cognition}\n\n{lean_p}" if compiled_cognition else lean_p
            return self.truncate_to_limit(full_lean, max_tokens=max_tokens_limit)

        # 2. BIẾN THỂ MID (~300-450 tokens) - TỐI ƯU HOÀN HẢO CHO MODEL 3B-4B TRÊN GPU
        if prompt_variant == "MID":
            mid_p = self._build_mid_prompt(role, task_tags)
            full_mid = f"{compiled_cognition}\n\n{mid_p}" if compiled_cognition else mid_p
            return self.truncate_to_limit(full_mid, max_tokens=max_tokens_limit)

        # 3. BIẾN THỂ FULL (~1200 tokens) - Dành cho Deep Reasoner MoE 30B trên CPU
        from prompt_engine.sop_protocol_catalog import get_role_sop
        rules_data = load_rules()
        behavioral_rules = rules_data.get("behavioral_rules", [])

        time_anchor = self._get_time_anchor_str()
        task_instruction = self._task_instruction(task_tags)

        parts = [
            f"# SECTION 1: ROLE IDENTITY & BOUNDARY\n"
            f"You are JKAI Zenith — Elite Autonomous AI OS created by Master LeeTrung.\n"
            f"Your active operational role is: **{role.upper()}**.\n"
            f"Live Spatio-Temporal Anchor: **{time_anchor}**.\n"
            f"Always operate in the context of current real-world time. Never hallucinate past dates.",
            
            f"# SECTION 2: OPERATIONAL 5-STAGE SOP CHECKLIST\n"
            f"{get_role_sop(role)}",

            f"# SECTION 3: STRICT AGENTIC GUIDELINES\n"
            f"{self._get_agentic_guidelines()}",

            f"# SECTION 4: TASK DIRECTIVES & FORMATTING\n"
            f"### Active Task Tags: {', '.join(task_tags)}\n"
            f"{task_instruction}\n"
            f"### Behavioral Directives:\n" + ("\n".join([f"  * {r}" for r in behavioral_rules]) if behavioral_rules else "  * Obey Master directives strictly.") + "\n",

            f"# SECTION 5: PLANNING & REACTIVE DISCIPLINE\n"
            f"{self._get_planning_mode_instructions()}\n\n"
            f"{self._get_reactive_wakeup_instructions()}"
        ]

        if context_degraded:
            parts.insert(0, "[SYSTEM ALERT]: Cognitive Substrate in Fallback Mode.")

        full_prompt = "\n\n---\n\n".join(parts)
        return self.truncate_to_limit(full_prompt, max_tokens=max_tokens_limit)

    def _build_mid_prompt(self, role: str, task_tags: List[str]) -> str:
        """
        MID variant (~300–450 tokens): Giữ vững Identity, Time Anchor, Core Guidelines rút gọn & Task Instruction.
        Triệt tiêu 70% SOP cồng kềnh, tối ưu độ tập trung của GPU Model 3B-4B.
        """
        time_anchor = self._get_time_anchor_str()
        task_inst = self._task_instruction(task_tags)
        
        cot_block = ""
        if any(t in ["REASONING", "CODING", "DEEP_PLAN", "OFFICE"] for t in task_tags):
            cot_block = (
                "\n[COGNITIVE REASONING DIRECTIVE]:\n"
                "Trước khi kết luận, hãy tự lập luận ngắn gọn trong khối <thinking>...</thinking>:\n"
                "1. Phân tích trọng tâm câu hỏi của Master.\n"
                "2. Kiểm tra tính xác thực số liệu/logic.\n"
                "3. Trình bày đáp án chuẩn xác, trực diện."
            )

        return (
            f"# IDENTITY: JKAI Zenith Autonomous OS (Role: {role.upper()})\n"
            f"[LIVE TIME ANCHOR]: {time_anchor}\n"
            f"[STRICT CORE RULES]:\n"
            f"1. Never guess facts or code paths. Base answers strictly on empirical evidence.\n"
            f"2. Always obey Master directives. Return professional, verified results.\n"
            f"3. Do not mask errors. Maintain API & document contracts.\n"
            f"4. Trả lời súc tích, trực diện, mạch lạc (ưu tiên bảng Markdown hoặc bullet points ngắn gọn). Tránh viết dông dài.\n"
            f"[TASK INSTRUCTION ({', '.join(task_tags)})]:\n"
            f"{task_inst}{cot_block}\n"
            f"Reply concisely, accurately, and professionally in user's language."
        )

    def _build_lean_prompt(self, role: str, primary_task: str) -> str:
        """LEAN variant (~150 tokens) cho Fast Reflex."""
        time_anchor = self._get_time_anchor_str()
        task_inst = self._task_instruction([primary_task])
        return (
            f"You are JKAI Zenith AI assistant (role: {role.upper()}).\n"
            f"[TIME ANCHOR]: {time_anchor}.\n"
            f"{task_inst}\n"
            f"Reply concisely and directly in user's language."
        )

    def truncate_to_limit(self, prompt: str, max_tokens: int = 4000) -> str:
        """
        Cắt gọt thông minh: Giữ nguyên phần đầu (Identity & Core Rules) và phần cuối (Directives),
        chỉ cắt bớt phần thân nếu vượt quá giới hạn token.
        """
        est_tokens = len(prompt) // 4
        if est_tokens <= max_tokens:
            return prompt

        char_limit = max_tokens * 4
        head_chars = int(char_limit * 0.4)
        tail_chars = int(char_limit * 0.6)
        
        truncated = (
            prompt[:head_chars] +
            "\n\n...[PROMPT CONTENT TRUNCATED FOR CONTEXT OPTIMIZATION]...\n\n" +
            prompt[-tail_chars:]
        )
        logger.info(f"[PROMPT-TRUNCATION]: Prompt truncated from ~{est_tokens} to ~{max_tokens} tokens.")
        return truncated

    def _get_time_anchor_str(self) -> str:
        import datetime, pytz
        try:
            tz = pytz.timezone(os.getenv("GENERIC_TIMEZONE", "Asia/Bangkok"))
            now_dt = datetime.datetime.now(tz)
        except Exception:
            now_dt = datetime.datetime.now()

        weekdays_vi = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"]
        weekday_str = weekdays_vi[int(now_dt.strftime("%w"))]
        location_str = os.getenv("GENERIC_LOCATION", "Việt Nam (Múi giờ Đông Dương UTC+7)")
        return f"{now_dt.strftime('%H:%M:%S')} {weekday_str}, ngày {now_dt.strftime('%d/%m/%Y')} (Năm {now_dt.year}) tại {location_str}"

    def _task_instruction(self, task_tags: List[str]) -> str:
        instructions = []
        if "LOOKUP" in task_tags:
            instructions.append("Answer with precise, factual information. If not available in context, say so honestly.")
        if "CODING" in task_tags:
            instructions.append("Plan first, identify target files, implement cleanly without placeholders, verify with exit code 0.")
        if "ANALYSIS" in task_tags:
            instructions.append("Define evaluation framework, analyze systematically, highlight anomalies, cross-check conclusions.")
        if "OFFICE" in task_tags:
            instructions.append(
                "TÁC VỤ TẠO TỆP TIN VĂN PHÒNG (BẮT BUỘC): Khi nhận yêu cầu tạo file Excel/Word/PDF, hãy TỰ ĐỘNG SINH 5-10 DÒNG DỮ LIỆU MẪU ĐẸP MẮT "
                "và viết toàn bộ khối mã Python (sử dụng openpyxl hoặc docx) trong cặp ```python ... ``` để tạo ngay tệp tin vật lý vào đĩa. "
                "Tuyệt đối KHÔNG dừng lại để hỏi dữ liệu từ người dùng."
            )
        if "CHAT" in task_tags or not instructions:
            instructions.append(
                "Phản hồi trực diện, chuẩn mực và tôn trọng Master. Khi soạn thảo văn bản hành chính (đơn từ, tờ trình), "
                "bám sát thể thức chuẩn công vụ Việt Nam theo tài liệu tham chiếu."
            )
        return "\n".join([f"- {inst}" for inst in instructions])

    @staticmethod
    def _get_planning_mode_instructions() -> str:
        return (
            "## Planning Mode Workflow\n"
            "1. **Research**: Inspect codebase and files thoroughly.\n"
            "2. **Implementation Plan**: Outline affected components and proposed diffs.\n"
            "3. **Execution**: Implement changes incrementally.\n"
            "4. **Verification**: Run unit tests (`exit 0`).\n"
            "5. **Walkthrough**: Document changes and validation results."
        )

    @staticmethod
    def _get_agentic_guidelines() -> str:
        return (
            "## Strict Agentic Guidelines\n"
            "- Never Guess Code Logic or File Paths. Inspect authoritative sources first.\n"
            "- No Superficial Patches. Fix root causes verified by test exit 0.\n"
            "- Preserve API Contracts & Existing Documentation."
        )

    @staticmethod
    def _get_reactive_wakeup_instructions() -> str:
        return (
            "## Reactive Wakeup\n"
            "- Do NOT poll in a loop. Await background event notifications.\n"
            "- Present clean, actionable summaries to Master."
        )


master_prompt_architect = MasterPromptArchitect()
