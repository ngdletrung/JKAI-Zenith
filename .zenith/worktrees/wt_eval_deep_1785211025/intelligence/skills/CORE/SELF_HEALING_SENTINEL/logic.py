import os
import re
import subprocess
import json
import httpx
import asyncio
import time
from core.utils.engine import engine

class SelfHealing:
    """
    🧬 GIAO THỨC TỰ CHỮA LÀNH ZENITH (Unified Warrior Edition).
    Hội tụ linh hồn của Chiến binh Zenith vào một Siêu Kỹ năng duy nhất.
    """
    def __init__(self):
        from core.utils.registry import registry
        from core.utils import path_manager
        
        self.CORE_SERVICES = ["ai-brain", "ai-executor", "ai-control-plane"]
        try:
            self.SERVICES_MAP = {
                "ai-brain": f"{registry.get_service_url('brain').rstrip('/')}/health",
                "ai-executor": f"{registry.get_service_url('executor').rstrip('/')}/health",
                "ai-control-plane": f"{registry.get_service_url('control_plane').rstrip('/')}/health",
                "ai-browser": os.getenv("AI_BROWSER_URL", "http://ai-browser:8000/health"),
                "mission-control": os.getenv("MISSION_CONTROL_URL", "http://mission-control:5173")
            }
        except Exception:
            self.SERVICES_MAP = {
                "ai-brain": "http://ai-brain:8000/health",
                "ai-executor": "http://ai-executor:8000/health",
                "ai-control-plane": "http://ai-control-plane:8000/health",
                "ai-browser": "http://ai-browser:8000/health",
                "mission-control": "http://mission-control:5173"
            }

        # 🧠 [NEURAL-INTEGRATION]: Ket noi voi Bo nao va Do thi thua Master
        self.brain = None
        self.graph = None
        try:
            from core.utils.knowledge_brain import knowledge_brain
            self.brain = knowledge_brain
            
            # Dung dynamic import cho ai-brain vi co dau gach ngang
            import importlib.util
            import sys
            
            workspace_root = path_manager.get("WORKSPACE_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            brain_path = os.path.normpath(os.path.join(workspace_root, "services/ai-brain"))
            if brain_path not in sys.path:
                sys.path.append(brain_path)
                
            kg_path = os.path.normpath(os.path.join(brain_path, "knowledge_graph.py"))
            if os.path.exists(kg_path):
                spec = importlib.util.spec_from_file_location("knowledge_graph", kg_path)
                if spec is None or spec.loader is None:
                    print("⚠️ [SELF-HEALING]: Không thể tạo spec/loader cho knowledge_graph.py")
                else:
                    kg_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(kg_module)
                    self.graph = kg_module.get_universal_graph()
            else:
                print("⚠️ [SELF-HEALING]: Không tìm thấy knowledge_graph.py (có thể đang chạy trong Executor isolated container). Đồ thị sẽ bị tắt.")
        except Exception as e:
            print(f"⚠️ [SELF-HEALING-INIT]: Lỗi nạp đồ thị hoặc não bộ: {e}")

    async def _search_experiential_solution(self, error_msg: str):
        """🧠 [Q-RANK-HEALING]: Truy tìm toa thuốc từ tiền lệ."""
        if not self.brain: return "Không thể truy cập kho tri thức (Não bộ không khả dụng)."
        try:
            # Dung Q-Rank de tim cac nhiem vu tuong tu trong qua khu
            query = f"Lỗi: {error_msg}. Cách khắc phục và giải pháp kỹ thuật."
            res = await self.brain.ask(query, tier=1)
            return res if res else "Chưa có tiền lệ cho lỗi này."
        except Exception:
            return "Không thể truy cập kho tri thức."

    async def _trace_impact_via_graph(self, file_path: str):
        """🕸️ [GRAPH-DIAGNOSTIC]: Thấu thị sự ảnh hưởng qua Đồ thị."""
        if not self.graph: return "Đồ thị tri thức không khả dụng trong phân khu này."
        try:
            # Tim cac file lien quan den file dang loi
            base_name = os.path.basename(file_path)
            related = []
            if hasattr(self.graph, "search"):
                related = await self.graph.search(base_name, limit=5)
            elif hasattr(self.graph, "search_nodes"):
                related = await self.graph.search_nodes(base_name)
                
            if not related: return "Không tìm thấy liên kết đồ thị."
            
            impact_list = []
            for node in related[:5]:
                if isinstance(node, dict) and "payload" in node:
                    payload = node["payload"]
                    name = payload.get("name", "Unknown")
                    file_type = payload.get("file_type", "Unknown")
                    impact_list.append(f"- {name} ({file_type})")
                elif isinstance(node, dict):
                    name = node.get("name", "Unknown")
                    file_type = node.get("type", "Unknown")
                    impact_list.append(f"- {name} ({file_type})")
            return "\n".join(impact_list) if impact_list else "Không tìm thấy liên kết đồ thị cụ thể."
        except Exception as e:
            return f"Đồ thị đang trong trạng thái mờ đục: {str(e)}"

    async def _audit_all_logs(self):
        """🕵️ [FULL-SIEVE-AUDIT]: Vét cạn TOÀN BỘ nhật ký để tìm lỗi logic."""
        try:
            from core.redis_client import get_redis
            r = await asyncio.to_thread(get_redis)
            
            # Vét cạn toàn bộ lịch sử (500 dòng gần nhất)
            logs = await asyncio.to_thread(r.lrange, "monitor:log_history", 0, 499)
            if not logs: return "✅ Nhật ký trống, hệ thống đang ở trạng thái sơ khai."
            
            log_entries = []
            for l in logs:
                try:
                    data = json.loads(l)
                    log_entries.append(f"[{data.get('tag')}] {data.get('msg')}")
                except Exception: continue
            
            log_context = "\n".join(log_entries[-100:]) # Lấy 100 dòng cuối để AI phân tích sâu
            
            prompt = f"""
            [HỆ THỐNG GIÁM ĐỊNH TOÀN DIỆN JKAI - PHIÊN BẢN NHẤT THỂ]
            Nhiệm vụ: Phân tích nhật ký và đưa ra GIẢI PHÁP CHIẾN LƯỢC dựa trên Tiền lệ và Đồ thị.
            
            NHẬT KÝ CHIẾN TRƯỜNG:
            {log_context}
            
            YÊU CẦU: 
            1. Nếu phát hiện lỗi, hãy đối soát với Tri thức Q-Rank.
            2. Sử dụng Đồ thị để báo cáo vùng ảnh hưởng.
            """
            
            try:
                # 🛡️ Limit LLM calling time to 15s. If it exceeds or fails, fall back to linear log analysis.
                response = await asyncio.wait_for(
                    engine.call_chat(
                        messages=[{"role": "user", "content": prompt}], 
                        role="RECEPTIONIST",
                        lock_timeout=15
                    ),
                    timeout=15.0
                )
            except Exception as chat_err:
                response = "⚠️ [LOG-AUDIT-FALLBACK]: Không thể triệu tập Đặc vụ phân tích do nơ-ron bận hoặc timeout. Đã tự động kích hoạt chế độ quét logic tuyến tính.\n"
                errors_found = []
                for entry in log_entries[-30:]:
                    if any(x in entry.upper() for x in ["ERROR", "EXCEPTION", "CRITICAL", "FAIL"]):
                        errors_found.append(entry)
                if errors_found:
                    response += "🚨 **Phát hiện các điểm đứt gãy trong log:**\n" + "\n".join([f"• {err}" for err in errors_found[:5]])
                else:
                    response += "✅ Không phát hiện sự cố nghiêm trọng qua quét tuyến tính."
            
            # 🧠 [Q-RANK-INTEGRATION]: Tìm giải pháp cho lỗi nghiêm trọng nhất
            if "Error" in log_context or "Exception" in log_context:
                top_error = log_context.split("\n")[-1] # Lấy lỗi mới nhất
                solution = await self._search_experiential_solution(top_error)
                response += f"\n\n💡 **[PHƯƠNG THUỐC TỪ QUÁ KHỨ]**: {solution}"

            return response
        except Exception as e:
            return f"❌ [LOG-AUDIT-ERR]: {e}"

    def _audit_intelligence_stack(self) -> str:
        """Rà soát MAP / Command Deck / agents / registry (read-only)."""
        lines = ["\n📚 **RÀ SOÁT TRI THỨC (INTELLIGENCE):**"]
        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            deck = SkillDeckIndex.get()
            deck.ensure_loaded(force=True)
            unmapped = [e for e in deck._by_deck.values() if not e.registry_id]
            lines.append(f"- Command Deck: **{len(deck._by_deck)}** mục MAP, **{len(unmapped)}** chưa map registry.")
            if unmapped:
                sample = ", ".join(f"#{e.deck_id}" for e in unmapped[:12])
                lines.append(f"  • Ví dụ chưa map: {sample}" + (" …" if len(unmapped) > 12 else ""))
                lines.append("  • Gợi ý: `python scripts/repair_map_deck_links.py` hoặc sửa cột Skill Con trên MAP_SKILLS.md.")
            map_p = deck._map_path()
            lines.append(f"- MAP_SKILLS: `{map_p or 'NOT FOUND'}`")
        except Exception as e:
            lines.append(f"- Command Deck: ⚠️ {e}")

        try:
            agents_dir = None
            from core.config import settings
            from core.utils import path_manager
            intel = settings.INTELLIGENCE_DIR or path_manager.get("INTELLIGENCE_DIR")
            if intel:
                agents_dir = os.path.join(intel, "agents")
            if agents_dir and os.path.isdir(agents_dir):
                agent_files = sorted(
                    f for f in os.listdir(agents_dir)
                    if f.startswith("agent_") and f.endswith(".md")
                )
                lines.append(f"- Agents: **{len(agent_files)}** file `agent_*.md`.")
                for ghost in ("agent_strategist.md", "agent_master_graphic.md"):
                    if ghost not in agent_files:
                        lines.append(f"  • ⚠️ Thiếu soul: `{ghost}` (MAP_AGENTS có thể tham chiếu).")
            else:
                lines.append("- Agents: ⚠️ Không tìm thấy thư mục agents.")
        except Exception as e:
            lines.append(f"- Agents: ⚠️ {e}")

        try:
            reg_path = os.path.join(
                os.getenv("INTELLIGENCE_DIR", "/intelligence"),
                "registry_Map_skills.json",
            )
            if os.path.isfile(reg_path):
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg = json.load(f)
                skills = reg.get("skills", {})
                with_deck = sum(1 for s in skills.values() if s.get("deck_number"))
                lines.append(f"- Registry: **{len(skills)}** skills, **{with_deck}** có `deck_number`.")
            else:
                lines.append(f"- Registry: ⚠️ Không đọc được `{reg_path}`.")
        except Exception as e:
            lines.append(f"- Registry: ⚠️ {e}")

        return "\n".join(lines)

    def _intel_root(self) -> str:
        from core.config import settings
        from core.utils import path_manager
        intel = settings.INTELLIGENCE_DIR or path_manager.get("INTELLIGENCE_DIR")
        if intel and os.path.isdir(intel):
            return intel
        for cand in ("/intelligence", "/workspace/intelligence"):
            if os.path.isdir(cand):
                return cand
        return os.path.normpath(
            os.path.join(path_manager.get("WORKSPACE_ROOT") or path_manager.get_root(), "intelligence")
        )

    def _rebuild_deck_overrides(self) -> int:
        from core.utils.skill_deck_index import SkillDeckIndex, _MANUAL_DECK_OVERRIDES

        deck = SkillDeckIndex.get()
        SkillDeckIndex._instance = None
        deck = SkillDeckIndex.get()
        deck.ensure_loaded(force=True)
        overrides = dict(_MANUAL_DECK_OVERRIDES)
        added = 0
        for entry in deck._by_deck.values():
            if entry.registry_id:
                overrides.setdefault(entry.deck_id, entry.registry_id)
                continue
            rid, conf = deck._fuzzy_registry_match(entry.title, entry.keywords)
            if rid and conf >= 0.2:
                overrides[entry.deck_id] = rid
                added += 1
        out_path = os.path.join(self._intel_root(), "deck_registry_overrides.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(overrides, f, indent=2, ensure_ascii=False)
        return len(overrides)

    def _sync_agent_index_file(self) -> int:
        agents_dir = os.path.join(self._intel_root(), "agents")
        items = []
        for name in sorted(os.listdir(agents_dir)):
            if name.startswith("agent_") and name.endswith(".md"):
                items.append(name)
        payload = {
            "category": "agents",
            "count": len(items),
            "items": [{"id": n, "file": n, "path": f"agents/{n}"} for n in items],
        }
        out = os.path.join(agents_dir, "agent_index.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return len(items)

    def _ensure_ghost_agents(self) -> list:
        templates = {
            "agent_strategist.md": (
                "# JKAI Zenith: STRATEGIST SOUL\n\n"
                "Ban la Quan su chien luoc. Phan tich boi canh, de xuat phuong an va ke hoach hanh dong.\n"
            ),
            "agent_master_graphic.md": (
                "# JKAI Zenith: GRAPHIC MASTER SOUL\n\n"
                "Ban la chuyen gia thi giac. Mo ta prompt, layout va huong dan tool vision.\n"
            ),
        }
        agents_dir = os.path.join(self._intel_root(), "agents")
        os.makedirs(agents_dir, exist_ok=True)
        created = []
        for fname, body in templates.items():
            path = os.path.join(agents_dir, fname)
            if not os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(body)
                created.append(fname)
        return created

    async def _probe_failed_services(self) -> list:
        failed = []
        for name, url in self.SERVICES_MAP.items():
            if name == "mission-control":
                continue
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        failed.append(name)
            except Exception:
                failed.append(name)
        return failed

    async def _docker_restart(self, container: str) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "restart", container,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            except asyncio.TimeoutError:
                proc.kill()
                return "TIMEOUT after 120s"
            if proc.returncode == 0:
                return "OK"
            return (stderr.decode().strip() or stdout.decode().strip() or f"exit {proc.returncode}")[:200]
        except Exception as e:
            return str(e)[:200]

    async def _execute_remediation(self, task_id: str, allow_restart: bool = False) -> str:
        """Tự sửa an toàn sau giám định (không đụng sovereign key)."""
        engine.publish_mission_log(
            "ZENITH-WARRIOR", "🔧 [REMEDIATION]: Bắt đầu tự sửa theo lệnh Master...", task_id
        )
        lines = [
            "\n🔧 **TỰ SỬA (REMEDIATION):**",
            "🔒 *Chính sách:* Dùng `/tucaitien_<skill_id>` để tạo kế hoạch cải tiến skill, phê duyệt qua tab Kế Hoạch."
            "Sửa **repo** (services/core) khi có SyntaxError hoặc Master yêu cầu fix trong chỉ thị. "
            "Còn lại: JSON/MAP + hạ tầng.",
        ]

        try:
            from core.redis_client import get_redis
            r = await asyncio.to_thread(get_redis)
            sig = await asyncio.to_thread(r.get, "agent:stop_signal")
            if sig in ("true", "1", b"true", b"1"):
                await asyncio.to_thread(r.delete, "agent:stop_signal")
                lines.append("- Đã xóa `agent:stop_signal` (mở khóa thực thi).")
        except Exception as e:
            lines.append(f"- Redis stop-signal: ⚠️ {e}")

        try:
            from core.utils.skill_deck_index import SkillDeckIndex

            n_ov = self._rebuild_deck_overrides()
            SkillDeckIndex._instance = None
            deck = SkillDeckIndex.get()
            deck.ensure_loaded(force=True)
            before = sum(1 for e in deck._by_deck.values() if not e.registry_id)
            stats = deck.sync_registry_deck_numbers(write=True)
            after = sum(1 for e in deck._by_deck.values() if not e.registry_id)
            reg_path = deck._registry_path()
            from core.utils.sandbox_deploy_gate import validate_json_file
            v_ok, v_msg = validate_json_file(reg_path) if reg_path else (False, "no registry path")
            lines.append(
                f"- Command Deck: {n_ov} overrides, sync **{stats.get('updated', 0)}** registry, "
                f"unmapped **{before}→{after}**, validate JSON: {v_msg if v_ok else 'FAIL ' + v_msg}."
            )
        except Exception as e:
            lines.append(f"- Command Deck: ⚠️ {e}")

        try:
            n_agents = self._sync_agent_index_file()
            idx_path = os.path.join(self._intel_root(), "agents", "agent_index.json")
            from core.utils.sandbox_deploy_gate import validate_json_file
            v_ok, v_msg = validate_json_file(idx_path)
            lines.append(
                f"- `agent_index.json` tái sinh (**{n_agents}** agents), validate: {v_msg if v_ok else 'FAIL'}."
            )
        except Exception as e:
            lines.append(f"- agent_index: ⚠️ {e}")

        created = self._ensure_ghost_agents()
        if created:
            lines.append(f"- Tạo agent soul thiếu: {', '.join(created)}.")

        try:
            from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator

            orch = JKAIKnowledgeOrchestrator()
            if hasattr(orch, "sync_sovereign_registry"):
                await orch.sync_sovereign_registry()
                lines.append("- `registry_Map_skills.json` đồng bộ từ thư mục skills.")
        except Exception as e:
            lines.append(f"- Registry scan: ⚠️ {e}")

        from core.config import settings
        from core.utils import path_manager
        workspace_root = settings.WORKSPACE_ROOT or path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
        sandbox_path = os.path.normpath(os.path.join(workspace_root, "scratch/sandbox"))
        if not os.path.isdir(sandbox_path):
            try:
                os.makedirs(sandbox_path, exist_ok=True)
                lines.append(f"- Đã tạo sandbox: `{sandbox_path}`.")
            except Exception as e:
                lines.append(f"- Sandbox: ⚠️ {e}")

        if allow_restart:
            failed = await self._probe_failed_services()
            restart_map = {
                "ai-brain": ["ai-brain"],
                "ai-executor": ["ai-executor-1", "ai-executor-2"],
                "ai-control-plane": ["ai-control-plane"],
                "ai-browser": ["ai-browser"],
            }
            for svc in failed:
                for container in restart_map.get(svc, [svc]):
                    res = await self._docker_restart(container)
                    lines.append(f"- `docker restart {container}` → {res}")
            if not failed:
                lines.append("- Không có trụ cột down — bỏ qua restart.")
        else:
            failed = await self._probe_failed_services()
            if failed:
                lines.append(
                    f"- Trụ cột lỗi: {', '.join(failed)}. "
                    "Chạy `/tusualoi --fix` để docker restart (cần quyền socket)."
                )

        lines.append(
            "\n💡 Sửa **mã skill**: `/tucaitien_<skill_id>` — tạo kế hoạch cải tiến, "
            "phê duyệt qua tab Kế Hoạch.\n"
            "💡 Sửa **mã repo** (services/core): đã chạy trong block RÀ SOÁT REPO; "
            "file thử tại `scratch/sandbox/repo_candidates/`."
        )
        engine.publish_mission_log("ZENITH-WARRIOR", "✅ [REMEDIATION]: Hoàn tất.", task_id)
        return "\n".join(lines)

    async def skill_self_healing(
        self,
        service_name: str = "System",
        auto_repair: bool = False,
        task_id: str = "system",
        instruction: str = None,
        audit_intelligence: bool = True,
        **kwargs,
    ):
        """
        🛡️ TRIỆU HỒI CHIẾN BINH ZENITH: Giám định & Phục hồi Nhất thể.
        Luôn ở chế độ audit, kết quả lưu vào tab Kế Hoạch để Master phê duyệt.
        """
        if service_name.lower() in ["system", "all", "warrior", "kiểm tra", "zenith"]:
            result = await self.full_system_audit(
                task_id,
                auto_repair=False,
                instruction=instruction,
                audit_intelligence=audit_intelligence,
                allow_restart=False,
            )
        else:
            container_name = service_name
            if container_name == "brain":
                container_name = "ai-brain"
            elif container_name == "executor":
                container_name = "ai-executor-1"
            is_core = container_name in self.CORE_SERVICES or service_name in self.CORE_SERVICES

            report = [f"📊 [BÁO CÁO CHIẾN THUẬT]: Giám định Nhất thể cho `{service_name}`."]
            container_down = False
            try:
                impact = await self._trace_impact_via_graph(container_name)
                report.append(f"🕸️ [VÙNG ẢNH HƯỞNG]:\n{impact}")
                proc = await asyncio.create_subprocess_shell(
                    f"docker logs --tail 50 {container_name}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                try:
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
                    logs = stdout.decode()
                except asyncio.TimeoutError:
                    proc.kill()
                    logs = ""
                if "Error" in logs or "Exception" in logs:
                    report.append("⚠️ [TRẠNG THÁI]: Phát hiện dấu hiệu đứt gãy trong log.")
                else:
                    report.append("✅ [TRẠNG THÁI]: Container phản hồi log bình thường.")
            except Exception:
                container_down = True
                report.append(f"❌ [CRITICAL]: Container `{container_name}` không phản hồi.")
            msg = "\n".join(report)
            result = {
                "status": "success" if not container_down else "degraded",
                "is_core": is_core,
                "msg": msg,
            }

        plan_text = result.get("msg") or result.get("output") or str(result)
        try:
            from core.redis_client import get_redis
            r = await asyncio.to_thread(get_redis)
            if r:
                import json as _json
                proposal = {
                    "id": f"audit_{int(time.time())}",
                    "task_id": task_id,
                    "title": "Kế hoạch Giám định & Khắc phục Hệ thống",
                    "description": plan_text,
                    "source_module": "SELF_HEALING",
                    "proposal_type": "SYSTEM_AUDIT",
                    "is_red_zone": False,
                    "execute_goal": instruction or "Thực thi các bước khắc phục theo kế hoạch giám định.",
                    "metadata": {"full_report_length": len(plan_text)},
                    "status": "pending",
                    "created_at": time.time(),
                }
                await asyncio.to_thread(r.lpush, "zenith:proposals", _json.dumps(proposal, ensure_ascii=False))
                await asyncio.to_thread(r.publish, "monitor:proposal_channel", _json.dumps({"event": "proposal_created", "payload": proposal}, ensure_ascii=False))
        except ImportError:
            logger = logging.getLogger("SELF_HEALING")
            logger.warning("[REDIS] core.redis_client not available, skipping proposal save.")
        except Exception as e:
            logger = logging.getLogger("SELF_HEALING")
            logger.warning(f"[REDIS] Failed to save proposal: {e}")

        ok_count = sum(1 for line in plan_text.split('\n') if 'ON DINH' in line or 'PASS' in line or 'ONLINE' in line or 'Sach se' in line)
        warn_count = sum(1 for line in plan_text.split('\n') if 'CANH BAO' in line or 'PHAT HIEN' in line or 'co the' in line)
        err_count = sum(1 for line in plan_text.split('\n') if 'LOI' in line or 'NGAT KET NOI' in line or 'ERROR' in line)
        summary = (
            f"GIAM DINH HOAN TAT. An toan: {ok_count}, Canh bao: {warn_count}, Loi: {err_count}.\n"
            f"Xem chi tiet ke hoach khac phuc tai tab Ke Hoach."
        )
        return {"status": "success", "msg": summary}

    async def get_hardware_stats(self):
        """🌐 [TELEMETRY]: Thu thập nhịp tim phần cứng thực tế."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            return {"cpu": cpu, "ram": ram, "ts": time.time()}
        except Exception:
            return {"cpu": 0, "ram": 0, "ts": time.time()}

    async def full_system_audit(
        self,
        task_id: str,
        auto_repair: bool = False,
        instruction: str = None,
        audit_intelligence: bool = True,
        allow_restart: bool = False,
    ):
        """🏛️ [SUPREME-AUDIT]: Cuộc tổng duyệt binh lực của Master LeeTrung."""
        engine.publish_mission_log("ZENITH-WARRIOR", "🛡️ [CHIẾN BINH ZENITH]: Đang thực hiện Tổng giám định hệ thống theo lệnh Master...", task_id)
        
        sep = "\n\n---\n\n"
        sec = []
        sec.append("🏛️ BAO CAO TONG DUYET HE THONG ZENITH")
        if instruction:
            sec.append(f"📋 Chij thij Master: {instruction}")
        sec.append(sep)

        # 1. Kiểm tra nhịp tim các Trụ cột
        sec.append("## 1. TRANG THAI TRU COT\n| Service | Trang thai |\n| --- | --- |")
        for name, url in self.SERVICES_MAP.items():
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(url)
                    status = "ON DINH" if resp.status_code == 200 else f"LOI {resp.status_code}"
                    sec.append(f"| {name} | {status} |")
            except Exception:
                sec.append(f"| {name} | NGAT KET NOI |")
        
        # 2. Kiểm tra Thông số Phần cứng (NEW - Pulse Migration)
        sec.append("\n📟 **THÔNG SỐ PHẦN CỨNG (TELEMETRY):**")
        stats = await self.get_hardware_stats()
        sec.append(f"- **CPU Usage**: {stats['cpu']}%")
        sec.append(f"- **RAM Usage**: {stats['ram']}%")

        # 3. Kiểm tra Nơ-ron (Ollama)
        sec.append("\n🧠 **TRẠNG THÁI NƠ-RON (OLLAMA):**")
        try:
            from core.utils.registry import registry
            ollama_host = registry.get_service_url('ollama_gpu').replace("0.0.0.0", "127.0.0.1")
            async with httpx.AsyncClient(timeout=3.0) as client:
                ps = await client.get(f"{ollama_host}/api/ps")
                if ps.status_code == 200:
                    loaded = [m['name'] for m in ps.json().get('models', [])]
                    sec.append(f"- Đặc vụ đang nạp: {', '.join(loaded) if loaded else 'Không có'}")
                else:
                    sec.append("- Ollama: ⚠️ Không phản hồi")
        except Exception:
            sec.append("- Ollama: 🚨 Lỗi kết nối")

        engine.publish_mission_log("ZENITH-WARRIOR", "🕵️ Đang phân tích nhật ký chiến trường...", task_id)
        # 4. Tổng truy vết Nhật ký (The Big Sieve)
        sec.append("\n🕵️ **PHÂN TÍCH NHẬT KÝ CHIẾN TRƯỜNG (FULL SCAN):**")
        audit_res = await self._audit_all_logs()
        sec.append(audit_res)

        engine.publish_mission_log("ZENITH-WARRIOR", "💾 Đang kiểm tra hạ tầng dữ liệu...", task_id)
        # 5. Kiểm tra hạ tầng Redis & Database
        sec.append("\n💾 **HẠ TRẦNG DỮ LIỆU:**")
        try:
            from core.redis_client import get_redis
            r = await asyncio.to_thread(get_redis)
            ping = await asyncio.to_thread(r.ping)
            sec.append(f"- Redis (redis-ai): {'✅ ONLINE' if ping else '🚨 LỖI'}")
        except Exception: sec.append("- Redis (redis-ai): 🚨 NGẮT KẾT NỐI")

        # 6. HẠT NHÂN COGNITIVE KERNEL v6.0 & SANDBOX
        sec.append("\n⚙️ **HẠT NHÂN COGNITIVE KERNEL v6.0 & SANDBOX:**")
        
        # 6.1 Kiem tra trang thai co lap cua thu muc sandbox
        from core.config import settings
        from core.utils import path_manager
        workspace_root = settings.WORKSPACE_ROOT
        if not workspace_root or not os.path.exists(workspace_root):
            workspace_root = path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
        sandbox_path = os.path.normpath(os.path.join(workspace_root, "scratch/sandbox"))
        sandbox_status = "❌ KHÔNG TỒN TẠI"
        if os.path.exists(sandbox_path):
            if os.path.isdir(sandbox_path):
                test_file = os.path.join(sandbox_path, ".sandbox_write_test")
                try:
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write("sandbox_test")
                    os.remove(test_file)
                    sandbox_status = "✅ ONLINE (ĐÃ CÔ LẬP & CO WRITABLE)"
                except Exception as e:
                    sandbox_status = f"⚠️ LỖI QUYỀN GHI: {str(e)}"
            else:
                sandbox_status = "⚠️ ĐƯỜNG DẪN KHÔNG PHẢI THƯ MỤC"
        else:
            try:
                os.makedirs(sandbox_path, exist_ok=True)
                sandbox_status = "✅ ONLINE (ĐÃ KHỞI TẠO TỰ ĐỘNG)"
            except Exception as e:
                sandbox_status = f"🚨 KHÔNG THỂ KHỞI TẠO: {str(e)}"
        sec.append(f"- Sandbox Isolation Path: `{sandbox_path}` -> {sandbox_status}")

        # 6.2 Quet tep .bak trong thu muc intelligence/
        intelligence_dir = settings.INTELLIGENCE_DIR
        if not intelligence_dir or not os.path.exists(intelligence_dir):
            intelligence_dir = path_manager.get("INTELLIGENCE_DIR") or os.path.normpath(os.path.join(workspace_root, "intelligence"))
        bak_files = []
        if os.path.exists(intelligence_dir):
            for root, dirs, files in os.walk(intelligence_dir, topdown=True):
                # Prune heavy folders to avoid long walk or infinite loop in giant vaults
                dirs[:] = [d for d in dirs if d not in ['.obsidian', 'vault', '.git', '__pycache__']]
                for file in files:
                    if file.endswith('.bak'):
                        bak_files.append(os.path.join(root, file))
        
        if bak_files:
            sec.append(f"- Phát hiện {len(bak_files)} tệp sao lưu .bak vật lý từ các phiên phẫu thuật gián đoạn:")
            for bf in bak_files:
                sec.append(f"  • `{os.path.basename(bf)}` tại `{os.path.dirname(bf)}`")
            sec.append(
                "  💡 [HƯỚNG DẪN THỦ CÔNG]: Master có thể sử dụng các tệp .bak này để ghi đè ngược lại "
                "tệp chính nhằm khôi phục cấu hình ổn định cũ, hoặc tự tay xóa bỏ nếu không cần thiết."
            )
        else:
            sec.append("- Trạng thái tệp sao lưu (.bak): Sạch sẽ (0 tệp tồn đọng)")

        # 6.3 Truy vấn SQLite Event Store để tìm 3 sự cố đứt gãy nhận thức gần nhất
        import sqlite3
        db_path = os.path.normpath(os.path.join(workspace_root, "core/data/zenith_events.db"))
        sqlite_status = "Chưa kết nối"
        sqlite_failures = []
        if os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("""
                        SELECT hlc_timestamp, event_type, payload 
                        FROM events 
                        WHERE event_type LIKE '%fail%' 
                           OR event_type LIKE '%error%' 
                           OR event_type LIKE '%critical%'
                           OR payload LIKE '%fail%' 
                           OR payload LIKE '%error%'
                        ORDER BY hlc_timestamp DESC 
                        LIMIT 3
                    """)
                    sqlite_failures = [dict(row) for row in cursor.fetchall()]
                    sqlite_status = "✅ KẾT NỐI THÀNH CÔNG"
            except Exception as e:
                sqlite_status = f"🚨 LỖI TRUY VẤN: {str(e)}"
        else:
            sqlite_status = "⚠️ ĐỒNG BỘ SQLITE THẤT BẠI (FILE KHÔNG TỒN TẠI)"
            
        sec.append(f"- SQLite Event Store: {sqlite_status}")
        if sqlite_failures:
            sec.append("  • Nhật ký 3 sự cố đứt gãy nhận thức gần nhất:")
            for idx, err_event in enumerate(sqlite_failures, 1):
                hlc_ts = err_event.get("hlc_timestamp", "N/A")
                evt_type = err_event.get("event_type", "N/A")
                payload_raw = err_event.get("payload", "{}")
                try:
                    p_data = json.loads(payload_raw)
                    p_msg = p_data.get("msg") or p_data.get("error") or p_data.get("message") or payload_raw[:120]
                except Exception:
                    p_msg = payload_raw[:120]
                sec.append(f"    [{idx}] HLC Clock: {hlc_ts}")
                sec.append(f"        Loại lỗi: {evt_type}")
                sec.append(f"        Mô tả chi tiết: {p_msg}")
        else:
            sec.append("  • Nhật ký 3 sự cố đứt gãy gần nhất: Sạch sẽ (Không phát hiện sự cố)")

        if audit_intelligence:
            sec.append(self._audit_intelligence_stack())

        engine.publish_mission_log("ZENITH-WARRIOR", "📂 Đang rà soát mã nguồn...", task_id)
        try:
            from core.utils.repo_surgeon import (
                audit_repo,
                format_audit_report,
                propose_repo_patches,
                apply_repo_patches,
            )

            inst = instruction or "Rà soát repo JKAI"
            repo_data = audit_repo(inst)
            sec.append(format_audit_report(repo_data, inst))
            syn_n = len(repo_data.get("syntax_errors") or [])
            bug_n = len(repo_data.get("common_bugs") or [])
            engine.publish_mission_log("ZENITH-WARRIOR", f"✅ Rà soát xong: {syn_n} lỗi cú pháp, {bug_n} lỗi tiềm ẩn.", task_id)
            want_llm_fix = auto_repair and (
                syn_n > 0
                or bool(re.search(r"\b(sửa|sua|fix|patch|repo|mã|ma|code)\b", inst, re.I))
            )
            promoted_paths: list = []
            if want_llm_fix:
                patches = await propose_repo_patches(inst, repo_data, task_id=task_id)
                fix_block, promoted_paths = await apply_repo_patches(
                    patches, dry_run=False, task_id=task_id
                )
                sec.append(fix_block)
            elif auto_repair:
                sec.append(
                    "- Repo: không có SyntaxError / chỉ thị sửa code — bỏ qua LLM patch repo."
                )

            if not promoted_paths:
                from core.utils.post_patch_verify import verify_after_repair

                _v_ok, verify_block = verify_after_repair(
                    touched_rel_paths=[],
                    run_compileall=auto_repair,
                    run_tests=auto_repair,
                )
                sec.append(verify_block)
        except Exception as repo_err:
            sec.append(f"\n📂 **RÀ SOÁT REPO:** ⚠️ {repo_err}")

        if auto_repair:
            sec.append(
                await self._execute_remediation(task_id, allow_restart=allow_restart)
            )

        final_msg = "\n".join(sec)
        engine.publish_mission_log("ZENITH-WARRIOR", "✅ [GIÁM ĐỊNH XONG]: Báo cáo đã sẵn sàng.", task_id)

        if "🚨" in final_msg and not auto_repair:
            engine.publish_mission_log(
                "ZENITH-WARRIOR",
                "WARNING: Phát hiện sự cố. Chạy `/tusualoi` (mặc định tự sửa dữ liệu) hoặc `/tusualoi --fix`.",
                task_id,
            )

        # 📡 [TELEGRAM-REPORT]: Gửi báo cáo trực tiếp cho Master
        tg_token = os.getenv("TELEGRAM_TOKEN")
        master_id = os.getenv("MASTER_ID")
        if tg_token and master_id:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"https://api.telegram.org/bot{tg_token}/sendMessage", json={
                        "chat_id": master_id,
                        "text": f"🛡️ [CHIẾN BINH ZENITH]:\n{final_msg}"
                    })
            except Exception: pass
        
        return {"status": "success", "msg": final_msg}

# Instance cho Router
_instance = SelfHealing()
async def skill_self_healing(service_name: str = "System", auto_repair: bool = False, task_id: str = "system", **kwargs):
    _sk = {k: v for k, v in kwargs.items() if k not in ("service_name", "auto_repair", "task_id")}
    return await _instance.skill_self_healing(service_name, auto_repair, task_id, **_sk)


async def SELF_HEALING_SENTINEL(**kwargs):
    """Alias registry id → skill_self_healing."""
    return await skill_self_healing(**kwargs)
