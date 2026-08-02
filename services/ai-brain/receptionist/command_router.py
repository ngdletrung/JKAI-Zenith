import re
import json
import os
import time
from core.utils.engine import engine
from core.utils.skill_selector import normalize_skill_name
from core.utils.models import TaskBudget

class CommandRouter:
    """
     TẬP ĐOÀN JKAI ZENITH - COMMAND ROUTER
    Quản lý các lệnh siêu tốc Bypass Cognitive Engine.
    """
    def __init__(self, redis_conn, http_client):
        self.redis_conn = redis_conn
        self.http_client = http_client

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except Exception: pass

    async def call_executor_tool(self, tool_name, tool_args, task_id, budget: TaskBudget = None):
        if budget is None:
            budget = TaskBudget()
        self._log("EXECUTOR", f"️ Thực thi: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})", task_id)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            resp = await self.http_client.post(f"{executor_url}/call_tool", json={
                "name": tool_name,
                "args": tool_args,
                "task_id": task_id
            })
            data = resp.json()
            if isinstance(data, dict):
                if data.get("status") == "error":
                    err_msg = data.get("msg") or data.get("output") or "Đã xảy ra lỗi không xác định."
                    return f" [EXECUTOR ERROR]: {err_msg}"
                
                output = data.get("output")
                if output is None:
                    output = data.get("msg") or data.get("response") or data.get("answer") or "No output."
                
                if isinstance(output, dict):
                    return output.get("output") or output.get("msg") or str(output)
                return str(output)
            return str(data)
        except Exception as e:
            return f"Error calling executor: {e}"

    def _clean_vn_accents(self, s: str) -> str:
        patterns = {
            '[àáảãạăằắẳẵặâầấẩẫậ]': 'a', '[èéẻẽẹêềếểễệ]': 'e', '[ìíỉĩị]': 'i',
            '[òóỏõọôồốổỗộơờớởỡợ]': 'o', '[ùúủũụưừứửữự]': 'u', '[ỳýỷỹỵ]': 'y', '[đ]': 'd'
        }
        res = s.lower()
        for p, r in patterns.items(): res = re.sub(p, r, res)
        return res

    async def process_command(self, cmd: str, args: str, task_id: str):
        """Định tuyến các siêu lệnh (Command Interceptor)"""
        cmd = cmd.lower()
        if cmd.startswith("/"):
            # Chuẩn hóa nhiều dấu gạch chéo dẫn đầu (VD: //help_secret -> /help_secret) thưa Master
            cmd = "/" + cmd.lstrip("/")
        if cmd in ["/search_skill", "/skill_search"]:
            res = await self._cmd_pillar_search("skills", args, task_id)
            return {"answer": res, "task_id": task_id, "sensitive": False}
        elif cmd in ["/run_skill", "/skill_run"]:
            res = await self._cmd_pillar_action("skills", "run", args, task_id)
            return {"answer": res, "task_id": task_id, "sensitive": True}
        elif cmd == "/search":
            res = await self._cmd_global_search(args, task_id)
            return {"answer": res, "task_id": task_id, "sensitive": False}
        elif cmd in ["/help", "/start"]:
            res = self._cmd_help()
            return {"answer": res, "task_id": task_id, "sensitive": False}
        elif cmd == "/shutdown":
            msg = "️ [SOVEREIGN]: Master đang yêu cầu TẮT HỆ THỐNG. Vui lòng nhập MẬT MÃ TỐI THƯỢNG vào bảng điều khiển."
            await self.call_executor_tool("request_sovereign_auth", {"action": "SHUTDOWN"}, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/self-destruct":
            msg = " [URGENT]: GIAO THỨC TỰ HỦY ĐÃ ĐƯỢC GỌI. Vui lòng nhấn APPROVE và NHẬP MẬT MÃ TỐI THƯỢNG."
            await self.call_executor_tool("request_sovereign_auth", {"action": "SELF_DESTRUCT"}, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/change-sovereign-key":
            msg = " [SECURITY]: Khởi động giao thức thay đổi mật mã chủ quyền."
            await self.call_executor_tool("request_sovereign_auth", {"action": "CHANGE_KEY"}, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/help_secret":
            res = self._cmd_help_secret()
            return {"answer": res, "task_id": task_id, "sensitive": True}
        elif cmd == "/sync":
            try:
                from core.tools.sync_pipeline import run_sync_pipeline
                result = await run_sync_pipeline(task_id)
                lines = [f" [SYNC] {result['msg']}"]
                for phase, info in result.get("phases", {}).items():
                    emoji = "" if info["status"] == "ok" else "️" if info["status"] == "skipped" else ""
                    msg = info.get("result", info.get("error", "?"))
                    if isinstance(msg, dict):
                        msg = msg.get("msg", str(msg))
                    lines.append(f"  {emoji} **{phase}**: {msg}")
                answer = "\n".join(lines)
            except Exception as pipe_err:
                answer = f"️ [SYNC-ERR]: {pipe_err}"
            return {
                "answer": answer,
                "task_id": task_id,
                "sensitive": True,
            }
        elif cmd == "/status":
            res = await self._cmd_status()
            return {"answer": res, "task_id": task_id, "sensitive": False}
        elif cmd == "/tusualoi":
            warrior_task_id = f"warrior_{int(time.time())}_auto_repair"
            args_dict = {
                "service_name": "System",
                "auto_repair": False,
                "instruction": "Giám định toàn diện hệ thống, đề xuất phương án khắc phục tối ưu.",
                "audit_intelligence": True,
                "task_id": warrior_task_id,
            }
            res = await self.call_executor_tool("skill_self_healing", args_dict, warrior_task_id)
            if not res or res.strip() == "" or res == "No output.":
                res = " [LỖI]: Tiến trình giám định không phản hồi (No output) thưa Master. Vui lòng kiểm tra nhật ký log của container hoặc thử lại."
            return {
                "answer": f" **[KẾ HOẠCH GIÁM ĐỊNH & KHẮC PHỤC]**\n\n{res}",
                "task_id": warrior_task_id,
                "sensitive": True,
            }
        elif cmd == "/tucaitien" or cmd.startswith("/tucaitien_"):
            warrior_task_id = f"warrior_{int(time.time())}_auto_improve"

            if cmd == "/tucaitien":
                skill_id = "System"
                optimization_goal = "Rà soát toàn diện hệ thống, đề xuất cải tiến tối ưu."
            else:
                raw_skill = cmd[len("/tucaitien_"):]
                skill_id = raw_skill
                optimization_goal = f"Rà soát và đề xuất cải tiến cho kỹ năng {skill_id}."

            args_dict = {
                "skill_id": skill_id,
                "optimization_goal": optimization_goal,
                "dry_run": True,
                "task_id": warrior_task_id,
            }
            res = await self.call_executor_tool("skill_tucaitien", args_dict, warrior_task_id)
            if not res or res.strip() == "" or res == "No output.":
                res = " [LỖI]: Tiến trình tự cải tiến không phản hồi (No output) thưa Master. Vui lòng kiểm tra nhật ký log của container hoặc thử lại."
            return {"answer": f" **[KẾ HOẠCH CẢI TIẾN]**\n\n{res}", "task_id": warrior_task_id, "sensitive": True}
        elif cmd in ["/cancel", "/cancle", "/stop"]:
            try:
                from core.utils.registry import registry
                control_plane_url = registry.get_service_url('control_plane')
                resp = await self.http_client.post(f"{control_plane_url}/commander/cancel")
                msg = resp.json().get("msg", "Đã gửi lệnh dừng.")
            except Exception as e:
                msg = f" Lỗi gửi lệnh dừng: {e}"
            self._log("ZENITH", msg, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd in ["/reset", "/clear"]:
            session_id = task_id
            if "_" in task_id:
                parts = task_id.split("_")
                if len(parts) >= 2: session_id = f"{parts[0]}_{parts[1]}"
            self.redis_conn.delete(f"chat_history:{session_id}")
            self.redis_conn.delete(f"chat_title:{session_id}")
            msg = " [PURGE-COMPLETE]: Lịch sử hội thoại đã được thanh tẩy thưa Master. Một khởi đầu mới đã sẵn sàng."
            self._log("BAN TRỢ LÝ", msg, task_id)
            return {"answer": msg, "task_id": task_id, "sensitive": True}
        elif cmd == "/insights":
            try:
                from core.qdrant_client import qdrant_client
                from core.utils.embed import embed
                vector = await embed.get_embedding_async("INSIGHT strategic memory", limit=1000)
                if vector:
                    memories = await qdrant_client.search_similar(vector, limit=5, collection="jkai_memory", filter_dict={"memory_type": "wisdom"})
                    if memories:
                        res = f"️ [TRUNG TÂM TRI THỨC - ĐÚC KẾT CHIẾN LƯỢC]:\n\n"
                        for m in memories:
                            payload = m.get('payload', {})
                            text = payload.get('text', '')[:150]
                            score = m.get('score', 0)
                            res += f"- **{payload.get('memory_type', 'wisdom')}**: {text}... (Score: {score:.2f})\n"
                    else:
                        res = " [CORTEX]: Không tìm thấy Insight chiến lược nào."
                else:
                    res = " [CORTEX]: Không tìm thấy Insight chiến lược nào."
            except Exception as e:
                res = f"️ [CORTEX ERROR]: {e}"
            return {"answer": res, "task_id": task_id, "sensitive": False}
        else:
            return {"answer": f"️ [ZENITH]: Không nhận diện được siêu lệnh `{cmd}` thưa Master. Gõ `/help` để xem danh sách.", "task_id": task_id, "sensitive": False}

    async def _cmd_pillar_search(self, pillar: str, query: str, task_id: str):
        if pillar != "skills":
            return f" [{pillar.upper()}]: Tìm kiếm chưa hỗ trợ cho trụ cột này."
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            deck.ensure_loaded()
            hits = deck.search(query or "", limit=15)
            if not hits:
                return f" Không tìm thấy kỹ năng cho `{query}`. Thử `/search_skill docker` hoặc `#số` (VD: #7001)."

            payload = []
            lines = [f" **TÌM KIẾM KỸ NĂNG** ({len(hits)} kết quả):\n"]
            for i, e in enumerate(hits, 1):
                payload.append({
                    "id": e.deck_id,
                    "name": e.title,
                    "registry_id": e.registry_id,
                    "display": e.display_id,
                })
                lines.append(
                    f"{i}. **{e.display_id}** — {e.title[:70]}\n"
                    f"   Registry: `{e.registry_id or 'chưa map'}`"
                )
            self.redis_conn.setex(f"session:last_search:{task_id}", 3600, json.dumps(payload, ensure_ascii=False))
            self.redis_conn.set(f"session:last_query:{task_id}", query or "")
            lines.append("\n Chạy: `/run_skill #7001` hoặc `/run_skill 1` (theo STT danh sách trên).")
            return "\n".join(lines)
        except Exception as e:
            return f" [SEARCH_SKILL]: {e}"

    async def _cmd_pillar_action(self, pillar: str, action: str, index_str: str, task_id: str):
        if pillar != "skills" or action not in ("run", "execute"):
            return f"️ Hành động `{action}` trên `{pillar}` chưa được hỗ trợ."

        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            deck.ensure_loaded()
            last_query = self.redis_conn.get(f"session:last_query:{task_id}") or "Thực thi kỹ năng theo lệnh Master"

            entry = None
            index_str = (index_str or "").strip()

            if index_str.startswith("#") or index_str.isdigit():
                ref = index_str.lstrip("#")
                entry = deck.resolve(ref)
                if not entry and index_str.startswith("#"):
                    entry = deck.resolve(index_str)
            else:
                raw = self.redis_conn.get(f"session:last_search:{task_id}")
                if raw:
                    results = json.loads(raw)
                    try:
                        idx = int(index_str) - 1
                        if 0 <= idx < len(results):
                            rid = results[idx].get("id") or results[idx].get("deck_id")
                            entry = deck.resolve(str(rid))
                    except ValueError:
                        pass

            if not entry:
                return (
                    f" Không tìm thấy kỹ năng `{index_str}`. "
                    "Dùng `/search_skill từ_khóa` hoặc `/run_skill #7001` (số trên MAP_SKILLS.md)."
                )
            if not entry.registry_id:
                return (
                    f" **{entry.display_id}** ({entry.title}) chưa map registry. "
                    "Cập nhật MAP_SKILLS cột Skill Con hoặc chạy `/sync`."
                )

            self._log("EXECUTOR", f" Chạy {entry.display_id} → `{entry.registry_id}`", task_id)
            obs = await self.call_executor_tool(
                entry.registry_id,
                {"query": last_query, "skill_id": entry.registry_id, "deck_ref": entry.display_id},
                task_id,
            )
            return (
                f" **{entry.display_id}** → `{entry.registry_id}`\n"
                f"_{entry.title}_\n\n{obs}"
            )
        except Exception as e:
            return f" [RUN_SKILL]: {e}"

    async def _cmd_global_search(self, query: str, task_id: str):
        """Global search — skills via Command Deck index; other pillars later."""
        q = (query or "").strip()
        if not q:
            return " Dùng `/search <từ khóa>` hoặc `/search_skill docker` hoặc `/search #1002`."
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            deck.ensure_loaded()
            hits = deck.search(q, limit=12)
            if hits:
                lines = [f" **TÌM KIẾM TOÀN CỤC (Kỹ năng)** — {len(hits)} kết quả cho `{q}`:\n"]
                for i, e in enumerate(hits, 1):
                    lines.append(
                        f"{i}. **{e.display_id}** — {e.title[:72]}\n"
                        f"   Registry: `{e.registry_id or 'chưa map'}`"
                    )
                lines.append("\n Chi tiết: `skill #1002 có gì hay` | Chạy: `/run_skill #7001`")
                return "\n".join(lines)
            return (
                f" Không tìm thấy kỹ năng cho `{q}`. "
                "Thử `/search_skill docker`, `/search #1002`, hoặc số 4 chữ số trên MAP_SKILLS.md."
            )
        except Exception as e:
            return f" [GLOBAL SEARCH]: {e}"

    def _cmd_help(self):
        return (
            "️ **JKAI ZENITH — COMMAND DECK**\n\n"
            "** HỆ THỐNG**\n"
            "- `/status` — Kiểm tra sức khỏe toàn bộ lõi AI\n"
            "- `/sync` — Đồng hóa tri thức (7 phase: import → cleanup)\n"
            "- `/reset` hoặc `/clear` — Xóa bộ nhớ ngữ cảnh\n"
            "- `/insights` — Trích xuất 10 tư duy chiến lược gần nhất\n"
            "- `/cancel` hoặc `/stop` — Ngắt khẩn cấp mọi tiến trình\n\n"
            "** IMPORT TRI THỨC**\n"
            "Thả file vào `files/Import/`, gõ `/sync`\n"
            "Hỗ trợ: `.md` `.txt` `.pdf` `.docx` `.csv` `.json` `.yaml` `.py` `.js` `.ts`\n"
            "Quy trình: chunk → embed → Qdrant `jkai_wiki` → phân loại tự động\n\n"
            "** SKILLS & COMMAND DECK**\n"
            "- `/search <từ khóa>` — Tìm kỹ năng toàn cục (VD: `/search docker`)\n"
            "- `/search_skill <từ khóa>` — Tra cứu Command Deck chi tiết\n"
            "- `/run_skill #<ID>` — Chạy kỹ năng theo mã MAP (VD: `/run_skill #7001`)\n"
            "- Tra cứu trực tiếp: `skill #1002 có gì hay`\n\n"
            "** CHẨN ĐOÁN & CẢI TIẾN**\n"
            "- `/tusualoi` — Giám định toàn diện, đề xuất khắc phục\n"
            "- `/tucaitien` — Rà soát toàn diện, đề xuất cải tiến\n"
            "- `/tucaitien_#<ID>` — Rà soát riêng một kỹ năng\n"
            "- Chat lỗi tự nhiên: \"sửa services/ai-brain/planner.py\" → tự DEEP\n\n"
            " Gõ `/help_secret` để xem Lệnh Đặc Quyền."
        )

    def _cmd_help_secret(self):
        return (
            " **LỆNH ĐẶC QUYỀN (SOVEREIGN)**\n"
            "*(Yêu cầu nhập Mật mã Tối thượng trên Web Dashboard)*\n\n"
            "- `/shutdown`:  Tắt toàn bộ hệ thống JKAI Zenith.\n"
            "- `/self-destruct`:  Giao thức tự hủy (Xóa toàn bộ dữ liệu).\n"
            "- `/change-sovereign-key`:  Thay đổi Mật mã Chủ quyền."
        )

    async def _cmd_status(self):
        try:
            import psutil, time, json, httpx
            import redis as redis_mod
            import os

            r = redis_mod.Redis(
                host=os.getenv("REDIS_HOST", "redis-ai"), port=6379,
                password=os.getenv("REDIS_PASSWORD"), decode_responses=True,
                socket_timeout=3,
            )

            cpu = psutil.cpu_percent(interval=0.3)
            ram = psutil.virtual_memory().percent
            now = time.strftime("%H:%M:%S")
            status = "OPTIMAL"
            details = []

            # Đọc pulse cache từ Redis (được ZenithPulse cập nhật mỗi 60s)
            cached = r.get("hardware_pulse_cache")
            if cached:
                try:
                    data = json.loads(cached)
                    health = data.get("health", {})
                    status = health.get("status", "OPTIMAL")
                    details = health.get("details", [])
                except Exception:
                    pass

            # Update Redis status real-time (override cached value)
            try:
                r.ping()
                redis_ok = True
            except Exception:
                redis_ok = False
            # Xoá dòng Redis cũ từ cache (nếu có) rồi thêm real-time
            details = [d for d in details if "Redis" not in d]
            details.append(" Redis AI: `Online` " if redis_ok else " Redis AI: `Offline` ")
            if not redis_ok:
                status = "DEGRADED"

            # Ollama VRAM
            try:
                client = engine._get_client()
                resp = await client.get("http://host.docker.internal:11434/api/ps", timeout=5.0)
                models = resp.json().get("models", [])
                if models:
                    vram = sum(m.get("size_vram", 0) for m in models) // 1048576
                    names = ", ".join(m["name"] for m in models)
                    details.append(f" Ollama: {names} | VRAM ~{vram}MB")
            except Exception:
                pass

            online = [l for l in details if "" in l]
            warns = [l for l in details if "️" in l]
            offline = [l for l in details if "" in l]

            header = " [ZENITH STATUS]" if status == "OPTIMAL" else " [ZENITH ALERT — DEGRADED]"
            footer = (
                "\n\n️ *Master, hệ thống đang mất ổn định!*"
                if status != "OPTIMAL" else
                "\n\n *Hệ thống JKAI ZENITH đang hoạt động ổn định, sẵn sàng phục vụ Master.*"
            )

            items = online + warns + offline
            service_block = "\n".join(f"- {l}" for l in items)

            return (
                f"{header}\n\n"
                f" CPU: {cpu:.1f}% | RAM: {ram:.1f}%\n\n"
                f" {now}\n\n"
                f"{service_block}"
                f"{footer}"
            )
        except Exception as e:
            return f" Không thể truy vấn trạng thái: {e}"
