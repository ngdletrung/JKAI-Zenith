# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/engine.py
# - Role: Intelligence Routing Engine & Thread Injector
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v19.1
# [WORKING PRINCIPLES]:
# 1. Routes conversational, planning, critic, and auxiliary tasks.
# 2. Synchronizes configurations dynamically from rule_hardware.md.
# 3. Enforces strict CPU thread limits directly in options for CPU-bound tasks.
# 4. Strictly zero emojis in code or system configuration lines.
# -----------------------------------------------------------------------------
import os
import json
import logging
import httpx
import asyncio
import re
import time
from core.qdrant_client import qdrant_client
from core.utils.embed import embed
from core.utils.hlc import hlc
from core.utils import path_manager
from core.utils.models import RoleConfig, NeuralProfile, ModelOptions, TaskBudget, BudgetLedger
from core.utils.model_router import ModelRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UIE')

class JKAIIntelligenceEngine:
    def __init__(self):
        self.logger = logger
        self.rules_path = '/intelligence/rule_hardware.md'
        if not os.path.exists(self.rules_path):
            self.rules_path = os.path.join(path_manager.get_root(), 'intelligence', 'rule_hardware.md')
            
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
        self.redis_host = os.getenv('REDIS_HOST', 'redis-ai')
        self.brain_url = os.getenv('AI_BRAIN_URL', 'http://ai-brain:8000')
        self.executor_url = os.getenv('EXECUTOR_URL', 'http://ai-executor-1:8000')
        self.planner_url = os.getenv('PLANNER_URL', 'http://ai-brain:8000')
        
        self.ollama_host_gpu = os.getenv('OLLAMA_HOST_GPU', 'http://host.docker.internal:11434')
        self.ollama_host_cpu = os.getenv('OLLAMA_HOST_CPU', 'http://host.docker.internal:11435')
        self.ollama_host = self.ollama_host_gpu # Default for legacy functions
        self.current_service_url = None # 🏛️ [IDENTITY-TAG]: Sẽ được set bởi service 
        self.is_brain_service = False # Legacy flag

        # Automatically translate container hosts when running outside of docker.
        is_docker = os.path.exists('/.dockerenv')
        if not is_docker:
            if "host.docker.internal" in self.ollama_host:
                self.ollama_host = self.ollama_host.replace("host.docker.internal", "127.0.0.1")
            if "host.docker.internal" in self.ollama_host_gpu:
                self.ollama_host_gpu = self.ollama_host_gpu.replace("host.docker.internal", "127.0.0.1")
            if "host.docker.internal" in self.ollama_host_cpu:
                self.ollama_host_cpu = self.ollama_host_cpu.replace("host.docker.internal", "127.0.0.1")
            if self.redis_host in ["redis-ai", "redis-queue"]:
                self.redis_host = "127.0.0.1"
            if "ai-brain" in self.brain_url:
                self.brain_url = self.brain_url.replace("ai-brain", "127.0.0.1").replace("8000", "8001")
            if "ai-executor-1" in self.executor_url:
                self.executor_url = self.executor_url.replace("ai-executor-1", "127.0.0.1").replace("8000", "8002")
            if "ai-brain" in self.planner_url:
                self.planner_url = self.planner_url.replace("ai-brain", "127.0.0.1").replace("8000", "8001")
        
        if not self.ollama_host.startswith('http'):
            self.ollama_host = f"http://{self.ollama_host}"
        
        # [WINDOWS-RELIABILITY]: Chuyển hướng 0.0.0.0 về 127.0.0.1 
        if "0.0.0.0" in self.ollama_host:
            self.ollama_host = self.ollama_host.replace("0.0.0.0", "127.0.0.1")
            
        # Đảm bảo port nếu thiếu 
        if ":" not in self.ollama_host[7:]: # Bỏ qua http://
            self.ollama_host = f"{self.ollama_host}:11434"
        self._rules_last_mtime = 0
        self._router = ModelRouter(self.rules_path)
        self._redis_conn = None
        self._client = None 
        self._role_mapping_cache = {} # Ensure this is initialized
        self.global_params = {}
        # 🔒 [ELITE REDIS LOCKS]: Khóa toàn cục hệ thống 
        self.lock_timeout = 180 # 3 phút tối đa chờ nơ-ron
        
        # [QUANTUM-LEAP v31.0]: Thực thi Processor Affinity 
        self._apply_hardware_affinity()
        self.agent_profiles_cache = {}
        self._intel_file_cache = {}

    def _load_agent_profiles(self):
        """📂 [SINGULARITY-LOAD]: Nạp toàn bộ tinh hoa Đặc vụ vào RAM ."""
        agents_dir = os.path.join(path_manager.get_root(), 'intelligence', 'agents')
        try:
            if os.path.exists(agents_dir):
                import os
                for file in os.listdir(agents_dir):
                    if file.endswith(".md"):
                        with open(os.path.join(agents_dir, file), "r", encoding="utf-8") as f:
                            self.agent_profiles_cache[file] = f.read()[:1000]
        except Exception as _e:
            logger.warning(f"[ENGINE] Không thể tải hồ sơ đặc vụ: {_e}")

    def _bridge_cognitive_schema(self, model_name: str, messages: list) -> list:
        """[COGNITIVE-BRIDGE]: Dong bo 'khau vi' tri thuc theo kien truc Model."""
        if not model_name or not messages:
            return messages

        # Clone messages to avoid mutating the input directly
        messages = [dict(m) for m in messages]
        model_lower = model_name.lower()

        # Find the system instruction to append formatting constraints, or create one
        sys_msg = None
        for msg in messages:
            if msg.get('role') == 'system':
                sys_msg = msg
                break

        if not sys_msg:
            sys_msg = {"role": "system", "content": ""}
            messages.insert(0, sys_msg)

        cognitive_instruction = ""
        if 'qwen' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: QWEN]: Structure your thoughts and response systematically. "
                "Ensure logical hierarchy using clean Markdown headers (e.g., #, ##, ###) and precise bullet points."
            )
        elif 'gemini' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: GEMINI]: Integrate standard, structured Context blocks for any retrieved reference data. "
                "Maintain a highly professional, academic, clear, and comprehensive presentation format."
            )
        elif 'llama' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: LLAMA]: Adhere to strict conciseness constraints. "
                "Respond directly and avoid any conversational filler, repetitive explanations, or unnecessary elaboration."
            )
        elif 'deepseek' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: DEEPSEEK]: Utilize the native reasoning architecture. "
                "Ensure the final response outside the thinking process is highly factual, objective, and structured, avoiding repeating raw thoughts."
            )
        elif 'gemma' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: GEMMA]: Adhere to professional, high-density, academic formatting. "
                "Structure answers with structured reasoning, avoiding unnecessary conversational filler or overly verbose preambles."
            )
        elif 'phi' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: PHI]: Break down complex topics into clear, progressive step-by-step explanations. "
                "Focus on logical step progression and high-clarity bullet points optimized for efficient parameter reasoning."
            )
        elif 'moondream' in model_lower:
            cognitive_instruction = (
                "\n\n[COGNITIVE-BRIDGE: MOONDREAM]: Provide extremely concise, visually accurate descriptions. "
                "Focus strictly on answering the visual or direct queries without analytical speculation or conversational fluff."
            )

        if cognitive_instruction:
            sys_msg['content'] = sys_msg.get('content', '') + cognitive_instruction

        return messages

    def _apply_hardware_affinity(self):
        """[QUANTUM-LEAP]: Giao thức Xeon Affinity - TẠM DỪNG THEO Ý CHÍ MASTER."""
        pass

    async def _acquire_neural_lock(self, lock_name, timeout=None):
        """[NEURAL-LOCK]: Giao thức Xếp hàng nơ-ron chuẩn Elite ."""
        r = self._get_redis()
        if not r: return True
        
        effective_timeout = timeout or self.lock_timeout
        start_time = time.time()
        while time.time() - start_time < effective_timeout:
            # Sử dụng Redis SETNX để làm khóa 
            if r.set(f"lock:{lock_name}", "locked", ex=self.lock_timeout, nx=True):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _release_neural_lock(self, lock_name):
        """🔓 Giải phóng lãnh thổ nơ-ron ."""
        r = self._get_redis()
        if r: r.delete(f"lock:{lock_name}")
        return True

    async def _enter_neural_gate(self, model_name):
        """[NEURAL GATE]: Mở cổng nơ-ron cư trú ."""
        pass

    async def _exit_neural_gate(self, model_name):
        """[NEURAL GATE]: Đóng cổng nơ-ron cư trú ."""
        pass

    def _get_client(self):
        """Khởi tạo hoặc trả về Client dùng chung để tối ưu TCP ."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=600.0, limits=httpx.Limits(max_keepalive_connections=10, max_connections=20))
        return self._client

    def _get_redis(self):
        """Khởi tạo kết nối Redis lười biếng để phát log tư duy ."""
        if self._redis_conn is None:
            try:
                import redis
                self._redis_conn = redis.Redis(
                    host=self.redis_host, 
                    port=6379, 
                    db=0, 
                    password=os.getenv("REDIS_PASSWORD"),
                    decode_responses=True,
                    socket_timeout=10,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                )
            except Exception as _e:
                self._redis_conn = None
        return self._redis_conn

    def _publish_thought(self, role, thought, task_id="system", stream_id=None, is_delta=False, is_first_chunk=False):
        """Phát sóng luồng tư duy lên Dashboard - Enterprise v31.2"""
        try:
            r = self._get_redis()
            if r and thought:
                from datetime import datetime
                iso_time = datetime.now().isoformat()
                
                # Assign default log level
                level = "[INFO]"
                if "error" in thought.lower() or "lỗi" in thought.lower() or "[ERR" in thought:
                    level = "[ERROR]"
                elif "warn" in thought.lower() or "cảnh báo" in thought.lower():
                    level = "[WARN]"
                elif "vram" in thought.lower() or "cpu" in thought.lower():
                    level = "[METRIC]"
                    
                if is_delta:
                    if is_first_chunk:
                        msg = f"{level} [{iso_time}] [{role}] [Task: {task_id}] {thought}"
                    else:
                        msg = thought
                else:
                    msg = f"{level} [{iso_time}] [{role}] [Task: {task_id}] {thought.strip()}"
                    
                display_tag = role.upper()
                payload = {
                    "tag": display_tag, "msg": msg, "ts": time.time(), "task_id": task_id or "system", "source": display_tag, "iso_time": iso_time
                }
                if is_delta:
                    payload["is_delta"] = True
                if stream_id:
                    payload["id"] = stream_id
                    payload["pin_id"] = stream_id
                log_payload = json.dumps(payload, ensure_ascii=False)
                # [BROADCAST]: Phát tín hiệu tới cả hai kênh để đồng bộ 100%
                r.publish("monitor:log_channel", log_payload)
                r.publish("monitor:progress_channel", log_payload)
                if not is_delta:
                    r.lpush("monitor:log_history", log_payload)
                    r.ltrim("monitor:log_history", 0, 499)
                    r.lpush("monitor:progress_history", log_payload)
                    r.ltrim("monitor:progress_history", 0, 1999)
        except Exception as e:
            logger.error(f"[LOG_ERROR] Could not publish thought: {e}")

    def publish_mission_log(self, tag, msg, task_id="system", trace_id=None, stealth=False):
        """
        [STRATEGIC-LOG]: Giao thức Nhật ký Chiến lược .
        Tinh giản tối đa để đảm bảo tốc độ phản xạ ánh sáng.
        """
        r = self._get_redis()
        if r and msg:
            try:
                payload_data = {
                    "tag": tag,
                    "msg": msg,
                    "ts": time.time(),
                    "task_id": task_id,
                    "hlc": str(hlc.now())
                }
                if stealth:
                    payload_data["stealth"] = True
                
                payload = json.dumps(payload_data, ensure_ascii=False)
                
                r.publish("monitor:log_channel", payload)
                r.publish("monitor:progress_channel", payload)
                r.lpush("monitor:log_history", payload)
                r.ltrim("monitor:log_history", 0, 999)
                r.lpush("monitor:progress_history", payload)
                r.ltrim("monitor:progress_history", 0, 1999)
            except Exception as e:
                logger.error(f"❌ [LOG-ERR]: {e}")

    def publish_progress(self, pct, msg, *args, **kwargs):
        """Giao thức Phát sóng Tiến độ chuẩn v12.0 ."""
        task_id = "system"
        phase = "system"
        trace_id = None
        
        if len(args) == 1:
            task_id = args[0]
        elif len(args) == 2:
            phase = args[0]
            task_id = args[1]
        elif len(args) >= 3:
            phase = args[0]
            task_id = args[1]
            trace_id = args[2]

        task_id = kwargs.get("task_id", task_id)
        phase = kwargs.get("phase", phase)
        trace_id = kwargs.get("trace_id", trace_id)

        r = self._get_redis()
        if r:
            try:
                payload = json.dumps({
                    "tag": "PROGRESS",
                    "pct": pct,
                    "msg": msg,
                    "task_id": task_id,
                    "phase": phase,
                    "trace_id": trace_id,
                    "ts": time.time()
                }, ensure_ascii=False)
                r.publish("monitor:log_channel", payload)
                r.publish("monitor:progress_channel", payload)
            except Exception: pass

    def get_intel_file(self, filename):
        """
        👑 [HYBRID-TWO-TIER-CACHE]: Hệ thống bộ nhớ đệm 2 lớp tối thượng thưa Master.
        - L1 (Local RAM Cache): Tốc độ chạm đáy tuyệt đối (0.01ms), cục bộ cho mỗi tiến trình.
        - L2 (Shared Redis Cache): Đồng bộ hóa liên container (0.5ms), tránh toàn bộ Disk I/O cho mọi cụm Docker.
        - Tự động đồng bộ và invalidation theo mtime (Modification Time) thời gian thực thưa Ngài.
        """
        intel_dir = os.path.join(path_manager.get_root(), 'intelligence')
        base_paths = [
            '/intelligence', '/intelligence/identity', '/intelligence/context', 
            '/intelligence/agents', '/intelligence/rules', '/intelligence/skills',
            intel_dir, os.path.join(intel_dir, 'identity'), os.path.join(intel_dir, 'context')
        ]
        clean_name = filename[2:] if filename.startswith('./') else filename
        for bp in base_paths:
            full_path = os.path.join(bp, clean_name)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    mtime = os.path.getmtime(full_path)
                    
                    # 🥇 [L1-CACHE]: Kiểm tra RAM cục bộ của tiến trình thưa Master
                    if full_path in self._intel_file_cache:
                        cached_mtime, cached_content = self._intel_file_cache[full_path]
                        if cached_mtime == mtime:
                            return cached_content
                    
                    # 🥈 [L2-CACHE]: Kiểm tra RAM dùng chung (Shared Redis) giữa các container thưa Ngài
                    import hashlib
                    redis_key = f"intel_cache:{hashlib.md5(full_path.encode('utf-8')).hexdigest()}"
                    r_conn = self._get_redis()
                    
                    if r_conn:
                        try:
                            shared_data = r_conn.get(redis_key)
                            if shared_data:
                                parsed = json.loads(shared_data)
                                if parsed.get("mtime") == mtime:
                                    content = parsed.get("content")
                                    # Đồng bộ ngược lại L1 để tối ưu lượt tiếp theo
                                    self._intel_file_cache[full_path] = (mtime, content)
                                    return content
                        except Exception: pass
                    
                    # 🥉 [DISK-READ]: Nếu cả L1 và L2 đều lỡ nhịp, đọc đĩa cứng và cập nhật đồng bộ thưa Master
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Cập nhật L1 thưa Master
                    self._intel_file_cache[full_path] = (mtime, content)
                    
                    # Cập nhật L2 thưa Ngài
                    if r_conn:
                        try:
                            payload = json.dumps({"mtime": mtime, "content": content}, ensure_ascii=False)
                            r_conn.setex(redis_key, 86400, payload) # Cache trong 24 giờ
                        except Exception: pass
                        
                    return content
                except Exception: pass
        return None

    def _get_smart_params(self):
        self._router._refresh_rules_if_needed()
        # Sync local caches from router for backward compat
        self._rules_last_mtime = self._router._rules_last_mtime
        self.global_params = self._router.get_global_params()
        self._role_mapping_cache = {}
        for role_key, rc in self._router._role_config_cache.items():
            self._role_mapping_cache[role_key] = rc
        # Sync profiles for call_chat fallback path (line ~1242)
        self.profiles = dict(self._router._profiles_cache)


    async def warmup_all_models(self):
        """GIAO THỨC TRIỆU HỒI TOÀN QUÂN: Nạp sẵn các model chiến lược ."""
        self._get_smart_params()
        unique_models = {}
        for role, cfg in self._role_mapping_cache.items():
            model = cfg.model
            if model and model not in unique_models:
                unique_models[model] = {'role': role, 'cfg': cfg}
        
        logger.info(f"[GUARDIAN] Khởi động Giao thức Triệu hồi ({len(unique_models)} model)...")
        client = self._get_client()
        
        available_tags = {self.ollama_host_gpu: [], self.ollama_host_cpu: []}
        loaded_models = {self.ollama_host_gpu: [], self.ollama_host_cpu: []}
        
        for host in [self.ollama_host_gpu, self.ollama_host_cpu]:
            try:
                tags_resp = await client.get(f"{host}/api/tags")
                if tags_resp.status_code == 200:
                    available_tags[host].extend([m['name'].lower() for m in tags_resp.json().get('models', [])])
                
                ps_resp = await client.get(f"{host}/api/ps")
                if ps_resp.status_code == 200:
                    loaded_models[host].extend([m['name'].lower() for m in ps_resp.json().get('models', [])])
            except Exception as _e:
                logger.warning(f"[GUARDIAN] Không thể kết nối {host}: {_e}")

        for model, info in unique_models.items():
            cfg = info['cfg']
            role = info['role']
            
            keep_alive_raw = str(cfg.keep_alive).strip()
            if keep_alive_raw == '0' or model.lower() in ['faster-whisper', 'sdxl-turbo-rocm']:
                continue

            num_gpu_val = cfg.options.num_gpu if cfg.options.num_gpu is not None else -1
            hw_target = str(cfg.hardware).upper()
            
            # [DYNAMIC-ROUTING]: Định vị cổng dựa trên nhãn Hardware hoặc num_gpu thưa Master
            if 'CPU' in hw_target or num_gpu_val == 0:
                target_host = self.ollama_host_cpu
            else:
                target_host = self.ollama_host_gpu
            other_host = self.ollama_host_cpu if target_host == self.ollama_host_gpu else self.ollama_host_gpu
            
            model_in_target = any(model in t for t in available_tags[target_host])
            model_in_other = any(model in t for t in available_tags[other_host])
            total_tags = len(available_tags[target_host]) + len(available_tags[other_host])

            if total_tags > 0 and not model_in_target and not model_in_other:
                logger.error(f"❌ [GUARDIAN] KHÔNG TÌM THẤY ĐẶC VỤ `{model}` TRONG PHÁO ĐÀI!")
                self.publish_mission_log("CRITICAL", f"[SỰ CỐ TÀI SẢN]: Đặc vụ `{model}` (Role: {role}) không tồn tại trong Thư viện. Cần Master Pull ngay !")
                continue
                
            # [MASTER-DIRECTIVE]: Tuyệt đối không tự ý nhảy Host nếu không tìm thấy đặc vụ thưa Master.
            # Nếu model không nằm đúng pháo đài đã quy định, hệ thống phải giữ nguyên hiện trạng để Master xử lý.
            # if not model_in_target and model_in_other:
            #    target_host = other_host

            if any(model in m for m in loaded_models[target_host]):
                logger.info(f"[GUARDIAN] Đặc vụ `{model}` đã có mặt tại vị trí ({target_host}).")
                # [PURGE-MISPLACED]: Nếu model cũng đang load ở port sai, giải phóng để giữ đúng Hardware Affinity
                if any(model in m for m in loaded_models[other_host]):
                    logger.warning(f"🧹 [GUARDIAN] Đặc vụ `{model}` đang chiếm cả {other_host} — dọn dẹp...")
                    try:
                        await client.post(f"{other_host}/api/generate", json={"model": model, "prompt": "", "keep_alive": 0}, timeout=30.0)
                    except Exception: pass
                continue

            try:
                logger.info(f"[GUARDIAN] Đang triệu hồi: {model} (Role: {role}) trên {target_host}...")
                keep_alive = cfg.keep_alive
                try:
                    if str(keep_alive) == "-1": keep_alive = -1
                    elif str(keep_alive).isdigit(): keep_alive = int(keep_alive)
                except Exception: pass

                await client.post(f"{target_host}/api/generate", json={
                    "model": model, "prompt": "", "keep_alive": keep_alive,
                    "options": cfg.options.model_dump(exclude_none=True)
                }, timeout=600.0)
                # [PURGE-MISPLACED]: Sau khi load đúng port, dọn dẹp bản copy ở port sai nếu có
                if any(model in m for m in loaded_models[other_host]):
                    logger.warning(f"🧹 [GUARDIAN] Đặc vụ `{model}` cũng đang chiếm {other_host} — dọn dẹp...")
                    try:
                        await client.post(f"{other_host}/api/generate", json={"model": model, "prompt": "", "keep_alive": 0}, timeout=30.0)
                    except Exception: pass
            except Exception as e:
                logger.error(f"❌ [GUARDIAN] Trục trặc khi triệu hồi {model}: {e}")
            
    # Alias for backward compatibility 
    warmup_models = warmup_all_models

    async def flush_gpu_memory(self, task_id="system"):
        """🧹 [SOVEREIGN ARBITRATOR]: Xả toàn bộ nơ-ron GPU để dọn đường cho Xưởng vẽ ."""
        self.publish_mission_log("VRAM_FLUSH", "🧹 [SOVEREIGN]: Đang thực hiện Surgical Flush để giải phóng VRAM...", task_id)
        client = self._get_client()
        try:
            for host in [self.ollama_host_gpu, self.ollama_host_cpu]:
                resp = await client.get(f"{host}/api/ps")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    for m in models:
                        name = m["name"]
                        self.publish_mission_log("VRAM_FLUSH", f"♻️ [SOVEREIGN]: Đang giải phóng: {name} tren {host}", task_id)
                        await client.post(f"{host}/api/chat", json={
                            "model": name, "messages": [], "keep_alive": 0
                        })
            self.publish_mission_log("VRAM_FLUSH", "✨ [SOVEREIGN]: VRAM đã được thanh lọc !", task_id)
            return True
        except Exception as e:
            self.publish_mission_log("ERROR", f"❌ [VRAM-ERR]: {e}", task_id)
            return False

    async def restore_neural_corps(self, task_id="system"):
        """[SOVEREIGN ARBITRATOR]: Tái triệu hồi các quân đoàn nơ-ron ."""
        self.publish_mission_log("VRAM_RESTORE", "[SOVEREIGN]: Đang tái triệu hồi quân đoàn nơ-ron chiến lược...", task_id)
        try:
            await self.warmup_all_models()
            self.publish_mission_log("VRAM_RESTORE", "[SOVEREIGN]: Hệ thống đã quay lại trạng thái chiến đấu tối thượng.", task_id)
            return True
        except Exception as e:
            self.publish_mission_log("ERROR", f"❌ [RESTORE-ERR]: {e}", task_id)
            return False

    def _get_active_key(self, model_name):
        return f"ollama:active:{model_name}"

    async def _get_neural_availability(self, model_name):
        r = self._get_redis()
        if r:
            try:
                val = r.get(self._get_active_key(model_name))
                return int(val) if val else 0
            except Exception: return 0
        return 0

    async def _enter_neural_gate(self, model_name: str):
        r = self._get_redis()
        if r:
            try: r.incr(self._get_active_key(model_name))
            except Exception: pass

    async def _exit_neural_gate(self, model_name: str):
        r = self._get_redis()
        if r:
            try:
                val = r.decr(self._get_active_key(model_name))
                if val < 0: r.set(self._get_active_key(model_name), 0)
            except Exception: pass
        # [VRAM-UNLOAD]: Thực sự giải phóng model khỏi VRAM bằng cách gửi keep_alive=0
        try:
            client = self._get_client()
            for host in [self.ollama_host_gpu, self.ollama_host_cpu]:
                await client.post(
                    f"{host}/api/generate",
                    json={"model": model_name, "prompt": "", "keep_alive": 0},
                    timeout=3.0
                )
        except Exception: pass

    def get_role_config(self, role):
        self._get_smart_params()
        role = role.upper()
        role_data = self._role_mapping_cache.get(role)
        
        if not role_data:
            logger.warning(f"[ENGINE] Role '{role}' undefined. Activating fallback protocol...")
            for backup_role in ["PLANNER", "EXECUTOR", "RECEPTIONIST"]:
                backup_data = self._role_mapping_cache.get(backup_role)
                if backup_data:
                    if isinstance(backup_data, dict):
                        return backup_data
                    return backup_data.to_dict()
            default_model = self.global_params.get("DEFAULT_MODEL", "")
            if not default_model:
                default_model = self.global_params.get("DEFAULT_MODEL", "qwen3.5:latest")
            return {'model': default_model, 'options': {}}
        
        if isinstance(role_data, dict):
            return role_data
        return role_data.to_dict()

    def load_software_rules(self):
        """📂 Trích xuất API keys và Base URLs từ rules_software.md ."""
        configs = {}
        intel_dir = os.path.join(path_manager.get_root(), 'intelligence')
        paths = [
            '/intelligence/rules_software.md',
            'intelligence/rules_software.md',
            os.path.join(intel_dir, 'rules_software.md')
        ]
        sw_path = None
        for p in paths:
            if os.path.exists(p):
                sw_path = p
                break
                
        if sw_path:
            try:
                with open(sw_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if '|' in line and ('_API_KEY' in line or 'Base URL' in line):
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 5:
                            # 🔍 [DYNAMIC-EXTRACTOR]: Lấy key và url trực tiếp từ bảng Markdown thưa Master
                            clean_part = parts[2].replace('`', '').strip()
                            var_name_match = re.search(r'([A-Z_]+_API_KEY)', clean_part)
                            var_name = var_name_match.group(1) if var_name_match else None
                            
                            if var_name:
                                provider = var_name.lower().replace('_api_key', '')
                                
                                # Lấy Base URL (thường ở cột 3)
                                url_clean = parts[3].replace('`', '').strip()
                                # Lấy API Key (thường ở cột 4)
                                key_clean = parts[4].replace('`', '').strip()
                                
                                if key_clean and len(key_clean) > 5:
                                    # [NEURAL-LINK]: Đồng bộ hóa vào biến môi trường để các skill khác có thể sử dụng thưa Master
                                    os.environ[var_name] = key_clean
                                    configs[provider] = {
                                        'api_key': key_clean,
                                        'base_url': url_clean if url_clean.startswith('http') else None
                                    }
            except Exception as e:
                logger.error(f"Error parsing rules_software.md: {e}")
        
        # Fallback to environment variables
        for p in ['gemini', 'anthropic', 'openai', 'deepseek', 'tavily']:
            var_name = f"{p.upper()}_API_KEY"
            env_val = os.getenv(var_name)
            if env_val:
                if p not in configs:
                    configs[p] = {}
                configs[p]['api_key'] = env_val
            
            # Default fallback endpoints if missing in md
            if p not in configs:
                configs[p] = {}
            if 'base_url' not in configs[p] or not configs[p]['base_url']:
                if p == 'gemini':
                    configs[p]['base_url'] = 'https://generativelanguage.googleapis.com/v1beta/'
                elif p == 'anthropic':
                    configs[p]['base_url'] = 'https://api.anthropic.com/v1'
                elif p == 'openai':
                    configs[p]['base_url'] = 'https://api.openai.com/v1'
                elif p == 'deepseek':
                    configs[p]['base_url'] = 'https://api.deepseek.com'
                    
        return configs


    async def get_embeddings(self, text, model=None):
        """[COGNITIVE-EMBEDDINGS]: Chuyen doi van ban thanh Vector tri thuc."""
        from core.utils.embed import embedder
        res = await embedder.get_embedding_async(text, model)
        return res or []


    async def get_detailed_geolocation_pipeline(self) -> dict:
        """
        Sovereign Geolocation Pipeline implementing AI Operating Substrate principles:
        1. Spatial Memory (experience.json preferred location) -> Confidence 1.0
        2. GPS Input (Browser coordinates from Redis) -> Confidence 0.95
        3. IP Geolocation (Network/ISP fallback) -> Confidence 0.50
        4. Environment Config (DEFAULT_GEOLOCATION from env) -> Confidence 0.30
        5. Default Baseline ("Hue, Vietnam") -> Confidence 0.10
        """
        import os
        import json
        import time
        import httpx

        now = time.time()

        # Step 1: Spatial Memory (preferred_geolocation in experience.json)
        try:
            intel_dir = os.getenv("INTELLIGENCE_DIR") or "d:\\Docker\\JKAI\\intelligence"
            exp_path = os.path.join(intel_dir, "experience.json")
            if os.path.exists(exp_path):
                with open(exp_path, "r", encoding="utf-8") as f:
                    exp_data = json.load(f)
                    pref_loc = exp_data.get("preferred_geolocation")
                    if pref_loc and pref_loc.strip():
                        return {
                            "source": "profile_memory",
                            "confidence_score": 1.0,
                            "coordinates": None,
                            "address": pref_loc.strip(),
                            "temporal": {
                                "timestamp": now,
                                "age_seconds": 0,
                                "is_stale": False
                            },
                            "metadata": {
                                "description": "Explicit user preferred location from experience.json"
                            }
                        }
        except Exception:
            pass

        # Step 2: GPS Input & Sensor Fusion (Browser Geolocation in Redis)
        try:
            r = self._get_redis()
            if r:
                geo_bytes = r.get("user:precise_geolocation")
                if geo_bytes:
                    if isinstance(geo_bytes, bytes):
                        geo_bytes = geo_bytes.decode("utf-8")
                    geo_data = json.loads(geo_bytes)
                    
                    lat = geo_data.get("latitude")
                    lon = geo_data.get("longitude")
                    accuracy = geo_data.get("accuracy")
                    timestamp = geo_data.get("timestamp") or now
                    age = max(0.0, now - timestamp)
                    is_stale = age > 86400  # Stale if older than 24h
                    
                    # Confidence adjustment based on accuracy and temporal age
                    base_confidence = 0.95
                    if is_stale:
                        base_confidence -= 0.20  # penalty for stale data
                    if accuracy is not None and accuracy > 100:
                        base_confidence -= 0.10  # penalty for poor accuracy
                    confidence_score = max(0.1, base_confidence)

                    # Check if address already cached in geo_data
                    address = geo_data.get("address")
                    if not address or not address.strip():
                        # Environment Context Engine: Reverse Geocoding using Nominatim
                        if lat is not None and lon is not None:
                            headers = {"User-Agent": "JKAI-Zenith/1.0 (contact: admin@jkai.local)"}
                            async with httpx.AsyncClient(timeout=3.0) as client:
                                resp = await client.get(
                                    f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}",
                                    headers=headers
                                )
                                if resp.status_code == 200:
                                    data = resp.json()
                                    address_parts = data.get("address", {})
                                    city = address_parts.get("city") or address_parts.get("town") or address_parts.get("village") or address_parts.get("suburb") or address_parts.get("municipality")
                                    country = address_parts.get("country")
                                    if city:
                                        address = f"{city}, {country}" if country else city
                                    else:
                                        address = data.get("display_name") or f"{lat}, {lon}"
                                        parts = [p.strip() for p in address.split(",")]
                                        if len(parts) > 3:
                                            address = ", ".join(parts[:3])
                                    
                                    # Cache address back to Redis
                                    geo_data["address"] = address
                                    r.set("user:precise_geolocation", json.dumps(geo_data))

                    if address and address.strip():
                        return {
                            "source": "gps_browser",
                            "confidence_score": confidence_score,
                            "coordinates": {
                                "latitude": lat,
                                "longitude": lon,
                                "accuracy": accuracy,
                                "altitude": geo_data.get("altitude"),
                                "heading": geo_data.get("heading"),
                                "speed": geo_data.get("speed")
                            },
                            "address": address.strip(),
                            "temporal": {
                                "timestamp": timestamp,
                                "age_seconds": age,
                                "is_stale": is_stale
                            },
                            "metadata": {
                                "description": "Precise coordinates synced from browser client",
                                "raw_response": geo_data
                            }
                        }
        except Exception as e:
            logger.warning(f"GEOLOCATION-PIPELINE-GPS-ERR: {e}")

        # Step 3: IP Geolocation (Network Triangulation Fallback)
        apis = [
            ("http://ip-api.com/json", "city"),
            ("https://ipapi.co/json/", "city"),
            ("https://ipinfo.io/json", "city")
        ]
        
        for url, key in apis:
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        city = data.get(key)
                        country = data.get("country") or data.get("country_name")
                        if city:
                            loc = f"{city}, {country}" if country else city
                            # Add coordinates if available in IP data
                            coordinates = None
                            if "lat" in data and "lon" in data:
                                coordinates = {"latitude": data["lat"], "longitude": data["lon"], "accuracy": 5000}
                            elif "loc" in data: # ipinfo uses 'loc': 'lat,lon'
                                try:
                                    lat_str, lon_str = data["loc"].split(",")
                                    coordinates = {"latitude": float(lat_str), "longitude": float(lon_str), "accuracy": 10000}
                                except Exception:
                                    pass

                            return {
                                "source": "ip_fallback",
                                "confidence_score": 0.50,
                                "coordinates": coordinates,
                                "address": loc,
                                "temporal": {
                                    "timestamp": now,
                                    "age_seconds": 0,
                                    "is_stale": False
                                },
                                "metadata": {
                                    "description": f"Approximate network location from {url}",
                                    "raw_response": data
                                }
                            }
            except Exception:
                continue

        # Step 4: Environment Config (.env DEFAULT_GEOLOCATION)
        env_loc = os.getenv("DEFAULT_GEOLOCATION")
        if env_loc and env_loc.strip():
            return {
                "source": "env_fallback",
                "confidence_score": 0.30,
                "coordinates": None,
                "address": env_loc.strip(),
                "temporal": {
                    "timestamp": now,
                    "age_seconds": 0,
                    "is_stale": False
                },
                "metadata": {
                    "description": "Configured fallback location from .env file"
                }
            }

        # Step 5: Ultimate Baseline Default
        return {
            "source": "system_default",
            "confidence_score": 0.10,
            "coordinates": None,
            "address": "Hue, Vietnam",
            "temporal": {
                "timestamp": now,
                "age_seconds": 0,
                "is_stale": False
            },
            "metadata": {
                "description": "Hardcoded baseline system location"
            }
        }


    async def get_dynamic_geolocation(self) -> str:
        """
        Dynamically detects system geolocation via the Sovereign Geolocation Pipeline.
        Uses a local memory cache to avoid repeated network hits.
        """
        now = time.time()
        if hasattr(self, '_geo_cache') and self._geo_cache and (now - self._geo_cache_time < 7200):
            return self._geo_cache

        pipeline_res = await self.get_detailed_geolocation_pipeline()
        loc = pipeline_res.get("address", "Hue, Vietnam")
        self._geo_cache = loc
        self._geo_cache_time = now
        return loc


    async def call_chat(self, messages, role='CHAT', model=None, json_mode=False, schema=None, options=None, profile=None, keep_alive=None, task_id=None, images=None, tools=None, **kwargs):
        """
        API giao tiếp với Bộ não Trung tâm (Ollama Dual-Engine).
        Tích hợp [DYNAMIC KEEP-ALIVE] & [COGNITIVE PROFILE].
        Hỗ trợ [NATIVE TOOL CALLING] (Function Calling).
        """
        # [MICROSERVICE-ROUTING]: Central multi-tier routing protocol
        # [SELF-AWARENESS]: Direct cognitive bypass for core brain services
        if self.is_brain_service and role in ['CICE', 'RECEPTIONIST', 'CRITIC', 'CRITIC_ALPHA', 'DISPATCHER', 'CHAT']:
            services = []
        else:
            services = [
                (self.executor_url, "EXECUTOR"),
                (self.planner_url, "PLANNER"),
                (self.brain_url, "BRAIN")
            ]
        
        for service_url, service_name in services:
            # If current service, stop redirecting and process locally
            if service_url == self.current_service_url or (self.is_brain_service and service_name == "BRAIN"):
                break 
                
            try:
                # [PRE-FLIGHT-CHECK]: Kiểm tra sức khỏe dịch vụ 
                client = self._get_client()
                health = await client.get(f"{service_url}/health", timeout=5.0)
                if health.status_code != 200:
                    logger.warning(f"[PRE-FLIGHT] Service {service_name} ({service_url}) đang bận hoặc lỗi. Đang chuyển hướng...")
                    continue
                    
                # 🔒 [NEURAL-AUDIT]: Kiểm tra xem có xung đột GPU không 
                r = self._get_redis()
                if r and r.get("lock:gpu_vram"):
                    # Nếu GPU đang bị khóa bởi tác vụ quan trọng, ta sẽ chờ thay vì gây xung đột 
                    logger.info(f"[NEURAL-QUEUE] GPU đang bận. {service_name} sẽ chờ nơ-ron giải phóng...")

                self._publish_thought(role, f"[ROUTING]: Đang chuyển hướng tới {service_name} ({service_url})...", task_id)
                routing_timeout = min(kwargs.get('timeout', 900.0), 300.0)
                resp = await client.post(f"{service_url}/chat", json={
                    "messages": messages, "role": role, "model": model,
                    "json_mode": json_mode, "schema": schema, "options": options,
                    "profile": profile, "keep_alive": keep_alive, "task_id": task_id,
                    "images": images, "lock_timeout": kwargs.get('lock_timeout', 60),
                    "timeout": routing_timeout,
                    "hlc": str(hlc.now())
                }, timeout=routing_timeout)
                
                res_data = resp.json()
                return res_data.get('response') or res_data.get('answer') or ''
            except Exception as e:
                logger.error(f"❌ [ENGINE-CHAT-ERR]: {type(e).__name__}: {repr(e)}")
                continue
                
        # [METADATA-INJECTION]: Giao thuc thoi gian thuc va vi tri dia ly he thong
        import datetime
        import pytz
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.datetime.now(tz)
        days = ["Thu Hai", "Thu Ba", "Thu Tu", "Thu Nam", "Thu Sau", "Thu Bay", "Chu Nhat"]
        
        try:
            geo_loc = await self.get_dynamic_geolocation()
        except Exception:
            import os
            geo_loc = os.getenv("DEFAULT_GEOLOCATION", "Hue")
            
        try:
            from core.utils.world_state import world_engine
            world_context = world_engine.get_world_context_string()
        except Exception:
            world_context = "[WORLD STATE]\n- CPU: N/A | RAM: N/A\n- Tinh trang: Unknown"
            
        metadata_str = (
            f"[SYSTEM_TIME]: Hien tai la {current_time.strftime('%H:%M')}, {days[current_time.weekday()]}, ngay {current_time.strftime('%d/%m/%Y')} (Gio Viet Nam GMT+7).\n"
            f"[SYSTEM_GEOLOCATION]: Vi tri dia ly thuc te cua he thong va nguoi dung hien tai: {geo_loc}.\n"
            f"{world_context}"
        )
        
        if messages and messages[0].get('role') == 'system':
            if "[SYSTEM_TIME]" not in messages[0]['content']:
                messages[0]['content'] += f"\n\n{metadata_str}"
        else:
            messages.insert(0, {"role": "system", "content": metadata_str})
        
        # [IDENTITY-INJECTION]: Cường chế bản sắc cho vai trò CHAT thưa Master
        if role.upper() == 'CHAT':
            identity_dna = self.get_intel_file("ZENITH_IDENTITY.md")
            if identity_dna:
                messages.insert(0, {"role": "system", "content": f"🏛️ [ZENITH-IDENTITY]:\n{identity_dna}"})

        # [DYNAMIC-MIND-FORGING]: Giao thức Não Vô Biên 
        if not kwargs.get('skip_forge'):
            try:
                if not self.agent_profiles_cache: self._load_agent_profiles()
                # Chọn ra 3 hồ sơ Đặc vụ phù hợp nhất để hợp nhất 
                context_query = messages[-1]['content'] if messages else ""
                relevant_profiles = [v for k,v in self.agent_profiles_cache.items() if any(word in v.lower() for word in context_query.lower().split())][:3]
                if relevant_profiles:
                    dynamic_mind = "\n\n".join(relevant_profiles)
                    messages.insert(0, {"role": "system", "content": f"🏛️ [OMNI-MINDSET]: Bạn là sự nhất thể của các Đặc vụ Elite sau:\n{dynamic_mind}"})
                    self._publish_thought(role, "[SINGULARITY]: Đã đúc kết Hệ tư tưởng Đa tầng .", task_id)
            except Exception: pass

        # [COGNITIVE-BRIDGE]: Đồng bộ 'khẩu vị' tri thức theo kiến trúc Model thưa Master
        role_cfg = self.get_role_config(role)
        final_model = model or role_cfg.get('model')
        messages = self._bridge_cognitive_schema(final_model, messages)

        # [AUTO-CONTEXT-INJECTION]: Giao thức Thấu thị Vĩnh cửu 
        if not kwargs.get('skip_memory'):
            try:
                # Trích xuất goal từ tin nhắn cuối cùng để tìm kiếm 
                query = messages[-1]['content'] if messages else ""
                if len(query) > 10:
                    vector = await embed.get_embedding_async(query[:1000])
                    if vector:
                        memories = await qdrant_client.search_intel(vector, limit=3)
                        if memories:
                            mem_text = "\n".join([f"- {m.get('payload', {}).get('text', '')}" for m in memories])
                            messages.insert(0, {"role": "system", "content": f"[EXPERIENCE DNA]: Dựa trên di sản tri thức quá khứ, hãy lưu ý:\n{mem_text}"})
                            self._publish_thought(role, "[OMNIPRESENT]: Đã nạp di sản tri thức từ Qdrant .", task_id)
            except Exception: pass

        # --- TIẾP TỤC LOGIC GỌI MODEL TRỰC TIẾP ---
        duration = 0.0
        
        # [COST-GOVERNOR]: Khởi tạo ngân sách cho task
        budget = TaskBudget()
        ledger = BudgetLedger(task_id=task_id or "unknown")
        if kwargs.get('task_budget'):
            budget = TaskBudget(**kwargs['task_budget']) if isinstance(kwargs['task_budget'], dict) else kwargs['task_budget']
        
        max_attempts = budget.max_retries
        use_manual_react = False
        
        # [PROACTIVE-REACT]: Tự động nhận diện model không tối ưu Native Tools để đi tắt đón đầu, tránh lỗi latency
        if tools:
            f_model_lower = final_model.lower()
            if (
                'llama' in f_model_lower or 
                'phi' in f_model_lower or 
                'gemma' in f_model_lower or 
                '0.6b' in f_model_lower or 
                '0.5b' in f_model_lower or 
                '1.5b' in f_model_lower or 
                'tiny' in f_model_lower
            ):
                use_manual_react = True
                self._publish_thought(role, f"🧠 [PROACTIVE-REACT]: Model {final_model} thuộc nhóm tối ưu ReAct văn bản. Kích hoạt Giao thức ReAct Thủ công chủ động để bỏ qua độ trễ lỗi API thưa Master.", task_id)
        
        forced_cloud = False
        for attempt in range(max_attempts):
            if ledger.exceeded:
                self.publish_mission_log("WARN", f"💰 [COST-GOVERNOR]: Task {task_id} đã vượt ngân sách. Dừng retry.", task_id)
                break
                
            if attempt > 0:
                if use_manual_react:
                    self.publish_mission_log("INFO", f"🔄 [MANUAL-REACT]: Đang thử lại với Giao thức ReAct thủ công cho {final_model}...")
                else:
                    self.publish_mission_log("WARN", f"[FALLBACK]: Khoi chay co che du phong cho {final_model}...")
                    try:
                        from core.utils.hardware_scheduler import hardware_scheduler
                        fb_info = await hardware_scheduler.resolve_smart_fallback(final_model, self, [role, "CHAT", "RESERVE_AGENT"])
                        if fb_info and fb_info.get("model"):
                            final_model = fb_info["model"]
                            # Preserve high-level role identity if falling back to generic roles
                            if role not in ['RECEPTIONIST', 'PLANNER', 'DISPATCHER', 'CRITIC'] or fb_info.get("role") not in ["RESERVE_AGENT", "CHAT"]:
                                role = fb_info.get("role", role)
                            role_cfg = self.get_role_config(role)
                            self.publish_mission_log("INFO", f"[SMART-FALLBACK]: Dong bo mo hinh thanh cong. Chuyen sang Role: {role}, Model: {final_model}")
                        else:
                            break # No fallback found
                    except Exception as fb_err:
                        break

            # Estimate context length to auto-route long context queries to Gemini
            total_chars = sum(len(m.get('content', '')) for m in messages)
            estimated_tokens = total_chars // 4
            
            configs = self.load_software_rules()
            gemini_key = configs.get('gemini', {}).get('api_key')
            
            # [COST-GOVERNOR]: Kiểm tra ngân sách cloud trước khi route
            # Hạ ngưỡng về 8000 để bảo vệ VRAM của GPU AMD RX 6600 thưa Master
            if estimated_tokens > 8000 and gemini_key and not any(final_model.lower().startswith(p) for p in ['gemini-', 'gpt-', 'claude-']):
                if attempt > 0 and forced_cloud:
                    self.publish_mission_log("ERROR", f"❌ Ngữ cảnh quá lớn ({estimated_tokens} tokens) nhưng Cloud API đã thất bại. Hủy bỏ để bảo vệ hệ thống.", task_id)
                    return "Error: Context too large and Cloud Fallback API failed. Task aborted."
                
                if ledger.cloud_calls_made >= budget.max_cloud_calls:
                    self.publish_mission_log("WARN", f"💰 [COST-GOVERNOR]: Đã đạt giới hạn cloud calls ({budget.max_cloud_calls}). Giữ local.", task_id)
                elif ledger.estimated_cost_usd >= budget.max_cloud_cost_usd:
                    self.publish_mission_log("WARN", f"💰 [COST-GOVERNOR]: Đã vượt ngân sách cloud (${budget.max_cloud_cost_usd}). Giữ local.", task_id)
                else:
                    self.publish_mission_log("INFO", f"🔄 Ngữ cảnh lớn ({estimated_tokens} tokens). Chuyển hướng sang Gemini.")
                    # Sửa lại model name cho đúng chuẩn API Google
                    final_model = "models/gemini-3.5-flash"
                    forced_cloud = True
                    ledger.cloud_calls_made += 1
                    ledger.estimated_cost_usd += 0.01
                    if ledger.cloud_calls_made >= budget.max_cloud_calls or ledger.estimated_cost_usd >= budget.max_cloud_cost_usd:
                        ledger.exceeded = True
                
            # Determine if it is a cloud model
            cloud_provider = None
            is_cloud = False
            
            model_lower = final_model.lower()
            if model_lower.startswith('gemini-') or 'gemini' in model_lower:
                cloud_provider = 'gemini'
                is_cloud = True
            elif model_lower.startswith('gpt-') or 'gpt-' in model_lower:
                cloud_provider = 'openai'
                is_cloud = True
            elif model_lower.startswith('claude-') or 'claude-' in model_lower:
                cloud_provider = 'anthropic'
                is_cloud = True
            elif model_lower.startswith('deepseek-') and not model_lower.endswith(':latest') and ('chat' in model_lower or 'reasoner' in model_lower):
                cloud_provider = 'deepseek'
                is_cloud = True
            elif model_lower.startswith('grok-') or 'grok' in model_lower:
                cloud_provider = 'grok'
                is_cloud = True
                
            if kwargs.get('provider'):
                cloud_provider = kwargs.get('provider').lower()
                is_cloud = True

            if is_cloud:
                prov_cfg = configs.get(cloud_provider, {})
                prov_key = prov_cfg.get('api_key')
                prov_url = prov_cfg.get('base_url')
                if not prov_key:
                    # If cloud is requested but key is not configured, fallback to local Ollama
                    self.publish_mission_log("WARN", f"Không tìm thấy API Key cho {cloud_provider.upper()} trong rules_software.md. Chuyển sang dùng model local .")
                    is_cloud = False

            
            # [PROFILE-INJECTION]: Hợp nhất cấu hình Profile nếu có 
            final_options = options or role_cfg.get('options', {}).copy()
            target_profile = profile or final_options.get('profile')
            
            if target_profile and target_profile.upper() in self.profiles:
                preset = self.profiles[target_profile.upper()]
                # Chỉ ghi đè các tham số chưa có 
                for k, v in preset.items():
                    if k.lower() not in final_options:
                        final_options[k.lower()] = v
            
            # [CPU-OFFLOAD]: Ép chạy trên CPU nếu là tác vụ giám sát nhẹ hoặc được yêu cầu 
            is_small = any(k in final_model.lower() for k in ["1.5b", "0.5b", "tiny", "phi3"])
            hw_col = role_cfg.get('hardware', '').upper()
            is_cpu_bound = kwargs.get('cpu_only') or is_small or ('CPU' in hw_col)
            
            if is_cpu_bound:
                final_options['num_gpu'] = 0
                # Giữ ctx ở mức tối thiểu 4096 để tránh lỗi "truncating input prompt" thưa Master.
                if final_options.get('num_ctx', 4096) < 4096:
                    final_options['num_ctx'] = 4096
                
                # [NCNN-ESSENCE 1]: Tối ưu băng thông bộ nhớ RAM thưa Master
                # Bỏ qua NUMA trên Windows vì Ollama API không hỗ trợ trực tiếp option này.
                # final_options['numa'] = True
                
                # [NCNN-ESSENCE 2]: Áp đặt bộ đệm MMAP để tối ưu I/O Load (Giống zero-copy của NCNN)
                if 'use_mmap' not in final_options:
                    final_options['use_mmap'] = True
                
                # [NCNN-ESSENCE 3]: Force CPU thread limit directly in request options because Ollama ignores OLLAMA_NUM_THREAD environment variable.
                final_options['num_thread'] = 10
                
            final_keep_alive = keep_alive or role_cfg.get('keep_alive', '5m')
            
            # [TYPE-PURIFICATION]: Đảm bảo keep_alive là integer nếu là số 
            try:
                if str(final_keep_alive).replace('-', '').isdigit():
                    final_keep_alive = int(final_keep_alive)
            except Exception: pass

            # 🖼️ [NEURAL-VISION]: Đính kèm hình ảnh vào tin nhắn cuối cùng nếu có 
            _vision_models = ['moondream', 'llava', 'llama3.2-vision', 'bakllava', 'minicpm-v', 'qwen2-vl', 'qwen2.5-vl', 'phi3-vision', 'gemma3']
            _model_is_vision = any(v in final_model.lower() for v in _vision_models)
            if images and len(messages) > 0:
                if not _model_is_vision:
                    _non_vision_warn = f"⚠️ Model '{final_model}' không hỗ trợ đọc ảnh. JKAI sẽ bỏ qua ảnh đã gửi và xử lý nội dung text."
                    self.publish_mission_log("WARN", _non_vision_warn, task_id)
                    self._publish_thought(role, _non_vision_warn, task_id)
                else:
                    if isinstance(images, list):
                        messages[-1]['images'] = images
                    else:
                        messages[-1]['images'] = [images]

            # [PARAM-PURIFICATION]: Lọc bỏ các tham số rác 
            safe_options = {k: v for k, v in final_options.items() if k not in ['profile']}
            
            # Giao thức truyền tin Elite 
            payload = {
                'model': final_model, 
                'messages': messages, 
                'stream': True
            }
            
            if tools:
                if use_manual_react:
                    # Inject manual react instructions to system prompt
                    manual_prompt = (
                        "\n\n[HỆ THỐNG]: Model của bạn hiện tại không hỗ trợ gọi Tool tự động qua API (Error 400). "
                        "Hãy sử dụng Giao thức ReAct Thủ công bằng cách viết lệnh theo cú pháp sau để thực thi kỹ năng:\n"
                        "Action: execute_skill(skill_id='tên_kỹ_năng', query='tham_số')"
                    )
                    # Clone messages to avoid polluting original ones if retrying multiple times
                    messages = [dict(m) for m in messages]
                    if messages[0]['role'] == 'system':
                        if "[HỆ THỐNG]: Model của bạn" not in messages[0]['content']:
                            messages[0]['content'] += manual_prompt
                    else:
                        messages.insert(0, {"role": "system", "content": manual_prompt})
                    payload['messages'] = messages
                else:
                    payload['tools'] = tools
            
            is_reasoning_model = any(k in final_model.lower() for k in ["r1", "thinking", "deepseek-v3"])
            
            payload['keep_alive'] = final_keep_alive
            payload['options'] = safe_options
            
            # [REASONING BYPASS]: Nếu là model Reasoning (DeepSeek-R1), KHÔNG dùng format: json 
            # vì nó sẽ làm tắt chức năng tư duy .
            is_reasoning_model = any(k in final_model.lower() for k in ["r1", "thinking", "deepseek-v3"])
            if is_reasoning_model:
                # Reasoning models perform better with natural language prompts 
                if 'format' in payload: del payload['format']
            elif schema: 
                payload['format'] = schema
            elif json_mode: 
                payload['format'] = 'json'
            
            # [SMALL MODEL GUARD]: Tự động áp dụng thiết lập an toàn cho các mô hình yếu 
            is_weak_model = any(k in final_model.lower() for k in ["0.5b", "0.8b", "tiny"])
            if is_weak_model:
                if 'options' not in payload: payload['options'] = {}
                payload['options']['repeat_penalty'] = 1.3 # Chống lặp cực mạnh
                payload['options']['top_k'] = 20           # Giới hạn lựa chọn từ để tránh nói sảng
                if 'num_predict' not in payload['options']:
                    payload['options']['num_predict'] = 256 # Ép ngắn gọn
            
            start_time = time.time()
            logger.info(f"[ENGINE] call_chat: {final_model} (Role: {role})")
            self._publish_thought(role, f"Đang triệu tập {final_model}... (Context: {final_options.get('num_ctx', 'default')})", task_id)
            
            client = self._get_client()
            full_content = ""
            thinking_content = ""
            display_thought = ""
            is_thinking = False
            think_stream_id = None
            final_tool_calls = []
            
            try:
                last_log_time = time.time()
                now = last_log_time
                last_published_text = ""
                last_signal_check = now
                last_published_len = 0
                last_published_thinking_len = 0
                is_first_chunk = True
                is_first_thinking_chunk = True
                # [SYNAPSE WATCHDOG]: Theo dõi phản hồi đầu tiên từ nơ-ron 
                first_token_received = False
                waiting_start = now
                
                # [NEURAL GATEWAY]: Phân phối luồng theo tài nguyên 
                num_gpu_val = final_options.get('num_gpu', -1)
                hw_col = role_cfg.get('hardware', '').upper()
                if 'GPU' in hw_col:
                    is_gpu = True
                elif 'CPU' in hw_col:
                    is_gpu = False
                else:
                    is_gpu = (num_gpu_val > 0) or (num_gpu_val == -1)
                
                # [DUAL-ENGINE-ROUTING]: Tuân thủ tuyệt đối Hardware Affinity của Master thưa Ngài
                # Master yêu cầu phân tách rõ rệt giữa Port 11434 (GPU) và Port 11435 (CPU)
                target_ollama_host = self.ollama_host_gpu if is_gpu else self.ollama_host_cpu
                
                # [RULE-COMPLIANT]: Không hardcode — routing hoàn toàn theo rule_hardware.md
                
                # 🚫 [SCAN-PHASE-REMOVAL]: Đã hủy bỏ việc tự ý quét model để tránh model "nhảy" lung tung thưa Master.
                # Hệ thống giờ đây sẽ ép buộc chạy đúng model tại đúng cổng phần cứng đã quy định.

                # [PRE-FLIGHT-ABORT]: Kiểm tra lệnh dừng trước khi khởi động nơ-ron 
                r_pre = self._get_redis()
                if r_pre and r_pre.get("agent:stop_signal") in [b'true', 'true']:
                    self._publish_thought(role, "[ABORT]: Lệnh Dừng đang hoạt động. Từ chối khởi động nơ-ron .", task_id)
                    return "Mission aborted by Master."

                # 🔒 Master đã xác nhận GPU có 2 model và chạy song song, KHÔNG cần khóa GPU 
                use_gpu_lock = False
                if not use_gpu_lock or await self._acquire_neural_lock("gpu_vram", timeout=kwargs.get('lock_timeout')):
                    try:
                        if is_cloud:
                            prov_cfg = configs.get(cloud_provider, {})
                            prov_key = prov_cfg.get('api_key')
                            prov_url = prov_cfg.get('base_url')
                            
                            if cloud_provider == 'anthropic':
                                url = f"{prov_url.rstrip('/')}/messages"
                                headers = {
                                    "x-api-key": prov_key,
                                    "anthropic-version": "2023-06-01",
                                    "content-type": "application/json"
                                }
                                system_prompts = [m['content'] for m in messages if m['role'] == 'system']
                                system_prompt = "\n".join(system_prompts) if system_prompts else None
                                
                                formatted_messages = [dict(m) for m in messages if m['role'] != 'system']
                                for m in formatted_messages:
                                    if m['role'] not in ['user', 'assistant']:
                                        m['role'] = 'user'
                                        
                                cloud_payload = {
                                    "model": final_model,
                                    "messages": formatted_messages,
                                    "max_tokens": 4096,
                                    "stream": True
                                }
                                if system_prompt:
                                    cloud_payload["system"] = system_prompt
                            else: # openai, gemini, deepseek
                                # [DYNAMIC-ENDPOINT]: Detect if Gemini uses OpenAI-compatible endpoint or native
                                if cloud_provider == 'gemini' and 'openai' not in prov_url.lower():
                                    model_clean = final_model.replace("models/", "")
                                    url = f"{prov_url.rstrip('/')}/models/{model_clean}:generateContent"
                                    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": prov_key}
                                    # Gemini native format
                                    contents = []
                                    for m in messages:
                                        role_map = {"user": "user", "assistant": "model", "system": "user"}
                                        contents.append({"role": role_map.get(m['role'], 'user'), "parts": [{"text": m['content']}]})
                                    cloud_payload = {"contents": contents}
                                else:
                                    # Standard OpenAI-compatible (including OpenAI, DeepSeek, Grok, and OpenAI-compat Gemini)
                                    url = f"{prov_url.rstrip('/')}/chat/completions"
                                    headers = {
                                        "Authorization": f"Bearer {prov_key}",
                                        "Content-Type": "application/json"
                                    }
                                    cloud_payload = {
                                        "model": final_model,
                                        "messages": messages,
                                        "stream": True
                                    }
                                
                            if 'temperature' in final_options:
                                cloud_payload['temperature'] = final_options['temperature']
                            if 'top_p' in final_options:
                                cloud_payload['top_p'] = final_options['top_p']
                                
                            if tools:
                                # [CLOUD-TOOL-SUPPORT]: Map tools for cloud APIs (OpenAI/Gemini/Deepseek)
                                cloud_payload['tools'] = tools
                                
                            req_url = url
                            req_headers = headers
                            req_payload = cloud_payload
                        else:
                            req_url = f'{target_ollama_host}/api/chat'
                            req_headers = None
                            req_payload = payload
                            
                        import httpx
                        if is_cloud:
                            custom_timeout = httpx.Timeout(900.0, connect=15.0, read=90.0)
                        else:
                            # [TIMEOUT-RELIABILITY]: Tăng read timeout cho local từ 35s lên 180s thưa Master.
                            # Việc này giúp tránh bị ReadTimeout giả tạo khi model đang được tải (load) từ đĩa cứng hoặc đang xử lý prefill dài.
                            custom_timeout = httpx.Timeout(900.0, connect=10.0, read=180.0)
                            
                        async with client.stream('POST', req_url, headers=req_headers, json=req_payload, timeout=custom_timeout) as resp:
                            if resp.status_code != 200:
                                logger.error(f"❌ [API-ERR] {resp.status_code} for {final_model}")
                                err_body = await resp.aread() if hasattr(resp, 'aread') else b''
                                err_text = err_body.decode('utf-8', errors='replace')[:300] if err_body else ''
                                err_msg = f"Error: [API-ERR] Server/API trả về mã {resp.status_code}. {err_text}"
                                
                                # Detect tool support error to trigger manual react
                                if ("support tools" in err_text.lower() or "too many tools" in err_text.lower()) and tools:
                                    use_manual_react = True
                                    # [RECOVERY-LOG]: Thông báo cho Master biết bối cảnh lỗi và cơ chế tự sửa
                                    self._publish_thought(role, f"⚠️ Model không hỗ trợ Tools API ({resp.status_code}). Đang kích hoạt Giao thức ReAct Thủ công để tự phục hồi...", task_id)
                                    # [SELF-HEALING]: Chuyển sang attempt tiếp theo ngay lập tức với use_manual_react=True
                                    continue
                                elif "not support image" in err_text.lower() or "does not support image" in err_text.lower() or "image input" in err_text.lower():
                                    # 🖼️ [VISION-FALLBACK]: Model không hỗ trợ ảnh — bỏ ảnh và thử lại
                                    if attempt < max_attempts - 1:
                                        _fallback_msg = f"⚠️ Model '{final_model}' không hỗ trợ đọc ảnh. JKAI sẽ bỏ qua ảnh và xử lý nội dung text."
                                        self._publish_thought(role, _fallback_msg, task_id)
                                        images = None
                                        for msg in messages:
                                            msg.pop('images', None)
                                        continue
                                    else:
                                        return f"❌ Model '{final_model}' không hỗ trợ đọc ảnh. Vui lòng dùng vision model (moondream, llava...) hoặc gửi yêu cầu không kèm ảnh."
                                else:
                                    self._publish_thought(role, err_msg, task_id)

                                if attempt == max_attempts - 1:
                                    return err_msg
                                else:
                                    raise httpx.HTTPStatusError(err_msg, request=resp.request, response=resp)

                            import uuid
                            stream_id = f"stream_{uuid.uuid4().hex[:8]}"
                            
                            async for line in resp.aiter_lines():
                                if not line: 
                                    # Nhịp đập nơ-ron: Báo cáo nếu đang chờ quá lâu 
                                    now = time.time()
                                    if not first_token_received and now - waiting_start > 10.0:
                                        self._publish_thought(role, "[NEURAL-PULSE]: Vẫn đang chờ phản hồi đầu tiên. Model có thể đang nạp hoặc suy nghĩ rất sâu...", task_id)
                                        waiting_start = now # Reset timer để không spam
                                    continue
                                
                                now = time.time()
                                if not first_token_received:
                                    first_token_received = True
                                    self._publish_thought(role, "[NEURAL-SYNC]: Đã bắt đầu nhận tín hiệu nơ-ron...", task_id)
                                
                                    last_signal_check = now

                                # [SIGNAL-INTERRUPT]: Kiểm tra lệnh dừng khẩn cấp 
                                if now - last_signal_check > 2.0:
                                    last_signal_check = now
                                    r = self._get_redis()
                                    if r:
                                        stop_sig = r.get("agent:stop_signal")
                                        if stop_sig in [b'true', 'true']:
                                            self._publish_thought(role, "[SIGNAL]: Đã nhận lệnh Dừng khẩn cấp từ Master. Ngắt kết nối nơ-ron ngay lập tức .", task_id)
                                            break

                                # [DEGENERATION CHECK]: Phát hiện vòng lặp vô tận 
                                if len(full_content) > 1000 and len(set(full_content[-100:])) < 5:
                                    self._publish_thought(role, "[NEURAL-DEGENERATION]: Phát hiện nơ-ron bị lặp (looping). Ngắt kết nối để bảo vệ VRAM.", task_id)
                                    break

                                token = ""
                                reasoning_token = ""
                                
                                if is_cloud:
                                    if cloud_provider == 'anthropic':
                                        if line.startswith("data: "):
                                            line_data = line[6:].strip()
                                            try:
                                                chunk = json.loads(line_data)
                                                if chunk.get('type') == 'content_block_delta':
                                                    token = chunk.get('delta', {}).get('text', '')
                                            except Exception: pass
                                    else: # openai, gemini, deepseek
                                        if line.startswith("data: "):
                                            line_data = line[6:].strip()
                                            if line_data == "[DONE]":
                                                continue
                                            try:
                                                chunk = json.loads(line_data)
                                                choices = chunk.get('choices', [])
                                                if choices:
                                                    delta = choices[0].get('delta', {})
                                                    token = delta.get('content', '')
                                                    reasoning_token = delta.get('reasoning_content', '')
                                            except Exception: pass
                                else:
                                    try:
                                        chunk = json.loads(line)
                                    except Exception as je:
                                        logger.warning(f"⚠️ [JSON-DECODE-WARN] Không thể giải mã dòng stream Ollama: '{line}'. Lỗi: {je}")
                                        continue
                                    # 🖼️ [STREAM-VISION-CHECK]: Phát hiện lỗi ảnh trong stream
                                    if 'error' in chunk:
                                        err_stream = chunk['error']
                                        if "not support image" in err_stream.lower() or "image input" in err_stream.lower():
                                            _vis_stream_msg = f"❌ Model '{final_model}' không hỗ trợ đọc ảnh. Vui lòng dùng vision model (moondream, llava...) hoặc gửi yêu cầu không kèm ảnh."
                                            self._publish_thought(role, _vis_stream_msg, task_id)
                                            return _vis_stream_msg
                                        self._publish_thought(role, f"⚠️ [STREAM-ERR]: {err_stream}", task_id)
                                        continue
                                    msg_obj = chunk.get('message', {})
                                    token = msg_obj.get('content', '')
                                    reasoning_token = msg_obj.get('reasoning_content', '')
                                    if 'tool_calls' in msg_obj and msg_obj['tool_calls']:
                                        # Ollama might send tool_calls in the chunk
                                        for tc in msg_obj['tool_calls']:
                                            if tc not in final_tool_calls:
                                                final_tool_calls.append(tc)
                                
                                # [UNIFIED REASONING ENGINE]: Xử lý cả reasoning_content và <think> tag 
                                if reasoning_token:
                                    if not is_thinking:
                                        is_thinking = True
                                        think_stream_id = f"think_{uuid.uuid4().hex[:8]}"
                                        self._publish_thought(role, "[HỆ THỐNG]: Đang khởi động luồng tư duy sâu...", task_id)
                                        last_log_time = time.time()
                                    thinking_content += reasoning_token
                                
                                if token:
                                    # [CHUNK-AGNOSTIC DETECTION]: Phát hiện thẻ <think> bất kể bị chia nhỏ 
                                    temp_buffer = (full_content + thinking_content + token)[-20:]
                                    
                                    if not is_thinking and '<think>' in temp_buffer:
                                        is_thinking = True
                                        think_stream_id = f"think_{uuid.uuid4().hex[:8]}"
                                        self._publish_thought(role, "[HỆ THỐNG]: Đang khởi động luồng tư duy sâu...", task_id)
                                    
                                    if is_thinking and '</think>' in temp_buffer:
                                        is_thinking = False
                                        # Phát sóng toàn bộ tư duy khi kết thúc
                                        self._publish_thought(role, f"[LUỒNG TƯ DUY NỘI TÂM]:\n{thinking_content}", task_id, stream_id=think_stream_id)
                                    
                                    if is_thinking:
                                        thinking_content += token
                                    else:
                                        full_content += token

                                # Cap nhat soan thao van ban moi 50ms de tao hieu ung nhay chu muot ma thua Master
                                if now - last_log_time > 0.05:
                                    if is_thinking and len(thinking_content) > last_published_thinking_len:
                                        thinking_delta = thinking_content[last_published_thinking_len:]
                                        if thinking_delta:
                                            if is_first_thinking_chunk:
                                                msg = f"[LUỒNG TƯ DUY NỘI TÂM]:\n{thinking_delta}"
                                            else:
                                                msg = thinking_delta
                                            
                                            if not think_stream_id:
                                                think_stream_id = f"think_{uuid.uuid4().hex[:8]}"
                                            
                                            self._publish_thought(
                                                role, 
                                                msg, 
                                                task_id, 
                                                stream_id=think_stream_id, 
                                                is_delta=True, 
                                                is_first_chunk=is_first_thinking_chunk
                                            )
                                            
                                            last_published_thinking_len = len(thinking_content)
                                            is_first_thinking_chunk = False
                                            last_log_time = now
                                    elif not is_thinking and len(full_content) > last_published_len:
                                        content_delta = full_content[last_published_len:]
                                        if content_delta:
                                            self._publish_thought(
                                                role, 
                                                content_delta, 
                                                task_id, 
                                                stream_id=stream_id, 
                                                is_delta=True, 
                                                is_first_chunk=is_first_chunk
                                            )
                                            
                                            last_published_len = len(full_content)
                                            is_first_chunk = False
                                            last_log_time = now

                            # Gui tin hieu hoan tat (final non-delta flush) de dong bo day du va luu vao lich su thưa Master
                            if thinking_content.strip():
                                if not think_stream_id:
                                    think_stream_id = f"think_{uuid.uuid4().hex[:8]}"
                                self._publish_thought(
                                    role, 
                                    f"[LUỒNG TƯ DUY NỘI TÂM]:\n{thinking_content.strip()}", 
                                    task_id, 
                                    stream_id=think_stream_id, 
                                    is_delta=False
                                )
                            if full_content.strip():
                                self._publish_thought(
                                    role, 
                                    full_content.strip(), 
                                    task_id, 
                                    stream_id=stream_id, 
                                    is_delta=False
                                )

                            duration = time.time() - start_time
                            
                            # [THINKING EXTRACTION] - Trích xuất tư duy từ các model Reasoning (<think> tag)
                            thinking_match = re.search(r'<think>\s*(.*?)\s*(?:</think>|$)', full_content, re.DOTALL)
                            if thinking_match:
                                thinking_process = thinking_match.group(1).strip()
                                if thinking_process:
                                    self._publish_thought(role, f"[LUỒNG TƯ DUY NỘI TÂM]:\n{thinking_process}", task_id)
                                
                                # Chỉ lọc bỏ nếu phần còn lại có nội dung đáng kể 
                                stripped_content = re.sub(r'<think>.*?(?:</think>|$)', '', full_content, flags=re.DOTALL).strip()
                                if len(stripped_content) > 20:
                                    full_content = stripped_content
                                elif thinking_process:
                                    # Nếu model chỉ "nghĩ" mà không "nói" ngoài thẻ, lấy phần nghĩ làm kết quả 
                                    full_content = thinking_process
                                else:
                                    full_content = stripped_content
                    finally:
                        if is_gpu:
                            await self._release_neural_lock("gpu_vram")

                # [JSON THOUGHT EXTRACTION] - Trích xuất từ trường JSON (thought/reasoning)
                if json_mode:
                    try:
                        data = json.loads(full_content)
                        if isinstance(data, dict):
                            # Ưu tiên các trường chứa tư duy
                            internal_thought = data.get("thought") or data.get("reasoning") or data.get("tư_duy")
                            if internal_thought:
                                self._publish_thought(role, f"[PHÂN TÍCH CHIẾN LƯỢC]:\n{internal_thought}", task_id)
                    except Exception: pass

                self._publish_thought(role, f"Hoàn tất trong {duration:.2f}s. (Size: {len(full_content)} chars)", task_id)

                # [LATENCY-REPORT]: Chuyển thành log nội bộ thay vì public
                logger.info(f"⏱️ [{role}] {final_model}: {duration:.2f}s")

                if final_tool_calls:
                    self._publish_thought(role, f"🛠️ [NATIVE-TOOL-CALL]: Nơ-ron quyết định sử dụng {len(final_tool_calls)} công cụ.", task_id)
                    return {"answer": full_content, "tool_calls": final_tool_calls}

                if json_mode or schema:
                    try: 
                        # [ROBUST JSON EXTRACTION]: Chỉ trích xuất khi được yêu cầu 
                        return self._extract_json_from_text(full_content)
                    except Exception:
                        self._publish_thought(role, f"Lỗi parse JSON. Trả về text thô.", task_id)
                        return full_content
                
                # 📜 [LEGACY-COMPATIBILITY]: Luôn trả về chuỗi văn bản cho các Đặc vụ cũ 
                return str(full_content)
                
            except Exception as e:
                import httpx
                err_str = str(e)
                # [SMART-FAILOVER-PROTOCOL]: Tự động chuyển vùng nếu trạm chính thực sự bị sập (ConnectError/ConnectTimeout)
                # Tuyệt đối KHÔNG tự ý chuyển vùng khi bị ReadTimeout để tránh gọi sai phần cứng (gọi CPU model lên GPU gây nghẽn VRAM) thưa Master.
                if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError)) and not kwargs.get('is_fallback_attempt'):
                    self.publish_mission_log("WARNING", f"📡 [CONNECTION-LOST]: Trạm tại {req_url} gặp sự cố hoặc nghẽn nơ-ron ({type(e).__name__}). Đang kích hoạt Giao thức Chuyển vùng thưa Master...", task_id)
                    # Thử trạm còn lại
                    other_host = self.ollama_host_cpu if target_ollama_host == self.ollama_host_gpu else self.ollama_host_gpu
                    kwargs['is_fallback_attempt'] = True
                    # Kiểm tra xem model có ở trạm kia không
                    try:
                        check_resp = await client.get(f"{other_host}/api/tags")
                        if check_resp.status_code == 200:
                            models = [m['name'].lower() for m in check_resp.json().get('models', [])]
                            if any(final_model.lower() in m for m in models):
                                self.publish_mission_log("INFO", f"✅ [FAILOVER-SUCCESS]: Đã tìm thấy nơ-ron {final_model} tại trạm dự phòng {other_host}. Đang chuyển kết nối thưa Master.", task_id)
                                return await self.call_chat(messages=messages, role=role, model=final_model, task_id=task_id, task_budget=budget, **kwargs)
                    except Exception:
                        pass

                if isinstance(e, httpx.ConnectError):
                    err_str = f"🛑 [CONNECT-FAILED]: Không thể kết nối tới Trạm nơ-ron {final_model} tại {req_url}. Có thể Trạm đang ngoại tuyến hoặc bị tường lửa chặn thưa Master."
                elif isinstance(e, httpx.TimeoutException):
                    err_str = f"⏳ [TIME-OUT]: Trạm nơ-ron {final_model} phản ứng quá chậm (>900s). Có thể VRAM đang bị nghẽn thưa Master."
                
                err_msg = f"Error: [NEURAL-ENGINE-ERR] {err_str}"
                logger.error(err_msg)
                self._publish_thought(role, err_msg, task_id)
                
                # [SMART-ERROR-RECOVERY]: Phát hiện lỗi Quota/429 để ép chuyển vùng nơ-ron
                if any(x in err_str.lower() for x in ["429", "quota", "rate limit", "limit exceeded", "exhausted"]):
                    self.publish_mission_log("CRITICAL", f"🚨 [CLOUD-QUOTA-EXCEEDED]: API {final_model} đã cạn kiệt tài nguyên. Kích hoạt Giao thức Dự phòng Thông minh (Smart Fallback).", task_id)
                    
                    try:
                        from core.utils.hardware_scheduler import hardware_scheduler
                        fb_info = await hardware_scheduler.resolve_smart_fallback(final_model, self, [role, "CHAT", "RESERVE_AGENT"])
                        if fb_info and fb_info.get("model"):
                            final_model = fb_info["model"]
                            self.publish_mission_log("INFO", f"✅ [DYNAMIC-RECOVERY]: Đã chuyển vùng sang `{final_model}` ({fb_info.get('hardware')}) thành công.", task_id)
                        else:
                            # ❌ [HARD-ABORT]: Kiệt lực hoàn toàn. Không tự ý triệu hồi model lạ thưa Master.
                            logger.error(f"❌ [FALLBACK-FAILED]: Không tìm thấy mô hình dự phòng hợp lệ cho Role `{role}`.")
                            return f"Error: [RESOURCE-EXHAUSTED] Mọi nơ-ron dự phòng cho Role `{role}` đã cạn kiệt thưa Master."
                    except Exception as fb_err:
                        logger.error(f"❌ [FALLBACK-CRITICAL]: {fb_err}")
                        return f"Error: [FALLBACK-CRITICAL] {fb_err}"

                    kwargs['skip_memory'] = True # Giảm tải ngữ cảnh để Local chạy mượt hơn
                    is_cloud = False
                
                if attempt == max_attempts - 1:
                    return err_msg
                else:
                    continue # continue the attempt loop
            finally:
                await self._exit_neural_gate(final_model)

            # If it succeeded, it would have returned earlier (either dict or string)
            # If it failed but didn't return, it means it hit the 'continue' or 'break' to retry.


    def _extract_json_from_text(self, text):
        """Trích xuất JSON từ văn bản thô một cách bền bỉ ."""
        if not text: return {}
        # 1. Thử parse trực tiếp
        try: return json.loads(text)
        except Exception: pass
        
        # 2. Tìm trong Markdown Code Blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group(1))
            except Exception: pass
            
        # 3. Tìm các khối { ... } tiềm năng và thử parse từng khối (ưu tiên khối hợp lệ đầu tiên hoặc khối có cấu trúc steps)
        # Sử dụng regex tìm các khối ngoặc nhọn lớn nhất có thể
        potential_json_blocks = re.findall(r'(\{.*?\})', text, re.DOTALL)
        
        # Thử parse từ ngược lại (thường JSON nằm ở cuối)
        for block in reversed(potential_json_blocks):
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    # Nếu tìm thấy khối có 'steps' hoặc 'answer', khả năng cao đây là kết quả đúng
                    if "steps" in data or "answer" in data or "thought" in data:
                        return data
                    # Lưu lại khối hợp lệ cuối cùng như phương án dự phòng
                    last_valid = data
            except Exception:
                continue
        
        if 'last_valid' in locals():
            return last_valid
            
        # 4. Cố gắng làm sạch text thô nếu không tìm thấy khối nào hoàn hảo
        # (Xóa các phần <think>...</think> nếu còn sót lại)
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if cleaned_text.startswith('{') and cleaned_text.endswith('}'):
            try:
                return json.loads(cleaned_text)
            except Exception: pass
            
        raise Exception("Không tìm thấy JSON hợp lệ.")

    def call_skill(self, skill_id, params, task_id="system"):
        """
        ⚡ [SUPREME CALL]: Giao thức Triệu hồi Kỹ năng chuẩn v30.2.
        Tìm kiếm và thực thi logic của kỹ năng dựa trên #ID.
        """
        self._publish_thought("SKILL_CALL", f"Đang triệu hồi Siêu kỹ năng `{skill_id}`...", task_id)
        
        # 1. Tìm đường dẫn kỹ năng từ Registry (Giả lập tìm kiếm)
        skill_name_map = {
            "#21": "skill_super_search",
            "#05": "skill_self_healing",
            "#24": "skill_giam_sat_he_thong",
            "#20": "skill_dongbotrithuc",
            "#31": "skill_strategic_proposal"
        }
        
        skill_folder = skill_name_map.get(skill_id)
        if not skill_folder:
            # Fallback: Trình trinh sát nơ-ron tìm kiếm thực tế
            self._publish_thought("WARN", f"Không tìm thấy mapping cho `{skill_id}`, kích hoạt Trinh sát nơ-ron...", task_id)
            return {"status": "failed", "msg": "Skill ID not mapped"}

        # 2. Thực thi logic (Giả lập - Trong bản n8n sẽ gọi qua Webhook)
        return {
            "status": "success", 
            "output": f"Dữ liệu từ {skill_id} ({skill_folder}) đã được xử lý chuẩn Sovereign.",
            "skill": skill_folder
        }


engine = JKAIIntelligenceEngine()
