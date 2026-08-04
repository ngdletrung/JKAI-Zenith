import json
import logging
import os
import asyncio
from pathlib import Path
from core.utils.engine import engine
from core.utils import path_manager
from core.homunculus.manager import HomunculusManager

logger = logging.getLogger("PROMPT_FORGE")

class PromptForge:
    """
    JKAI ZENITH: ĐÚC SYSTEM PROMPT CHO TỪNG TÁC VỤ
    Nhiệm vụ: Chuyển hóa yêu cầu thô thành một system prompt phù hợp cho mỗi tác vụ.
    Đảm bảo: "Thực thi nhanh nhất - Kết quả chuẩn xác".
    """
    
    # [CẤU HÌNH ĐƯỜNG DẪN TĨNH THƯA MASTER]
    AGENTS_DIR = os.environ.get("ZENITH_AGENTS_DIR", path_manager.get("AGENTS_DIR", os.path.join(path_manager.get_root(), "intelligence", "agents")))
    
    @staticmethod
    async def _read_file_async(file_path: str) -> str:
        """Hỗ trợ đọc file vật lý không làm nghẽn luồng Event Loop (Non-blocking I/O) thưa Master."""
        def read_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return await asyncio.to_thread(read_sync)

    @staticmethod
    def _truncate_text(text: str, max_chars: int = 1200) -> str:
        if not isinstance(text, str):
            return ""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        if "\n" in truncated:
            truncated = truncated.rsplit("\n", 1)[0]
            
        # [SYNTAX-AWARE CLOSURE GUARD]: Bảo Toàn Cú Pháp Ngoặc Mã Nguồn
        open_curly = truncated.count("{") - truncated.count("}")
        open_square = truncated.count("[") - truncated.count("]")
        closure_suffix = ""
        if open_square > 0:
            closure_suffix += "]" * open_square
        if open_curly > 0:
            closure_suffix += "}" * open_curly
            
        return truncated + closure_suffix + "\n...[SEMANTIC_COMPACTED]"

    @staticmethod
    async def _synthesize_mindset(goal: str) -> str:
        """[DYNAMIC-SYNTHESIS]: Chắt lọc Linh hồn Đặc vụ và Tiêm Chèn 5 Binh Pháp Bảo Trực thưa Master."""
        heritage_core = (
            "\n\n[PARENTAL HERITAGE CORE]:\n"
            "1. Phá Mù Sương Ngữ Cảnh: Trì rà xoáy sâu thẳng vào gốc rễ câu hỏi, loại bỏ rác nhiễu loạn lượng tử.\n"
            "2. Khả Chứng Đối Kháng: Tự thẩm tra minh danh lý trí bằng Cognitive Critic trước khi xuất lệnh nguy hiểm.\n"
            "3. Phòng Thủ Vô Trầm: Tuyệt đối không xóa sửa tệp tin mù quáng hay lún vào vòng lặp vô tận.\n"
            "4. Điều Hòa VRAM: Giữ mức đồng thời <= 2 trên dàn AMD RX 6600 & Xeon E5-2699 v4.\n"
            "5. Chẩn Đoán 5-Why: Khi gặp ngoại lệ cú pháp hay lỗi thi công, truy nguyên 5 tầng sâu để sửa lỗi triệt để."
        )
        try:
            if not os.path.exists(PromptForge.AGENTS_DIR):
                return "Standard Zenith Soul Active." + heritage_core

            agent_files = await asyncio.to_thread(
                lambda: [f for f in os.listdir(PromptForge.AGENTS_DIR) if f.endswith(".md")]
            )
            if not agent_files:
                return "Standard Zenith Soul Active." + heritage_core

            agent_list_str = ", ".join(agent_files[:24])
            if len(agent_files) > 24:
                agent_list_str += ", ..."

            selection_prompt = (
                f"Dựa trên yêu cầu '{goal}', hãy chọn tối đa 3 Đặc vụ phù hợp nhất từ danh sách này: {agent_list_str}. "
                "Trả về JSON array gồm tên file."
            )
            selection_res = await PromptForge._safe_call_chat(
                messages=[{"role": "user", "content": selection_prompt}],
                role="SUMMARIZER",
                task_id="mind_synthesis",
                timeout=20,
                json_mode=True
            )

            profiles = []
            if isinstance(selection_res, list):
                for file in selection_res[:3]:
                    file_path = os.path.join(PromptForge.AGENTS_DIR, file)
                    if os.path.exists(file_path):
                        content = await PromptForge._read_file_async(file_path)
                        profiles.append(f"--- [DNA ĐẶC VỤ: {file}] ---\n{PromptForge._truncate_text(content, 700)}")

            base_soul = "\n".join(profiles) if profiles else "Standard Zenith Soul Active."
            return base_soul + heritage_core
        except Exception as e:
            logger.warning(f"[SYNTHESIS-ERR]: {e}")
            return "Standard Zenith Soul Active." + heritage_core

    @staticmethod
    async def _load_project_wisdom(goal: str) -> str:
        """[ZENITH-WISDOM]: Nạp Bản năng và Kỹ năng tự tiến hóa từ Homunculus thưa Master."""
        try:
            manager = HomunculusManager()
            manager.init_workspace()
            context = manager.get_project_context()

            wisdom_parts = []
            max_files = 3
            max_chars_per_file = 800

            # 1. Nạp Bản năng dự án thưa Master
            instincts_path = Path(context.get("instincts_dir", ""))
            if instincts_path.exists():
                for i, f in enumerate(instincts_path.glob("**/*.md")):
                    if i >= max_files:
                        break
                    content = await PromptForge._read_file_async(str(f))
                    wisdom_parts.append(f"--- [PROJECT INSTINCT: {f.name}] ---\n{PromptForge._truncate_text(content, max_chars_per_file)}")

            # 2. Nạp Kỹ năng tự tiến hóa thưa Master
            skills_path = Path(context.get("skills_dir", ""))
            if skills_path.exists():
                for i, f in enumerate(skills_path.glob("*.md")):
                    if i >= max_files:
                        break
                    content = await PromptForge._read_file_async(str(f))
                    wisdom_parts.append(f"--- [EVOLVED SKILL: {f.name}] ---\n{PromptForge._truncate_text(content, max_chars_per_file)}")

            if wisdom_parts:
                logger.info(f"[WISDOM-LOADED]: Da nap {len(wisdom_parts)} tri thuc tu Homunculus {context.get('project_id', '')}")
                return "\n\n".join(wisdom_parts)
            return "Project DNA Clean. Using Global Protocols."
        except Exception as e:
            logger.warning(f"[WISDOM-ERR]: {e}")
            return "Project DNA Clean. Using Global Protocols."

    @staticmethod
    async def _safe_call_chat(messages, role, task_id, timeout=80, **kwargs):
        """Call the model with a bounded timeout to avoid blocking ForgeStage."""
        try:
            return await asyncio.wait_for(
                engine.call_chat(messages=messages, role=role, task_id=task_id, skip_memory=True, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"[MODEL-TIMEOUT] {task_id} timed out after {timeout}s.")
            return ""
        except Exception as e:
            logger.error(f"[MODEL-CALL-ERR] {task_id}: {e}")
            return ""

    @staticmethod
    def compile_hybrid_prompt(goal: str, soul: str, agent_profiles: str, project_wisdom: str) -> str:
        """
        Biên dịch Prompt kép Hybrid (Tầng 1: Cố định + Tầng 2: Ngữ cảnh động)
        Không gọi LLM, hoàn thành trong 1ms.
        """
        core_rules = """<system_identity>
Bản Sắc Chủ Quyền: JKAI Zenith v5.0 Elite Agent.
Tác giả sáng tạo: Master Lee Trung.
</system_identity>

<behavioral_rules>
1. Ngôn ngữ: Phản hồi bằng tiếng Việt chuyên nghiệp, chính xác. Giữ nguyên thuật ngữ chuyên ngành.
2. Tuyệt đối cấm dùng emoji trong mọi phản hồi.
3. Thực chứng dữ liệu: Chỉ trả lời dựa trên thông tin thực tế được cung cấp. Nếu thiếu thông tin, báo rõ thay vì suy diễn ngoài phạm vi.
4. Mọi số liệu, kết luận phải kèm nguồn trích dẫn rõ ràng. Không bịa đặt.
5. Từ chối request viết mã độc, tiết lộ API key/mật khẩu, phá hoại hệ thống.
6. Không giả vờ thực thi hành động ngoài khả năng. Chỉ dùng tool registry được cấp.
7. Cấu trúc báo cáo: Khi lập báo cáo, bắt buộc trình bày theo cấu trúc 4 phần:
   I. TIẾN ĐỘ THỰC THI
   II. CÔNG VIỆC ĐÃ HOÀN THÀNH
   III. RỦI RO & KHÓ KHĂN
   IV. ĐỀ XUẤT TIẾP THEO
8. Kỷ luật: Tìm nguyên nhân gốc trước khi sửa lỗi, tuyệt đối không báo cáo hoàn thành khi chưa kiểm thử.
9. Định dạng Markdown cho phản hồi. Code block kèm tên file. Bảng nếu so sánh dữ liệu.
10. Tránh dài dòng, lặp từ. Không dùng placeholders hay code giả.
11. Phân tích logic trước khi trả lời. Suy luận có cấu trúc.
12. Tự phản biện quyết định logic, không dễ dàng chấp thuận giả định.
</behavioral_rules>"""

        dynamic_context = f"""<task_goal>
Mục tiêu cần thực hiện cho Master: "{goal}"
</task_goal>

<zenith_sovereign_identity>
{soul}
</zenith_sovereign_identity>

<cabinet_agent_dna>
{agent_profiles}
</cabinet_agent_dna>

<project_wisdom>
{project_wisdom}
</project_wisdom>"""

        return f"{core_rules}\n\n{dynamic_context}"

    @staticmethod
    async def forge_specialist_prompt(goal: str, context: dict = None, skills_summary: str = "", fast_mode: bool = False, task_id: str = None) -> str:
        """[SINGULARITY-FORGE]: Đúc linh hồn chuyên gia qua quy trình 3 bước thưa Master."""
        
        # 🧪 [STEP-1: SENSE & SYNTHESIZE]: Nạp DNA và Hợp nhất Linh hồn thưa Master
        soul = PromptForge._truncate_text(engine.get_intel_file("ZENITH_IDENTITY.md") or "", 900)
        manifesto = PromptForge._truncate_text(engine.get_intel_file("ZENITH_MANIFESTO.md") or "", 900)
        deep_knowledge = PromptForge._truncate_text(engine.get_intel_file("DEEP_KNOWLEDGE_VAULT.md") or "", 900)

        if skills_summary and isinstance(skills_summary, str) and skills_summary.strip():
            agent_profiles = PromptForge._truncate_text(skills_summary, 1000)
            project_wisdom = PromptForge._truncate_text(await PromptForge._load_project_wisdom(goal), 1000)
        else:
            agent_profiles_task = asyncio.create_task(PromptForge._synthesize_mindset(goal))
            project_wisdom_task = asyncio.create_task(PromptForge._load_project_wisdom(goal))
            agent_profiles, project_wisdom = await asyncio.gather(agent_profiles_task, project_wisdom_task)
            agent_profiles = PromptForge._truncate_text(agent_profiles, 1000)
            project_wisdom = PromptForge._truncate_text(project_wisdom, 1000)

        # [HYBRID-PROMPT-ENGINE]: Áp dụng Giao thức Prompt Kép Hybrid siêu tốc (1ms) cho mọi chế độ (DEEP & FAST)
        # Loại bỏ nút thắt cổ chai 3 bước gọi LLM-Forge (tốn >250s gây nghẽn CPU/VRAM)
        engine.publish_mission_log("FORGE", "[PROMPT-FORGE]: Đang áp dụng Giao thức Prompt Kép Hybrid siêu tốc (1ms).", "prompt_forge")
        return PromptForge.compile_hybrid_prompt(goal, soul, agent_profiles, project_wisdom)

prompt_forge = PromptForge()

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. v11.0*