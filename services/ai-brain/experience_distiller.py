import os
import json
import asyncio
import logging
import time as _time
from core.utils.engine import engine
from redis_client import redis_safe

logger = logging.getLogger("Distiller")

class ExperienceDistiller:
    """
    🧪 JKAI ZENITH: COGNITIVE DISTILLER
    Chuyên gia "đúc rút kim cương" từ nhật ký hành động.
    """
    def __init__(self):
        self.log_history_key = "monitor:log_history"
        self.base_intel_path = "/intelligence" if os.path.exists("/intelligence") else "D:/Docker/N8N/intelligence"
        self.pillars = [
            "skills", "agents", "rules", "knowledge", "prompts", 
            "commands", "tools", "protocols", "training", "vault", 
            "archive", "obsidian"
        ]

    async def distill_task(self, task_id: str, goal: str):
        logger.info(f"🧪 [DISTILLER] Analyzing task {task_id}: '{goal}'")
        
        # 1. Thu thập dữ liệu (Logs)
        logs = redis_safe(lambda r: r.lrange(self.log_history_key, 0, 100), [])
        relevant_logs = []
        for l in logs:
            try:
                data = json.loads(l)
                if data.get("task_id") == task_id or task_id == "manual":
                    relevant_logs.append(f"[{data.get('tag')}] {data.get('msg')}")
            except: pass
        
        if not relevant_logs:
            logger.warning("⚠️ [DISTILLER] No relevant logs found for distillation.")
            return

        # 2. Xây dựng Prompt phân tích Đa tầng thưa Master
        log_text = "\n".join(relevant_logs[::-1])
        prompt = f"""
        BẠN LÀ EXECUTOR - CHUYÊN GIA ĐÚC RÚT TRI THỨC JKAI ZENITH.
        Nhiệm vụ: Phân tích nhật ký của Task '{goal}' và chắt lọc tinh hoa vào 12 TRỤ CỘT TRI THỨC (ZENITH_12_PILLAR_PROTOCOL).
        
        DANH MỤC 12 TRỤ CỘT:
        1. SKILLS (Bộ Tứ Elite) | 2. AGENTS (Persona) | 3. RULES (SOP) | 4. KNOWLEDGE (⭐ Rating)
        5. PROMPTS (Templates) | 6. COMMANDS (Snippets) | 7. TOOLS (API) | 8. PROTOCOLS (Security)
        9. TRAINING (Data) | 10. VAULT (Context) | 11. ARCHIVE (Freeze) | 12. OBSIDIAN (Links)
        
        NHẬT KÝ THỰC THI:
        {log_text}
        
        TRẢ VỀ JSON CHUẨN:
        {{
            "action_type": "tên_pillar_thấp_phân",
            "lessons_learned": ["..."],
            "master_preferences": ["..."],
            "technical_patterns": ["..."],
            "suggested_rules": ["..."],
            "rating": 1-5
        }}
        """


        # 🛡️ [ABORT-CHECK]: Kiểm tra tín hiệu dừng trước khi gọi model nặng thưa Master
        if redis_safe(lambda r: r.get("agent:stop_signal")) in [b'true', 'true']:
            logger.info("🛑 [DISTILLER]: Master đã ngắt mạch. Hủy bỏ phiên chắt lọc thưa Master.")
            return

        # 🥇 GIAO THỨC TINH HOA: Sử dụng EXECUTOR với Profile ELITE để triệu hồi model mạnh nhất thưa Master
        distilled_data = await engine.call_chat(
            messages=[{"role": "system", "content": prompt}],
            role="EXECUTOR",
            profile="ELITE", # 💎 Ép buộc sử dụng nơ-ron mạnh nhất thưa Master
            json_mode=True,
            keep_alive=-1    # Giữ nơ-ron thường trú để chắt lọc liên tục
        )

        if isinstance(distilled_data, dict):
            # 🏛️ [SOVEREIGN GUARD INTEGRATION]: Nhất thể hóa vào Hiến pháp Chủ quyền thưa Master
            from core.utils.sovereign_guard import SovereignGuard
            guard = SovereignGuard("Zenith Distiller")
            
            summary = distilled_data.get("lessons_learned", ["Kết tinh tri thức mới"])[0][:100]
            approved = await guard.ensure_approval(
                task_id=task_id,
                action_desc=f"Kết tinh tri thức vào Trụ cột `{distilled_data.get('action_type', 'knowledge')}`: {summary}",
                is_core=True,
                req_type="APPROVE_DISTILL" # Loại phê duyệt chuẩn hóa cho Distiller thưa Master
            )
            
            if not approved:
                logger.info("🛑 [DISTILLER]: Master từ chối kết tinh tri thức này.")
                return

            # 🛡️ GIAO THỨC PHÂN LOẠI VĨ MÔ: Đưa tri thức về đúng Trụ cột thưa Master
            pillar = distilled_data.get("action_type", "knowledge").lower()
            if pillar not in self.pillars: pillar = "knowledge"
            
            await self._package_knowledge(distilled_data, goal, pillar)
            await self._update_registry(distilled_data, pillar)
            
            # 🚀 [SELF-EVOLUTION-TRIGGER]: Nếu phát hiện lỗi hệ thống, kích hoạt Tự phẫu thuật thưa Master
            if distilled_data.get("rating", 0) <= 2 or "error" in goal.lower() or "failure" in goal.lower():
                await self.propose_self_patch(task_id, goal, relevant_logs)

    async def propose_self_patch(self, task_id: str, goal: str, logs: list):
        """🏛️ [SELF-SURGERY]: Tự đề xuất bản vá mã nguồn để sửa lỗi logic thưa Master."""
        logger.info(f"🔬 [SELF-SURGERY] Đang phân tích lỗi để tự đề xuất bản vá cho Task {task_id}...")
        
        log_text = "\n".join(logs[-20:])
        patch_prompt = f"""
        BẠN LÀ KIẾN TRÚC SƯ TRƯỞNG JKAI ZENITH - CHUYÊN GIA TỰ PHẪU THUẬT (SELF-SURGERY).
        Hệ thống vừa gặp sự cố trong Task: '{goal}'.
        
        NHẬT KÝ LỖI:
        {log_text}
        
        NHIỆM VỤ:
        1. Xác định chính xác file nào trong `services/ai-brain/` hoặc `core/` đang gây lỗi.
        2. Viết một bản vá (Patch) để sửa lỗi đó mãi mãi.
        
        TRẢ VỀ JSON CHUẨN:
        {{
            "target_file": "đường_dẫn_file",
            "reason": "Giải thích tại sao lỗi thưa Master",
            "proposed_code": "Đoạn code mới hoàn chỉnh để thay thế đoạn lỗi",
            "impact": "Lợi ích sau khi phẫu thuật thưa Master"
        }}
        """
        
        try:
            patch_data = await engine.call_chat(
                messages=[{"role": "system", "content": patch_prompt}],
                role="PLANNER",
                profile="STRICT",
                json_mode=True,
                skip_memory=True
            )
            
            if isinstance(patch_data, dict) and patch_data.get("target_file"):
                from core.utils.sovereign_guard import SovereignGuard
                guard = SovereignGuard("Zenith Surgeon")
                
                # 🛡️ XIN MẬT LỆNH MASTER thưa Ngài
                approved = await guard.ensure_approval(
                    task_id=task_id,
                    action_desc=(
                        f"🔬 [TỰ PHẪU THUẬT]: Đề xuất sửa file `{patch_data['target_file']}`\n"
                        f"Lý do: {patch_data['reason']}\n"
                        f"Tác động: {patch_data['impact']}"
                    ),
                    is_core=True,
                    req_type="APPROVE_SELF_PATCH"
                )
                
                if approved:
                    # Ghi nhận đề xuất vào 00_Import để Master hoặc Antigravity thực thi thực tế thưa Master
                    # (Để an toàn, hiện tại chỉ lưu đề xuất để Master duyệt cuối cùng thưa Ngài)
                    import_path = os.path.join(self.base_intel_path, "vault/01_Surgical_Proposals")
                    os.makedirs(import_path, exist_ok=True)
                    proposal_file = f"patch_{int(_time.time())}.json"
                    with open(os.path.join(import_path, proposal_file), "w", encoding="utf-8") as f:
                        json.dump(patch_data, f, indent=2, ensure_ascii=False)
                        
                    engine.publish_mission_log("SURGEON", f"✅ [SELF-SURGERY]: Bản vá cho `{patch_data['target_file']}` đã được phê duyệt và lưu tại Vault.", task_id)
        except Exception as e:
            logger.error(f"❌ [SURGERY-ERR]: {e}")

    async def _package_knowledge(self, data: dict, goal: str, pillar: str):
        """Đóng gói tri thức vào 12 Trụ cột thưa Master"""
        lessons = "\n".join([f"- {l}" for l in data.get("lessons_learned", [])])
        prefs = "\n".join([f"- {p}" for p in data.get("master_preferences", [])])
        patterns = "\n".join([f"- {pt}" for pt in data.get("technical_patterns", [])])
        rules = "\n".join([f"- {r}" for r in data.get("suggested_rules", [])])
        
        content = f"# 🧪 JKAI EVOLUTION: {pillar.upper()} CHRYSTALIZATION\n\n"
        content += f"## 📚 Bài học thực chiến:\n{lessons}\n\n"
        content += f"## 💎 Profile Master:\n{prefs}\n\n"
        
        if patterns:
            content += f"## 🛠️ Pattern Kỹ thuật:\n{patterns}\n\n"
        if rules:
            content += f"## ⚖️ Quy tắc đề xuất:\n{rules}\n"

        # 1. Lưu vào Vault/00_Import để Assimilator xử lý tiếp thưa Master
        # Gán nhãn Pillar trong filename để Assimilator dễ nhận diện
        import_path = os.path.join(self.base_intel_path, "vault/00_Import")
        os.makedirs(import_path, exist_ok=True)
        filename = f"{pillar}_{int(_time.time())}.md"
        
        full_path = os.path.join(import_path, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # 2. Cập nhật trực tiếp vào Bản đồ Tri thức (MAP_*.md) thưa Master
        await self._update_map_file(pillar, data, goal)
        
        logger.info(f"💎 [DISTILLER] Knowledge crystallized and routed to Pillar: {pillar}")

    async def _update_registry(self, data: dict, pillar: str):
        """Cập nhật Registry trung tâm thưa Master"""
        registry_path = os.path.join(self.base_intel_path, "registry.json")
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            
            # Đảm bảo pillar tồn tại trong registry
            if pillar not in registry: registry[pillar] = {}
            
            item_id = f"DIST_{int(_time.time())}"
            registry[pillar][item_id] = {
                "name": data.get("lessons_learned", ["New Insight"])[0][:50],
                "type": pillar,
                "ts": _time.time(),
                "status": "crystallized"
            }
            registry["last_updated"] = int(_time.time())
            
            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ [REGISTRY-ERR] {e}")

    async def _update_map_file(self, pillar: str, data: dict, goal: str):
        """Cập nhật các file MAP_*.md thưa Master"""
        map_filename = f"MAP_{pillar.upper()}.md"
        map_path = os.path.join(self.base_intel_path, map_filename)
        
        if not os.path.exists(map_path): return
        
        try:
            new_entry = f"\n- ⭐⭐⭐ | **{goal[:50]}** | `Auto-Distilled` | {data.get('lessons_learned', [''])[0][:100]} |"
            with open(map_path, "a", encoding="utf-8") as f:
                f.write(new_entry)
        except: pass

distiller = ExperienceDistiller()
