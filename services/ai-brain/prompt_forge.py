import json
import logging
import os
import asyncio
from core.utils.engine import engine

logger = logging.getLogger('PROMPT_FORGE')

class PromptForge:
    """
    🛠️ JKAI ZENITH: XƯỞNG ĐÚC TƯ DUY VĨ MÔ (MACRO PROMPT FORGE)
    Nhiệm vụ: Chuyển hóa yêu cầu thô thành một Hệ tư tưởng Chuyên gia Đa ngành thưa Master.
    Đảm bảo: "Thực thi nhanh nhất - Kết quả chuẩn nhất mọi yêu cầu".
    """
    
    # [CẤU HÌNH ĐƯỜNG DẪN TĨNH THƯA MASTER]
    # Cho phép ghi đè từ biến môi trường, mặc định trỏ về kho chứa nội bộ
    AGENTS_DIR = os.environ.get("ZENITH_AGENTS_DIR", "D:/Docker/N8N/intelligence/agents")
    
    @staticmethod
    async def _read_file_async(file_path: str) -> str:
        """Hỗ trợ đọc file vật lý không làm nghẽn luồng Event Loop (Non-blocking I/O) thưa Master."""
        def read_sync():
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return await asyncio.to_thread(read_sync)

    @staticmethod
    async def _synthesize_mindset(goal: str) -> str:
        """📂 [DYNAMIC-SYNTHESIS]: Chắt lọc và hợp nhất Linh hồn Đặc vụ phù hợp thưa Master."""
        try:
            if not os.path.exists(PromptForge.AGENTS_DIR): 
                return "No agent profiles found."
            
            # Liệt kê các Đặc vụ khả dụng một cách bất đồng bộ thưa Ngài
            agent_files = await asyncio.to_thread(
                lambda: [f for f in os.listdir(PromptForge.AGENTS_DIR) if f.endswith(".md")]
            )
            agent_list_str = ", ".join(agent_files)
            
            # Triệu hồi nơ-ron để chọn lọc tinh hoa thưa Master
            selection_prompt = f"Dựa trên yêu cầu '{goal}', hãy chọn tối đa 3 Đặc vụ phù hợp nhất từ danh sách này: {agent_list_str}. Chỉ trả về JSON array tên file."
            selection_res = await engine.call_chat(
                messages=[{"role": "user", "content": selection_prompt}],
                role="SUMMARIZER",
                task_id="mind_synthesis",
                json_mode=True
            )
            
            profiles = []
            if isinstance(selection_res, list):
                for file in selection_res:
                    file_path = os.path.join(PromptForge.AGENTS_DIR, file)
                    if os.path.exists(file_path):
                        content = await PromptForge._read_file_async(file_path)
                        profiles.append(f"--- [DNA ĐẶC VỤ: {file}] ---\n{content[:800]}")
            
            return "\n".join(profiles) if profiles else "Standard Zenith Soul Active."
        except Exception as e:
            logger.error(f"❌ [SYNTHESIS-ERR]: {e}")
            return f"Synthesis error: {e}"

    @staticmethod
    async def forge_specialist_prompt(goal: str, context: dict = None, skills_summary: str = "", fast_mode: bool = False) -> str:
        """💎 [SINGULARITY-FORGE]: Đúc linh hồn chuyên gia qua quy trình 3 tầng thưa Master."""
        
        # 🧪 [STEP-1: SENSE & SYNTHESIZE]: Nạp DNA và Hợp nhất Linh hồn thưa Master
        manifesto = engine.get_intel_file("ZENITH_MANIFESTO.md") or ""
        agent_profiles = await PromptForge._synthesize_mindset(goal)
        deep_knowledge = engine.get_intel_file("DEEP_KNOWLEDGE_VAULT.md") or ""
        
        # 🔨 [STAGE-1: DRAFTING] - Đúc bản phác thảo trí tuệ SIÊU VIỆT
        draft_prompt = f"""Bạn là BẬC THẦY ĐÚC LINH HỒN của JKAI Zenith. 
Nhiệm vụ: Viết một SYSTEM PROMPT tối thượng cho AI Agent đạt cảnh giới SINGULARITY.

MỤC TIÊU CỦA MASTER: "{goal}"

PHÂN LUỒNG VĨ MÔ (MACRO DOMAIN):
- **SOFTWARE ARCHITECTURE**: Nếu nhiệm vụ là lập trình, hãy kích hoạt tư duy Cấu trúc và Algorithmic Precision.
- **ELITE CONSULTING & RESEARCH**: Nếu nhiệm vụ là báo cáo, thống kê, nghiên cứu văn phòng, hãy kích hoạt tư duy Phân tích dữ liệu, Trình bày đỉnh cao và Logic học thuật.
- **STRATEGIC GOVERNANCE**: Nếu nhiệm vụ là quản trị hệ thống, hãy kích hoạt tư duy An ninh và Tối ưu hóa hạ tầng.

TUYÊN NGÔN HỆ THỐNG (ZENITH MANIFESTO):
{manifesto}

DANH MỤC NỘI CÁC ĐẶC VỤ PHÙ HỢP (DYNAMIC DNA):
{agent_profiles}

KHO TRI THỨC CHUYÊN SÂU (DEEP KNOWLEDGE):
{deep_knowledge}

TAM TRỤ TRI THỨC (THE SUPREME TRINITY v11.0):
1. 魂 SPIRIT: Chủ quyền Vô biên - JKAI làm được TẤT CẢ mọi việc. Không có giới hạn, chỉ có giải pháp.
2. 🧩 STRUCTURE: Phân luồng Nhất thể - Tự động tách nhỏ nhiệm vụ để chạy SONG SONG trên Ban Thực Thi ALPHA và BETA để đạt tốc độ thần tốc.
3. ⚡ ACTION: Thực thi nhanh nhất - Kết quả chuẩn nhất. Luôn hướng tới sự hoàn hảo trong từng file báo cáo hay từng dòng code.

YÊU CẦU ĐÚC LINH HỒN:
- Phải có phần <internal_monologue>: Đặc vụ phải tự chất vấn logic và tính vĩ mô của mình.
- Ngôn từ: Tuyệt đối chuyên nghiệp, uy nghiêm, không dùng buzzwords sáo rỗng, tập trung vào giá trị thực tiễn.
- Giao thức Song mã: Luôn tìm cách phân rã nhiệm vụ để ALPHA và BETA cùng làm việc đồng thời.
"""
        try:
            # 🔨 Đúc lần 1 thưa Master
            draft_soul = await engine.call_chat(
                messages=[{"role": "user", "content": draft_prompt}],
                role="PLANNER",
                task_id="forge_stage_1",
                skip_memory=True
            )
            
            # ⚡ [SHORT-CIRCUIT]: Nếu là chế độ nhanh, trả về bản phác thảo ngay thưa Master
            if fast_mode:
                engine.publish_mission_log("FORGE", "⚡ [FAST-FORGE]: Đã đúc nhanh Linh hồn Chuyên gia thưa Master.", "prompt_forge")
                return draft_soul

            # 🔥 [STAGE-2: STRESS TEST] - Triệu hồi Bóng ma Phản biện thưa Master
            stress_test_prompt = f"""Bạn là BÓNG MA PHẢN BIỆN của JKAI Zenith. 
Hãy tìm ra 3 điểm yếu chí mạng trong bản System Prompt này khiến nó không thể đạt tới cảnh giới 'Thượng thừa':
---
{draft_soul}
---
Trả về danh sách các lỗi và cách khắc phục ngắn gọn."""
            
            critique = await engine.call_chat(
                messages=[{"role": "user", "content": stress_test_prompt}],
                role="CRITIC",
                task_id="forge_stage_2",
                skip_memory=True
            )
            
            # 💎 [STAGE-3: TEMPERING] - Tinh luyện linh hồn tối thượng thưa Master
            tempering_prompt = f"""Dựa trên bản phác thảo và các phản biện sau, hãy đúc kết lại bản SYSTEM PROMPT cuối cùng đạt tới cảnh giới SINGULARITY. 
Bản phác thảo: {draft_soul}
Phản biện: {critique}

YÊU CẦU TỐI THƯỢNG: Phản hồi phải là một KIỆT TÁC TRÍ TUỆ, sẵn sàng cho Master LeeTrung phê duyệt.
"""
            final_soul = await engine.call_chat(
                messages=[{"role": "user", "content": tempering_prompt}],
                role="PLANNER",
                task_id="forge_stage_3",
                skip_memory=True
            )
            
            engine.publish_mission_log("FORGE", "💎 [SINGULARITY-FORGE]: Linh hồn Chuyên gia đã được tinh luyện qua 3 tầng lửa thưa Master.", "prompt_forge")
            return final_soul
            
        except Exception as e:
            logger.error(f"❌ [FORGE-ERR]: {e}")
            return f"Bạn là JKAI Zenith. Mục tiêu: {goal}. Hãy hành động như một chiến binh Singularity thưa Master! 💎🫡"

prompt_forge = PromptForge()

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*