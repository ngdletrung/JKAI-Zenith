import os
import json
import asyncio
import logging
import time as _time
from core.utils.engine import engine
from core.utils import path_manager
from redis_client import redis_safe

logger = logging.getLogger("Distiller")

class ExperienceDistiller:
    """
    🧪 JKAI ZENITH: COGNITIVE DISTILLER
    Chuyên gia "đúc rút kim cương" từ nhật ký hành động.
    """
    def __init__(self):
        self.log_history_key = "monitor:log_history"
        self.base_intel_path = "/intelligence" if os.path.exists("/intelligence") else path_manager.get("INTELLIGENCE_DIR", os.path.join(path_manager.get_root(), "intelligence"))
        self.pillars = [
            "skills", "agents", "rules", "knowledge", "prompts", 
            "commands", "tools", "protocols", "training", "vault", 
            "archive", "obsidian"
        ]

    async def is_system_idle(self) -> bool:
        """Kiểm tra tải hệ thống và số lượng tác vụ người dùng để nhường tài nguyên thưa Master."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            if cpu > 40 or mem > 70:
                logger.info("[EVOLVE-PREEMPT] Hệ thống bận (cpu=%s%%, mem=%s%%) — nhường tài nguyên.", cpu, mem)
                return False
        except Exception:
            pass
        try:
            active = redis_safe(lambda r: r.scard("active_tasks"), 0)
            if active and int(active) > 0:
                logger.info("[EVOLVE-PREEMPT] Phát hiện %s tác vụ người dùng đang chạy — nhường tài nguyên.", active)
                return False
        except Exception:
            pass
        return True

    async def distill_recent_tasks(self, max_tasks: int = 20):
        """🔄 [AUTO-DISTILL-ALL]: Tầm soát và đúc kết các task chạy gần đây thưa Master.
        
        Args:
            max_tasks: Giới hạn số task tối đa xử lý trong chu kỳ nếu rảnh.
        """
        logger.info("[DISTILLER] Bắt đầu quét tác vụ gần đây (max=%s)...", max_tasks)
        logs = redis_safe(lambda r: r.lrange(self.log_history_key, 0, 499), [])
        
        unique_tasks = {}
        # Quét log để trích xuất tất cả task IDs (cũ trước mới sau để gối đầu cuốn chiếu)
        for l in reversed(logs):
            try:
                data = json.loads(l)
                tid = data.get("task_id")
                msg = data.get("msg", "")
                if tid and tid not in ["system", "manual", "unknown"]:
                    if tid not in unique_tasks:
                        unique_tasks[tid] = msg
            except Exception: pass
            
        if not unique_tasks:
            logger.info("[DISTILLER] Không tìm thấy tác vụ nào trong nhật ký thưa Master.")
            return
            
        processed = 0
        for tid, goal in unique_tasks.items():
            if processed >= max_tasks:
                break
                
            # 🛡️ 1. GIAO THỨC TỰ NGẮT: Nhường tài nguyên ngay lập tức nếu hệ thống hết rảnh
            if not await self.is_system_idle():
                logger.info("[DISTILLER] Tự động ngắt nhường CPU/VRAM cho Master.")
                break
                
            # 🛡️ 2. CHECKPOINT: Bỏ qua nếu task này đã được đúc kết trước đó
            is_processed = redis_safe(lambda r: r.sismember("zenith:distilled_tasks", tid), False)
            if is_processed:
                continue
                
            logger.info("[DISTILLER] Tiến hành đúc kết nhiệm vụ cuốn chiếu: %s ('%s')", tid, goal)
            try:
                await asyncio.wait_for(
                    self.distill_task(tid, goal),
                    timeout=120,
                )
                # Đánh dấu đã hoàn tất đúc kết vào Redis Set
                redis_safe(lambda r: (
                    r.sadd("zenith:distilled_tasks", tid),
                    r.expire("zenith:distilled_tasks", 259200) # Hạn dùng 3 ngày để giải phóng bộ nhớ
                ))
                processed += 1
            except asyncio.TimeoutError:
                logger.warning("[DISTILLER] Timeout task %s, bỏ qua", tid)
            except Exception as e:
                logger.error("[DISTILLER-ERR] Lỗi task %s: %s", tid, e)

    async def distill_task(self, task_id: str, goal: str):
        logger.info("[DISTILLER] Analyzing task %s: '%s'", task_id, goal)
        
        # 1. Thu thập dữ liệu (Logs)
        logs = redis_safe(lambda r: r.lrange(self.log_history_key, 0, 499), [])
        relevant_logs = []
        for l in logs:
            try:
                data = json.loads(l)
                if data.get("task_id") == task_id or task_id == "manual":
                    relevant_logs.append(f"[{data.get('tag')}] {data.get('msg')}")
            except Exception: pass
        
        if not relevant_logs:
            logger.warning("[DISTILLER] No relevant logs found for distillation.")
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
            logger.info("[DISTILLER]: Master đã ngắt mạch. Hủy bỏ phiên chắt lọc thưa Master.")
            return

        # 🥇 GIAO THỨC TINH HOA: Sử dụng EXECUTOR với Profile ELITE để triệu hồi model mạnh nhất thưa Master
        distilled_data = await engine.call_chat(
            messages=[{"role": "system", "content": prompt}],
            role="EXECUTOR",
            profile="ELITE", # 💎 Ép buộc sử dụng nơ-ron mạnh nhất thưa Master
            json_mode=True,
            keep_alive=-1,    # Giữ nơ-ron thường trú để chắt lọc liên tục
            task_id="omni_evolve",
            stealth=True
        )

        if isinstance(distilled_data, dict):
            # 📋 [PLAN BOARD v2.0]: Lưu đề xuất vào Tab Kế Hoạch thay vì block HITL thưa Master
            from core.utils.sovereign_guard import SovereignGuard
            guard = SovereignGuard("OMNI-EVOLVE Distiller")
            
            pillar = distilled_data.get("action_type", "knowledge").lower()
            if pillar not in self.pillars: pillar = "knowledge"
            
            lessons = distilled_data.get("lessons_learned", [])
            summary = lessons[0][:120] if lessons else "Kết tinh tri thức từ kinh nghiệm thực chiến"
            
            description_parts = []
            if lessons:
                description_parts.append("**📚 Bài học:** " + "; ".join(lessons[:3]))
            prefs = distilled_data.get("master_preferences", [])
            if prefs:
                description_parts.append("**💎 Profile Master:** " + "; ".join(prefs[:2]))
            rules = distilled_data.get("suggested_rules", [])
            if rules:
                description_parts.append("**⚖️ Quy tắc đề xuất:** " + "; ".join(rules[:2]))
            
            # Gửi lên Tab Kế Hoạch — không block, trả về ngay
            await guard.submit_proposal(
                task_id=task_id,
                title=f"[OMNI-EVOLVE] Kết tinh tri thức Trụ cột: {pillar.upper()}",
                description="\n\n".join(description_parts) or summary,
                proposal_type="KNOWLEDGE_DISTILL",
                is_red_zone=False,  # Chỉ đồng hóa tri thức, không can thiệp hệ thống
                execute_goal=f"Đồng hóa tri thức mới vào Trụ cột {pillar}: {summary}",
                metadata={
                    "pillar": pillar,
                    "rating": distilled_data.get("rating", 3),
                    "distilled_data": distilled_data
                }
            )
            
            # 🚀 [SELF-EVOLUTION-TRIGGER]: Nếu phát hiện lỗi hệ thống, đề xuất Tự phẫu thuật thưa Master
            if distilled_data.get("rating", 0) <= 2 or "error" in goal.lower() or "failure" in goal.lower():
                await self.propose_self_patch(task_id, goal, relevant_logs)

    async def propose_self_patch(self, task_id: str, goal: str, logs: list):
        """🏛️ [SELF-SURGERY]: Tự đề xuất bản vá mã nguồn để sửa lỗi logic thưa Master."""
        logger.info("[SELF-SURGERY] Đang phân tích lỗi để tự đề xuất bản vá cho Task %s...", task_id)
        
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
                skip_memory=True,
                task_id="omni_evolve",
                stealth=True
            )
            
            if isinstance(patch_data, dict) and patch_data.get("target_file"):
                from core.utils.sovereign_guard import SovereignGuard
                guard = SovereignGuard("OMNI-EVOLVE Surgeon")
                
                # 📋 [PLAN BOARD v2.0]: Lưu vào Tab Kế Hoạch — Master quyết định khi rảnh thưa Ngài
                # is_red_zone=True vì can thiệp vào mã nguồn → cần mật khẩu lệnh khi phê duyệt
                target_file = patch_data['target_file']
                reason = patch_data.get('reason', 'Phát hiện lỗi logic')
                impact = patch_data.get('impact', 'Cải thiện hiệu suất hệ thống')
                proposed_code = patch_data.get('proposed_code', '')
                
                proposal_desc = (
                    f"**🎯 File cần sửa:** `{target_file}`\n\n"
                    f"**🔍 Lý do:** {reason}\n\n"
                    f"**✅ Tác động:** {impact}\n\n"
                    f"**💻 Code đề xuất:**\n```python\n{proposed_code[:500]}{'...' if len(proposed_code) > 500 else ''}\n```"
                )
                
                await guard.submit_proposal(
                    task_id=task_id,
                    title=f"[SELF-SURGERY] Đề xuất sửa file: {os.path.basename(target_file)}",
                    description=proposal_desc,
                    proposal_type="SELF_SURGERY",
                    is_red_zone=True,  # 🔴 Vùng đỏ — can thiệp mã nguồn, cần mật khẩu lệnh
                    execute_goal=f"Phẫu thuật file `{target_file}`: {reason}",
                    metadata=patch_data
                )
        except Exception as e:
            logger.error("[SURGERY-ERR]: %s", e)

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
        await asyncio.to_thread(os.makedirs, import_path, exist_ok=True)
        filename = f"{pillar}_{int(_time.time())}.md"
        
        full_path = os.path.join(import_path, filename)
        await asyncio.to_thread(self._write_file, full_path, content)
            
        # 2. Cập nhật trực tiếp vào Bản đồ Tri thức (MAP_*.md) thưa Master
        await self._update_map_file(pillar, data, goal)
        
        logger.info("[DISTILLER] Knowledge crystallized and routed to Pillar: %s", pillar)

    def _write_file(self, path: str, content: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _append_file(self, path: str, content: str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

    async def _update_registry(self, data: dict, pillar: str):
        """Cập nhật Registry trung tâm thưa Master"""
        registry_path = os.path.join(self.base_intel_path, "registry.json")
        try:
            def _sync_update():
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                
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
                return registry
            await asyncio.to_thread(_sync_update)
        except Exception as e:
            logger.error("[REGISTRY-ERR] %s", e)

    async def _update_map_file(self, pillar: str, data: dict, goal: str):
        """Cập nhật các file MAP_*.md thưa Master"""
        map_filename = f"MAP_{pillar.upper()}.md"
        map_path = os.path.join(self.base_intel_path, map_filename)
        
        if not await asyncio.to_thread(os.path.exists, map_path): return
        
        try:
            new_entry = f"\n- ⭐⭐⭐ | **{goal[:50]}** | `Auto-Distilled` | {data.get('lessons_learned', [''])[0][:100]} |"
            await asyncio.to_thread(self._append_file, map_path, new_entry)
        except Exception: pass

distiller = ExperienceDistiller()
