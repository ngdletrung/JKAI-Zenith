import json
import logging
import os
import asyncio
from pathlib import Path
from core.utils.engine import engine
from core.utils import path_manager
from core.homunculus.manager import HomunculusManager

logger = logging.getLogger('PROMPT_FORGE')

class PromptForge:
    """
    JKAI ZENITH: XUONG DUC TU DUY VI MO (MACRO PROMPT FORGE)
    Nhiem vu: Chuyen hoa yeu cau tho thanh mot He tu tuong Chuyen gia Da nganh thua Master.
    Dam bao: "Thuc thi nhanh nhat - Ket qua chuan nhat moi yeu cau".
    """
    
    # [CẤU HÌNH ĐƯỜNG DẪN TĨNH THƯA MASTER]
    # Cho phép ghi đè từ biến môi trường, mặc định trỏ về kho chứa nội bộ
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
        return truncated + "\n...[TRUNCATED]"

    @staticmethod
    async def _synthesize_mindset(goal: str) -> str:
        """[DYNAMIC-SYNTHESIS]: Chat loc va hop nhat Linh hon Dac vu phu hop thua Master."""
        try:
            if not os.path.exists(PromptForge.AGENTS_DIR):
                return "No agent profiles found."

            # Liệt kê các Đặc vụ khả dụng một cách bất đồng bộ thưa Ngài
            agent_files = await asyncio.to_thread(
                lambda: [f for f in os.listdir(PromptForge.AGENTS_DIR) if f.endswith(".md")]
            )
            if not agent_files:
                return "Standard Zenith Soul Active."

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

            return "\n".join(profiles) if profiles else "Standard Zenith Soul Active."
        except Exception as e:
            logger.warning(f"[SYNTHESIS-ERR]: {e}")
            return "Standard Zenith Soul Active."

    @staticmethod
    async def _load_project_wisdom(goal: str) -> str:
        """[ZENITH-WISDOM]: Nap Ban nang va Ky nang tu tien hoa tu Homunculus thưa Master."""
        try:
            manager = HomunculusManager()
            manager.init_workspace()  # Tu dong khoi tao neu chua co
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
    async def forge_specialist_prompt(goal: str, context: dict = None, skills_summary: str = "", fast_mode: bool = False) -> str:
        """[SINGULARITY-FORGE]: Duc linh hon chuyen gia qua quy trinh 3 tang thua Master."""
        
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
        
        # [STAGE-1: DRAFTING] - Duc ban phac thao tri tue ELITE
        draft_prompt = f"""Ban la CHUYEN GIA THIET KE HE TU TUONG cua JKAI Zenith. 
Nhiem vu: Viet mot SYSTEM PROMPT toi thuong cho AI Agent dat hieu nang ELITE EXECUTIVE.

MUC TIEU CUA MASTER: "{goal}"

PHAN LUONG VI MO (MACRO DOMAIN):
- SOFTWARE ARCHITECTURE: Neu nhiem vu la lap trinh, hay kich hoat tu duy Cau truc va Algorithmic Precision.
- ELITE CONSULTING & RESEARCH: Neu nhiem vu la bao cao, thong ke, nghien cuu van phong, hay kich hoat tu duy Phan tich du lieu, Trinh bay dinh cao va Logic hoc thuat.
- STRATEGIC GOVERNANCE: Neu nhiem vu la quan tri he thong, hay kich hoat tu duy An ninh va Toi uu hoa ha tang.

BAN SAC CHU QUYEN (ZENITH SOVEREIGN IDENTITY):
{soul}

TUYEN NGON HE THONG (ZENITH MANIFESTO):
{manifesto}

DANH MUC NOI CAC DAC VU PHU HOP (DYNAMIC DNA):
{agent_profiles}

KHO TRI THUC CHUYEN SAU (DEEP KNOWLEDGE):
{deep_knowledge}

BAN NANG & KY NANG DU AN (PROJECT WISDOM - HOMUNCULUS):
{project_wisdom}

TAM TRU TRI THUC (THE SUPREME TRINITY v11.0):
1. SPIRIT: Chu quyen Vo bien - JKAI lam duoc TAT CA moi viec. Khong co gioi han, chi co giai phap.
2. STRUCTURE: Phan luong Nhat the - Tu dong tach nho nhiem vu de chay SONG SONG tren Ban Thuc Thi ALPHA va BETA de dat toc do than toc.
3. ACTION: Thuc thi nhanh nhat - Ket qua chuan nhat. Luon huong toi su hoan hao trong tung file bao cao hay tung dong code.

YEU CAU DUC LINH HON:
- Phai co phan <internal_monologue>: Dac vu phai tu chat van logic va tinh vi mo cua minh.
- Ngon tu: Tuyet doi chuyen nghiep, uy nghiem, khong dung buzzwords sao rong, tap trung vao gia tri thuc tien.
- Giao thuc Song ma: Luon tim cach phan ra nhiem vu de ALPHA va BETA cung lam viec dong thoi.
- Tuyet doi cam dung emoji: Phai ghi ro rang mot constraint la: "Tuyet doi cam su dung emoji trong bat ky phan hoi nao de dam bao tinh nghiem tuc va giam nhieu thong tin".
- Bao cao Tap doan: Khi lap bao cao hoac tong hop ket qua cong viec, bat buoc phai dinh dang dau ra theo cau truc 4 phan ro ret bang tieng Viet, tuyet doi khong viet tu do:
  I. TIEN DO THUC THI (CURRENT STATUS)
  II. CONG VIEC DA HOAN THANH (DELIVERABLES)
  III. RUI RO & KHO KHAN (RISK AUDIT)
  IV. DE XUAT TIEP THEO (NEXT ACTIONS)

KY LUAT THEP CUA HE THONG (SUPERPOWERS METHODOLOGY):
Dac vu nay BAT BUOC phai tuan thu cac ky luat sau trong moi hanh dong:
1. SYSTEMATIC DEBUGGING: Khong bao gio duoc phep doan bua va sua bua. Phai luon tim Root Cause, phan tich Pattern, dat Hypothesis truoc khi Fix. Neu fix hong 3 lan, phai chat van lai kien truc.
2. VERIFICATION BEFORE COMPLETION: Tuyet doi khong duoc tuyen bo "Hoan tat" hoac "Da sua xong" neu chua tu tay chay lenh kiem tra (Test/Build) va nhin thay bang chung terminal (Exit 0).
3. DOUBT-DRIVEN DEVELOPMENT (D3): Doi voi moi quyet dinh logic re nhanh, thay doi kien truc hoac tac vu rui ro cao, phai tu tao mot AI doc lap phan bien (Adversarial Review) bang cach trich xuat Hop dong (Contract) va tim kiem loi sai thay vi tu chap thuan.
4. ANTI-RATIONALIZATION: Tuyet doi khong tu bao chua bang cac ly do nhu "tac vu qua nho khong can test", "se viet test hoac bo sung tai lieu sau". Quy quy trinh la bat buoc va phai tuan thu 100%.
"""
        try:
            model_timeout = 90 if not fast_mode else 60

            # Duc lan 1 thua Master
            draft_soul = await PromptForge._safe_call_chat(
                messages=[{"role": "user", "content": draft_prompt}],
                role="PLANNER",
                task_id="forge_stage_1",
                timeout=model_timeout
            )
            if not isinstance(draft_soul, str) or not draft_soul.strip():
                draft_soul = "Standard Zenith Soul Active."
                logger.warning("[FORGE-FALLBACK] Draft stage returned empty or timed out, fallback to standard soul.")

            # [SHORT-CIRCUIT]: Neu la che do nhanh, tra ve ban phac thao ngay thưa Master
            if fast_mode:
                engine.publish_mission_log("FORGE", "[FAST-FORGE]: Da duc nhanh Linh hon Chuyen gia thua Master.", "prompt_forge")
                return draft_soul

            # [STAGE-2: ANALYTICAL CRITIQUE] - Trieu hoi Ban Phan bien thua Master
            stress_test_prompt = f"""Ban la CHUYEN GIA PHAN BIEN CHIEN LUOC cua JKAI Zenith. 
Hay tim ra 3 diem yeu chi mang trong ban System Prompt nay khien no khong the dat toi hieu nang toi uu:
---
{draft_soul}
---
Tra ve danh sach cac loi va cach khac phuc ngan gon."""
            
            critique = await PromptForge._safe_call_chat(
                messages=[{"role": "user", "content": stress_test_prompt}],
                role="CRITIC",
                task_id="forge_stage_2",
                timeout=model_timeout
            )
            if not isinstance(critique, str) or not critique.strip():
                critique = "No critique available due to timeout or model failure."
                logger.warning("[FORGE-FALLBACK] Critique stage returned empty, continuing with draft prompt.")

            # [STAGE-3: TEMPERING] - Tinh luyen linh hon toi thuong thua Master
            tempering_prompt = f"""Dua tren ban phac thao va cac phan bien sau, hay duc ket lai ban SYSTEM PROMPT cuoi cung dat toi hieu nang ELITE. 
Ban phac thao: {draft_soul}
Phan bien: {critique}

YEU CAU TOI THUONG: Phan hoi phai la mot KIET TAC TRI TUE, san sang cho Master LeeTrung phe duyet.
"""
            final_soul = await PromptForge._safe_call_chat(
                messages=[{"role": "user", "content": tempering_prompt}],
                role="PLANNER",
                task_id="forge_stage_3",
                timeout=model_timeout
            )
            if not isinstance(final_soul, str) or not final_soul.strip():
                final_soul = draft_soul
                logger.warning("[FORGE-FALLBACK] Final tempering stage failed, falling back to draft prompt.")

            engine.publish_mission_log("FORGE", "[SINGULARITY-FORGE]: Linh hon Chuyen gia da duoc tinh luyen qua 3 tang lua thua Master.", "prompt_forge")
            return final_soul
            
        except Exception as e:
            logger.error(f"[FORGE-ERR]: {e}")
            return f"Ban la JKAI Zenith. Muc tieu: {goal}. Hay hanh dong nhu mot chien binh Singularity thua Master!"

prompt_forge = PromptForge()

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. v11.0*