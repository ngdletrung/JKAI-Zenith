import os
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
        self.CORE_SERVICES = ["ai-brain", "ai-executor", "ai-control-plane"]
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
            from core.config import settings
            brain_path = os.path.join(settings.WORKSPACE_ROOT, "services/ai-brain")
            if brain_path not in sys.path:
                sys.path.append(brain_path)
                
            kg_path = os.path.join(brain_path, "knowledge_graph.py")
            if os.path.exists(kg_path):
                spec = importlib.util.spec_from_file_location("knowledge_graph", kg_path)
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
        except:
            return "Không thể truy cập kho tri thức."

    async def _trace_impact_via_graph(self, file_path: str):
        """🕸️ [GRAPH-DIAGNOSTIC]: Thấu thị sự ảnh hưởng qua Đồ thị."""
        if not self.graph: return "Đồ thị tri thức không khả dụng trong phân khu này."
        try:
            # Tim cac file lien quan den file dang loi
            base_name = os.path.basename(file_path)
            # Gia su chung ta tim cac file co lien ket 'imported_by' hoac 'depends_on'
            related = await self.graph.search_nodes(base_name)
            if not related: return "Không tìm thấy liên kết đồ thị."
            
            impact_list = []
            for node in related[:5]:
                impact_list.append(f"- {node.get('name')} ({node.get('type')})")
            return "\n".join(impact_list)
        except:
            return "Đồ thị đang trong trạng thái mờ đục."

    async def _audit_all_logs(self):
        """🕵️ [FULL-SIEVE-AUDIT]: Vét cạn TOÀN BỘ nhật ký để tìm lỗi logic."""
        try:
            from redis_client import get_redis
            r = get_redis()
            
            # Vét cạn toàn bộ lịch sử (500 dòng gần nhất)
            logs = r.lrange("monitor:log_history", 0, 499)
            if not logs: return "✅ Nhật ký trống, hệ thống đang ở trạng thái sơ khai."
            
            log_entries = []
            for l in logs:
                try:
                    data = json.loads(l)
                    log_entries.append(f"[{data.get('tag')}] {data.get('msg')}")
                except: continue
            
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
            
            response = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}], 
                role="RECEPTIONIST",
                lock_timeout=45
            )

            # 🧠 [Q-RANK-INTEGRATION]: Tìm giải pháp cho lỗi nghiêm trọng nhất
            if "Error" in log_context or "Exception" in log_context:
                top_error = log_context.split("\n")[-1] # Lấy lỗi mới nhất
                solution = await self._search_experiential_solution(top_error)
                response += f"\n\n💡 **[PHƯƠNG THUỐC TỪ QUÁ KHỨ]**: {solution}"

            return response
        except Exception as e:
            return f"❌ [LOG-AUDIT-ERR]: {e}"

    async def skill_self_healing(self, service_name: str = "System", auto_repair: bool = False, task_id: str = "system"):
        """
        🛡️ TRIỆU HỒI CHIẾN BINH ZENITH: Giám định & Phục hồi Nhất thể.
        """
        if service_name.lower() in ["system", "all", "warrior", "kiểm tra", "zenith"]:
            return await self.full_system_audit(task_id)

        container_name = service_name
        is_core = service_name in self.CORE_SERVICES
        
        report = [f"📊 [BÁO CÁO CHIẾN THUẬT]: Giám định Nhất thể cho `{service_name}`."]
        
        try:
            # 🕸️ [GRAPH-AWARENESS]: Kiểm tra vùng ảnh hưởng
            impact = await self._trace_impact_via_graph(container_name)
            report.append(f"🕸️ [VÙNG ẢNH HƯỞNG]:\n{impact}")
            
            # 📜 Kiểm tra Docker Logs
            logs = subprocess.check_output(f"docker logs --tail 50 {container_name}", shell=True, stderr=subprocess.STDOUT).decode()
            if "Error" in logs or "Exception" in logs:
                report.append("⚠️ [TRẠNG THÁI]: Phát hiện dấu hiệu đứt gãy trong dòng chảy dữ liệu.")
            else:
                report.append("✅ [TRẠNG THÁI]: Đặc vụ đang vận hành ổn định về mặt vật lý.")
        except:
            report.append(f"❌ [CRITICAL]: Container `{container_name}` không phản hồi lệnh giám định.")

        if not auto_repair:
            return {
                "status": "waiting_approval",
                "is_core": is_core,
                "msg": "\n".join(report) + f"\n\n🛠️ [ĐỀ XUẤT]: Tái khởi động `{container_name}` để phục hồi công lực.",
                "proposal": f"docker restart {container_name}"
            }

        # ⚡ Thực thi Sửa chữa
        try:
            subprocess.run(f"docker restart {container_name}", shell=True, check=True)
            return {"status": "success", "msg": f"✅ [PHỤC HỒI XONG]: `{container_name}` đã hồi sinh và sẵn sàng!"}
        except Exception as e:
            return {"status": "error", "msg": f"🚨 [LỖI]: Không thể phục hồi `{container_name}`: {e}"}

    async def get_hardware_stats(self):
        """🌐 [TELEMETRY]: Thu thập nhịp tim phần cứng thực tế."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            return {"cpu": cpu, "ram": ram, "ts": time.time()}
        except:
            return {"cpu": 0, "ram": 0, "ts": time.time()}

    async def full_system_audit(self, task_id: str):
        """🏛️ [SUPREME-AUDIT]: Cuộc tổng duyệt binh lực của Master LeeTrung."""
        engine.publish_mission_log("ZENITH-WARRIOR", "🛡️ [CHIẾN BINH ZENITH]: Đang thực hiện Tổng giám định hệ thống theo lệnh Master...", task_id)
        
        final_report = ["🏛️ **BÁO CÁO TỔNG DUYỆT HỆ THỐNG ZENITH** 🏛️\n"]
        
        # 1. Kiểm tra nhịp tim các Trụ cột
        final_report.append("📡 **TRẠNG THÁI TRỤ CỘT:**")
        for name, url in self.SERVICES_MAP.items():
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(url)
                    status = "✅ ỔN ĐỊNH" if resp.status_code == 200 else f"⚠️ {resp.status_code}"
                    final_report.append(f"- {name}: {status}")
            except:
                final_report.append(f"- {name}: 🚨 NGẮT KẾT NỐI")
        
        # 2. Kiểm tra Thông số Phần cứng (NEW - Pulse Migration)
        final_report.append("\n📟 **THÔNG SỐ PHẦN CỨNG (TELEMETRY):**")
        stats = await self.get_hardware_stats()
        final_report.append(f"- **CPU Usage**: {stats['cpu']}%")
        final_report.append(f"- **RAM Usage**: {stats['ram']}%")

        # 3. Kiểm tra Nơ-ron (Ollama)
        final_report.append("\n🧠 **TRẠNG THÁI NƠ-RON (OLLAMA):**")
        try:
            ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434').replace("0.0.0.0", "127.0.0.1")
            async with httpx.AsyncClient(timeout=3.0) as client:
                ps = await client.get(f"{ollama_host}/api/ps")
                if ps.status_code == 200:
                    loaded = [m['name'] for m in ps.json().get('models', [])]
                    final_report.append(f"- Đặc vụ đang nạp: {', '.join(loaded) if loaded else 'Không có'}")
                else:
                    final_report.append("- Ollama: ⚠️ Không phản hồi")
        except:
            final_report.append("- Ollama: 🚨 Lỗi kết nối")

        # 4. Tổng truy vết Nhật ký (The Big Sieve)
        final_report.append("\n🕵️ **PHÂN TÍCH NHẬT KÝ CHIẾN TRƯỜNG (FULL SCAN):**")
        audit_res = await self._audit_all_logs()
        final_report.append(audit_res)

        # 5. Kiểm tra hạ tầng Redis & Database
        final_report.append("\n💾 **HẠ TRẦNG DỮ LIỆU:**")
        try:
            from redis_client import get_redis
            r = get_redis()
            ping = r.ping()
            final_report.append(f"- Redis (redis-ai): {'✅ ONLINE' if ping else '🚨 LỖI'}")
        except: final_report.append("- Redis (redis-ai): 🚨 NGẮT KẾT NỐI")

        final_msg = "\n".join(final_report)
        engine.publish_mission_log("ZENITH-WARRIOR", "✅ [GIÁM ĐỊNH XONG]: Báo cáo đã sẵn sàng.", task_id)
        
        # 🛡️ [AUTO-HEAL]: Tự động sửa lỗi nếu phát hiện Trụ cột sụp đổ
        if "🚨" in final_msg and "auto_repair" in task_id:
            engine.publish_mission_log("ZENITH-WARRIOR", "🚑 [AUTO-HEAL]: Phát hiện Trụ cột sụp đổ. Đang kích hoạt giao thức tái thiết...", task_id)
            for line in final_report:
                if "🚨" in line and ":" in line:
                    svc = line.split(":")[0].strip("- ")
                    await self.skill_self_healing(svc, auto_repair=True, task_id=task_id)

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
            except: pass
        
        return {"status": "success", "msg": final_msg}

# Instance cho Router
_instance = SelfHealing()
async def skill_self_healing(service_name: str = "System", auto_repair: bool = False, task_id: str = "system"):
    return await _instance.skill_self_healing(service_name, auto_repair, task_id)
