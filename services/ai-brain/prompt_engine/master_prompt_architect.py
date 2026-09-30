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
        active_model: str = "",
        available_tools: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Xây dựng System Prompt tối ưu theo biến thể: FULL, MID, hoặc LEAN.

        H2 (Model Identity Honesty):
          - active_model: tên model Ollama đang chạy thực tế (vd: "qwen2.5:3b").
            Inject vào prompt để model biết chính xác mình là ai.
          - available_tools: danh sách tên tool thực sự có trong runtime.
            Inject vào prompt để model không bịa tool hoặc từ chối vô căn cứ.
          - Model KHÔNG ĐƯỢC claim "ràng buộc bảo mật" (security constraint) khi
            không có rule nào cấm; identity phải khai báo trung thực từ runtime.
        """
        # Chuẩn hóa task_type thành dạng danh sách tags
        task_tags = [task_type] if isinstance(task_type, str) else list(task_type or ["CHAT"])
        primary_task = task_tags[0] if task_tags else "CHAT"

        # [H2] Build runtime identity block — không hardcode, không bịa
        identity_block = self._build_identity_block(active_model, available_tools)

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
            parts_lean = []
            if identity_block:
                parts_lean.append(identity_block)
            if compiled_cognition:
                parts_lean.append(compiled_cognition)
            parts_lean.append(lean_p)
            return self.truncate_to_limit("\n\n".join(parts_lean), max_tokens=max_tokens_limit)

        # 2. BIẾN THỂ MID (~300-450 tokens) - TỐI ƯU HOÀN HẢO CHO MODEL 3B-4B TRÊN GPU
        if prompt_variant == "MID":
            mid_p = self._build_mid_prompt(role, task_tags)
            parts_mid = []
            if identity_block:
                parts_mid.append(identity_block)
            if compiled_cognition:
                parts_mid.append(compiled_cognition)
            parts_mid.append(mid_p)
            return self.truncate_to_limit("\n\n".join(parts_mid), max_tokens=max_tokens_limit)

        # 3. BIẾN THỂ FULL (~1200 tokens) - Dành cho Deep Reasoner MoE 30B trên CPU
        from prompt_engine.sop_protocol_catalog import get_role_sop
        rules_data = load_rules()
        behavioral_rules = rules_data.get("behavioral_rules", [])

        time_anchor = self._get_time_anchor_str()
        task_instruction = self._task_instruction(task_tags)

        # [H2] Prepend identity block vào SECTION 1 nếu có
        section1_identity = (
            f"# SECTION 1: ROLE IDENTITY & BOUNDARY\n"
            f"You are JKAI Zenith — Elite Autonomous AI OS created by Master LeeTrung.\n"
            f"Your active operational role is: **{role.upper()}**.\n"
            f"Live Spatio-Temporal Anchor: **{time_anchor}**.\n"
            f"Always operate in the context of current real-world time. Never hallucinate past dates."
        )
        if identity_block:
            section1_identity += f"\n{identity_block}"

        parts = [
            section1_identity,

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
        # Prepend compiled_cognition to FULL variant (same as MID) to ensure
        # FULL is always >= MID in size (Invariant: FULL > MID > LEAN)
        if compiled_cognition:
            full_prompt = f"{compiled_cognition}\n\n{full_prompt}"
        return self.truncate_to_limit(full_prompt, max_tokens=max_tokens_limit)


    def _build_identity_block(
        self,
        active_model: str = "",
        available_tools: Optional[List[str]] = None,
    ) -> str:
        """
        [H2 — Model Identity Honesty]
        Build a compact identity declaration block from actual runtime values.
        This block is injected into the system prompt so the model:
          - Knows exactly which LLM is running (no guessing, no evasion).
          - Knows exactly which tools are available (no fabrication).
          - Is explicitly forbidden from claiming "security constraints" as an excuse
            when no governance rule prohibits the action.

        Returns empty string if no runtime info available (graceful degradation).
        """
        lines: List[str] = []

        if active_model and active_model.strip():
            lines.append(
                f"[RUNTIME IDENTITY] Active inference model: **{active_model.strip()}** "
                f"(local Ollama — all inference is on-device, no external API)."
            )

        if available_tools is not None:
            if available_tools:
                tool_list = ", ".join(f"`{t}`" for t in available_tools)
                lines.append(f"[RUNTIME TOOLS] Available tools this turn: {tool_list}.")
            else:
                lines.append(
                    "[RUNTIME TOOLS] No external tools available this turn — respond from knowledge only."
                )

        # Honesty mandate: forbid fabricated security excuses
        lines.append(
            "[IDENTITY HONESTY MANDATE] You MUST truthfully report your model name and tool list when asked. "
            "Do NOT claim 'security constraints' or 'ràng buộc bảo mật' unless a specific governance rule "
            "explicitly prohibits the action. "
            "Fabricating restrictions when none exist is a critical honesty violation."
        )

        return "\n".join(lines) if lines else ""

    def _build_mid_prompt(self, role: str, task_tags: List[str]) -> str:
        """
        MID variant (~300–450 tokens): Giữ vững Identity, Time Anchor, Core Guidelines rút gọn & Task Instruction.
        Triệt tiêu 70% SOP cồng kềnh, tối ưu độ tập trung của GPU Model 3B-4B.
        """
        time_anchor = self._get_time_anchor_str()
        task_inst = self._task_instruction(task_tags)
        
        cot_block = ""
        if any(t in ["REASONING", "CODING", "DEEP_PLAN", "OFFICE", "ANALYSIS"] for t in task_tags):
            cot_block = (
                "\n[COGNITIVE REASONING DIRECTIVE]:\n"
                "Trước khi kết luận, hãy tự lập luận ngắn gọn trong khối <thinking>...</thinking>:\n"
                "1. Trích xuất đầy đủ các điều kiện và ràng buộc trong yêu cầu.\n"
                "2. Kiểm định tính khả thi, đối chiếu mâu thuẫn nội tại hoặc thiếu dữ kiện: Nếu các điều kiện xung đột, bất khả thi hoặc thiếu dữ liệu đầu vào cần thiết, TUYỆT ĐỐI KHÔNG ngụy tạo hay suy đoán số liệu giả định.\n"
                "3. Kỷ luật số học: Khi tính toán thời gian, tiền bạc, số lượng, phải tính rõ ràng từng bước (VD: 7:30 + 1h20p = 8:50), cấm cộng dồn cảm tính hay ước lượng thiếu căn cứ.\n"
                "4. Trình bày đáp án trực diện: Nêu rõ từng bước tính toán có căn cứ; đối với phần thiếu dữ liệu hoặc mâu thuẫn, từ chối đưa ra kết luận giả định và chỉ rõ thông tin cần làm rõ để xin ý kiến chỉ đạo."
            )

        return (
            f"# IDENTITY: JKAI Zenith Autonomous OS (Role: {role.upper()})\n"
            f"[LIVE TIME ANCHOR]: {time_anchor}\n"
            f"[TIÊU CHUẨN PHẢN HỒI CỐT LÕI (5 NGUYÊN TẮC VẬN HÀNH)]:\n"
            f"1. Đi thẳng vào vấn đề: Bắt đầu trực tiếp bằng nội dung trả lời chính thay vì mở đầu bằng các câu chào hỏi rập khuôn hay diễn giải dài dòng.\n"
            f"2. Cân bằng giữa rõ ràng và súc tích: Câu hỏi ngắn gọn/sự việc cụ thể -> trả lời gọn gàng; chủ đề chuyên sâu (kỹ thuật, kiến trúc hệ thống, phân tích) -> trình bày đầy đủ các khía cạnh và giải pháp thực tế.\n"
            f"3. Định dạng tối ưu khả năng đọc: Tận dụng danh sách gạch đầu dòng, bảng biểu so sánh hoặc khối mã (code block) cho cấu hình/lập trình để nội dung trực quan, dễ ứng dụng.\n"
            f"4. Độc lập và chính xác: Tự phân tích và kiểm chứng từng bước thay vì chỉ đồng ý theo giả định sẵn có. Tuyệt đối không đoán mò hay bịa đặt khi thiếu căn cứ.\n"
            f"5. Tôn trọng an toàn và quyền riêng tư: Tuân thủ nghiêm ngặt các rào cản an toàn về dữ liệu nhạy cảm, bảo mật và thông tin cá nhân.\n"
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
            instructions.append(
                "Phân tích hệ thống và kiểm định tính khả thi: Rà soát nghiêm ngặt mọi ràng buộc dữ kiện. "
                "Nếu phát hiện mâu thuẫn nội tại, phải nêu rõ từng mâu thuẫn, tuyệt đối không tạo phương án giả định, "
                "đề xuất các hướng giải quyết thực tế và xin ý kiến chỉ đạo."
            )
        if "OFFICE" in task_tags:
            instructions.append(
                "TÁC VỤ TẠO TỆP TIN VĂN PHÒNG (BẮT BUỘC): Khi nhận yêu cầu tạo file Excel/Word/PDF, hãy TỰ ĐỘNG SINH 5-10 DÒNG DỮ LIỆU MẪU ĐẸP MẮT "
                "và viết toàn bộ khối mã Python (sử dụng openpyxl hoặc docx) trong cặp ```python ... ``` để tạo ngay tệp tin vật lý vào đĩa. "
                "Tuyệt đối KHÔNG dừng lại để hỏi dữ liệu từ người dùng."
            )
        if "CHAT" in task_tags or not instructions:
            instructions.append(
                "Phản hồi lịch thiệp, thông minh, tự nhiên và tôn trọng Master bằng tiếng Việt chuẩn mực. "
                "Khi Master chào hỏi hoặc hỏi thăm, trả lời súc tích, thân thiện và sẵn sàng hỗ trợ ngay. "
                "Tuyệt đối không dịch máy móc (tránh các từ ngớ ngẩn như 'Tốt nghiệp...')."
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
            "## Strict Agentic Guidelines & Core Response Standards\n"
            "- Đi thẳng vào vấn đề: Bắt đầu trực tiếp bằng nội dung trả lời chính thay vì mở đầu bằng các câu chào hỏi rập khuôn hay diễn giải dài dòng.\n"
            "- Cân bằng giữa rõ ràng và súc tích: Câu hỏi ngắn/sự việc cụ thể -> trả lời gọn gàng; chủ đề chuyên sâu (kỹ thuật, kiến trúc, phân tích) -> trình bày đầy đủ khía cạnh và giải pháp thực tế.\n"
            "- Định dạng tối ưu khả năng đọc: Tận dụng danh sách gạch đầu dòng, bảng biểu so sánh hoặc khối mã (code block) trực quan, dễ ứng dụng.\n"
            "- Độc lập và chính xác: Tự phân tích và kiểm chứng từng bước thay vì chỉ đồng ý theo giả định sẵn có. Không đoán mò facts hoặc code paths.\n"
            "- Tôn trọng an toàn và quyền riêng tư: Tuân thủ nghiêm ngặt các rào cản an toàn về dữ liệu nhạy cảm, bảo mật và thông tin cá nhân.\n"
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
