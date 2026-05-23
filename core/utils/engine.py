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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UIE')

class JKAIIntelligenceEngine:
    def __init__(self):
        self.rules_path = '/intelligence/rule_hardware.md'
        if not os.path.exists(self.rules_path):
            self.rules_path = 'D:/Docker/N8N/intelligence/rule_hardware.md'
            
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
        
        if not self.ollama_host.startswith('http'):
            self.ollama_host = f"http://{self.ollama_host}"
        
        # [WINDOWS-RELIABILITY]: Chuyển hướng 0.0.0.0 về 127.0.0.1 
        if "0.0.0.0" in self.ollama_host:
            self.ollama_host = self.ollama_host.replace("0.0.0.0", "127.0.0.1")
            
        # Đảm bảo port nếu thiếu 
        if ":" not in self.ollama_host[7:]: # Bỏ qua http://
            self.ollama_host = f"{self.ollama_host}:11434"
        self._rules_last_mtime = 0
        self._redis_conn = None
        self._client = None 
        self._role_mapping_cache = {} # Ensure this is initialized
        self.global_params = {}
        # 🔒 [ELITE REDIS LOCKS]: Khóa toàn cục hệ thống 
        self.lock_timeout = 180 # 3 phút tối đa chờ nơ-ron
        
        # [QUANTUM-LEAP v31.0]: Thực thi Processor Affinity 
        self._apply_hardware_affinity()
        self.agent_profiles_cache = {}

    def _load_agent_profiles(self):
        """📂 [SINGULARITY-LOAD]: Nạp toàn bộ tinh hoa Đặc vụ vào RAM ."""
        agents_dir = "D:/Docker/N8N/intelligence/agents"
        try:
            if os.path.exists(agents_dir):
                import os
                for file in os.listdir(agents_dir):
                    if file.endswith(".md"):
                        with open(os.path.join(agents_dir, file), "r", encoding="utf-8") as f:
                            self.agent_profiles_cache[file] = f.read()[:1000]
        except: pass

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
                    decode_responses=True
                )
            except: pass
        return self._redis_conn

    def _publish_thought(self, role, thought, task_id="system", stream_id=None):
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
                    
                msg = f"{level} [{iso_time}] [{role}] [Task: {task_id}] {thought.strip()}"
                display_tag = role.upper()
                payload = {
                    "tag": display_tag, "msg": msg, "ts": time.time(), "task_id": task_id or "system", "source": display_tag, "iso_time": iso_time
                }
                if stream_id:
                    payload["id"] = stream_id
                    payload["pin_id"] = stream_id
                log_payload = json.dumps(payload, ensure_ascii=False)
                # [BROADCAST]: Phát tín hiệu
                r.publish("monitor:log_channel", log_payload)
                r.lpush("monitor:log_history", log_payload)
                r.ltrim("monitor:log_history", 0, 499)
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
                r.lpush("monitor:log_history", payload)
                r.ltrim("monitor:log_history", 0, 999)
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
            except: pass

    def get_intel_file(self, filename):
        """Truy xuất tệp tin từ Thánh địa Tri thức."""
        base_paths = [
            '/intelligence', '/intelligence/context', '/intelligence/agents',
            '/intelligence/rules', '/intelligence/skills',
            'D:/Docker/N8N/intelligence', 'D:/Docker/N8N/intelligence/context'
        ]
        clean_name = filename[2:] if filename.startswith('./') else filename
        for bp in base_paths:
            full_path = os.path.join(bp, clean_name)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except: pass
        return None

    def _get_smart_params(self):
        try:
            mtime = os.path.getmtime(self.rules_path)
            if mtime > self._rules_last_mtime:
                self._parse_rules()
                self._rules_last_mtime = mtime
        except: pass

    def _parse_rules(self):
        try:
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_r_cache = {}
            self.global_params = {}
            self.profiles = {}
            lines = content.split('\n')
            in_section_3 = False
            in_section_25 = False
            headers = []
            
            for line in lines:
                line = line.strip()
                # [GLOBAL PARAMS]: Trích xuất thông số tổng thể từ Section 1 
                if line.startswith('- **') and ':' in line:
                    # Hỗ trợ cả **KEY**: và **KEY:** 
                    clean_line = line[4:].replace('**:', ':').replace('**', '')
                    if ':' in clean_line:
                        p_key, p_val = clean_line.split(':', 1)
                        self.global_params[p_key.strip().upper()] = p_val.split('(')[0].strip()

                if '2.5. Neural Hardware Profiles' in line:
                    in_section_25 = True
                    in_section_3 = False
                    headers = []
                    continue
                if '3. Active Role Mapping' in line:
                    in_section_3 = True
                    in_section_25 = False
                    headers = []
                    continue
                if (in_section_3 or in_section_25) and line.startswith('## '):
                    in_section_3 = False
                    in_section_25 = False
                    continue
                if not (in_section_3 or in_section_25) or not line.startswith('|') or ':---' in line:
                    continue
                
                parts = [p.strip() for p in line.split('|')]
                if 'ROLE' in line.upper() or 'PROFILE NAME' in line.upper():
                    headers = [p.upper() for p in parts]
                    continue
                
                if len(parts) >= 3 and headers:
                    role_key = re.sub(r'[^a-zA-Z0-9_-]', '', parts[1].replace('**', '')).strip().upper()
                    model_name = re.sub(r'[^a-zA-Z0-9:._/-]', '', parts[2].replace('**', '')).strip().lower()
                    if not role_key or not model_name: continue
                    
                    def get_safe_int(h_name, default=0):
                        try:
                            idx = next((i for i, h in enumerate(headers) if h_name in h), -1)
                            if idx != -1 and idx < len(parts):
                                val = parts[idx].replace('**', '').strip().lower()
                                if val == 'n/a' or not val: return default
                                nums = re.findall(r'\d+', val)
                                return int(nums[0]) if nums else default
                            return default
                        except: return default

                    def get_safe_float(h_name, default=0.7):
                        try:
                            idx = next((i for i, h in enumerate(headers) if h_name in h), -1)
                            if idx != -1 and idx < len(parts):
                                val = parts[idx].replace('**', '').strip().lower()
                                if val == 'n/a' or not val: return default
                                nums = re.findall(r'\d+\.?\d*', val)
                                return float(nums[0]) if nums else default
                            return default
                        except: return default

                    def get_safe_str(h_name, default=''):
                        try:
                            idx = [i for i, h in enumerate(headers) if h_name in h]
                            if idx and idx[0] < len(parts):
                                val = parts[idx[0]].replace('**', '').strip()
                                return val if val else default
                            return default
                        except: return default

                    if in_section_25:
                        # [PROFILE-PARSING]: Đăng ký Preset nơ-ron 
                        p_name = get_safe_str('PROFILE NAME').upper()
                        if p_name:
                            self.profiles[p_name] = {
                                "num_ctx": get_safe_int('NUM_CTX', 4096),
                                "num_gpu": get_safe_int('NUM_GPU', 0),
                                "temperature": get_safe_float('TEMP', 0.7),
                                "repeat_penalty": get_safe_float('REPEAT_P', 1.1)
                            }
                        continue

                    try:
                        # GIẢI MÃ THAM SỐ ELITE: Chỉ nạp những gì Master chỉ định .
                        opts = {}
                        
                        ctx = get_safe_int('NUM_CTX', -1)
                        if ctx != -1: opts["num_ctx"] = ctx
                        
                        gpu = get_safe_int('NUM_GPU', -1)
                        if gpu != -1: opts["num_gpu"] = gpu
                        
                        temp = get_safe_float('TEMP', -1)
                        if temp != -1: opts["temperature"] = temp
                        
                        penalty = get_safe_float('REPEAT_P', -1)
                        if penalty != -1: opts["repeat_penalty"] = penalty
                        
                        opts["top_p"] = 0.9
                        opts["top_k"] = 40
                        
                        # [PROFILE-MERGING]: Hợp nhất Preset vào Role 
                        active_profile = get_safe_str('ACTIVE PROFILE').upper()
                        if active_profile and active_profile in self.profiles:
                            preset = self.profiles[active_profile]
                            # Chỉ lấy từ Profile nếu trong bảng Mapping để N/A hoặc rỗng 
                            if ctx == -1: opts["num_ctx"] = preset["num_ctx"]
                            if gpu == -1: opts["num_gpu"] = preset["num_gpu"]
                            if temp == -1: opts["temperature"] = preset["temperature"]
                            if penalty == -1: opts["repeat_penalty"] = preset["repeat_penalty"]

                        # Đọc Keep-alive nếu có, mặc định 5m 
                        keep_alive = get_safe_str('KEEP_ALIVE', '5m')
                        hardware = get_safe_str('HARDWARE', '').upper()
                        new_r_cache[role_key] = {'model': model_name, 'options': opts, 'keep_alive': keep_alive, 'hardware': hardware}
                    except Exception as e:
                        logger.error(f"Error parsing role {role_key}: {e}")
                        new_r_cache[role_key] = {'model': model_name}
            self._role_mapping_cache = new_r_cache
        except Exception as e:
            logger.error(f'❌ [UIE-PARSE-ERR] {e}')

    async def warmup_all_models(self):
        """GIAO THỨC TRIỆU HỒI TOÀN QUÂN: Nạp sẵn các model chiến lược ."""
        self._get_smart_params()
        unique_models = {}
        for role, cfg in self._role_mapping_cache.items():
            model = cfg.get('model')
            if model and model not in unique_models:
                unique_models[model] = {'role': role, 'cfg': cfg}
        
        logger.info(f"[GUARDIAN] Khởi động Giao thức Triệu hồi ({len(unique_models)} model)...")
        client = self._get_client()
        
        # 🕵️ [STEP-1]: Tầm soát Kho tàng (Tags) 
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
            except:
                pass

        for model, info in unique_models.items():
            cfg = info['cfg']
            role = info['role']
            
            # [ELITE-FILTER]: Chỉ triệu hồi những nơ-ron cần thiết 
            keep_alive_raw = str(cfg.get('keep_alive', '5m')).strip()
            if keep_alive_raw == '0' or model.lower() in ['faster-whisper', 'sdxl-turbo-rocm']:
                continue

            num_gpu_val = cfg.get('options', {}).get('num_gpu', -1)
            target_host = self.ollama_host_cpu if num_gpu_val == 0 else self.ollama_host_gpu
            other_host = self.ollama_host_cpu if target_host == self.ollama_host_gpu else self.ollama_host_gpu
            
            model_in_target = any(model in t for t in available_tags[target_host])
            model_in_other = any(model in t for t in available_tags[other_host])
            total_tags = len(available_tags[target_host]) + len(available_tags[other_host])

            # KIỂM TRA SỰ TỒN TẠI 
            if total_tags > 0 and not model_in_target and not model_in_other:
                logger.error(f"❌ [GUARDIAN] KHÔNG TÌM THẤY ĐẶC VỤ `{model}` TRONG PHÁO ĐÀI!")
                self.publish_mission_log("CRITICAL", f"[SỰ CỐ TÀI SẢN]: Đặc vụ `{model}` (Role: {role}) không tồn tại trong Thư viện. Cần Master Pull ngay !")
                continue
                
            # Nếu model không có ở target_host nhưng có ở other_host, ta chuyển host
            if not model_in_target and model_in_other:
                target_host = other_host

            # KIỂM TRA TRẠNG THÁI NẠP 
            if any(model in m for m in loaded_models[target_host]):
                logger.info(f"[GUARDIAN] Đặc vụ `{model}` đã có mặt tại vị trí ({target_host}).")
                continue

            try:
                logger.info(f"[GUARDIAN] Đang triệu hồi: {model} (Role: {role}) trên {target_host}...")
                keep_alive = cfg.get('keep_alive', '5m')
                try:
                    if str(keep_alive) == "-1": keep_alive = -1
                    elif str(keep_alive).isdigit(): keep_alive = int(keep_alive)
                except: pass

                await client.post(f"{target_host}/api/generate", json={
                    "model": model, "prompt": "", "keep_alive": keep_alive, "options": cfg.get('options', {})
                }, timeout=600.0)
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
            except: return 0
        return 0

    async def _enter_neural_gate(self, model_name: str):
        r = self._get_redis()
        if r:
            try: r.incr(self._get_active_key(model_name))
            except: pass

    async def _exit_neural_gate(self, model_name: str):
        r = self._get_redis()
        if r:
            try:
                val = r.decr(self._get_active_key(model_name))
                if val < 0: r.set(self._get_active_key(model_name), 0)
            except: pass

    def get_role_config(self, role):
        self._get_smart_params()
        role = role.upper()
        role_data = self._role_mapping_cache.get(role)
        
        # GIAO THỨC DỰ PHÒNG 3 TẦNG: Tuân thủ tuyệt đối rule_hardware.md 
        if not role_data:
            logger.warning(f"[ENGINE] Role '{role}' chưa được định nghĩa. Đang kích hoạt Giao thức Chuyển hướng...")
            for backup_role in ["PLANNER", "EXECUTOR", "RECEPTIONIST"]:
                backup_data = self._role_mapping_cache.get(backup_role)
                if backup_data:
                    return backup_data
            return {'model': 'qwen2.5:1.5b', 'options': {}}
        
        return role_data

    def load_software_rules(self):
        """📂 Trích xuất API keys và Base URLs từ rules_software.md ."""
        configs = {}
        paths = [
            '/intelligence/rules_software.md',
            'intelligence/rules_software.md',
            'D:/Docker/N8N/intelligence/rules_software.md'
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
                    if '|' in line and any(k in line for k in ['GEMINI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY']):
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 5:
                            var_match = re.search(r'`([A-Z_]+)`', parts[2])
                            url_match = re.search(r'`([^`]+)`', parts[3])
                            key_match = re.search(r'\(([^)]+)\)', parts[4])
                            
                            var_name = var_match.group(1) if var_match else None
                            base_url = url_match.group(1) if url_match else None
                            api_key = key_match.group(1) if key_match else None
                            if api_key:
                                api_key = api_key.strip("`'\" ")
                            
                            if var_name:
                                provider = var_name.lower().replace('_api_key', '')
                                configs[provider] = {
                                    'api_key': api_key,
                                    'base_url': base_url
                                }
            except Exception as e:
                logger.error(f"Error parsing rules_software.md: {e}")
        
        # Fallback to environment variables
        for p in ['gemini', 'anthropic', 'openai', 'deepseek']:
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
                    configs[p]['base_url'] = 'https://generativelanguage.googleapis.com/v1beta/openai/'
                elif p == 'anthropic':
                    configs[p]['base_url'] = 'https://api.anthropic.com/v1'
                elif p == 'openai':
                    configs[p]['base_url'] = 'https://api.openai.com/v1'
                elif p == 'deepseek':
                    configs[p]['base_url'] = 'https://api.deepseek.com'
                    
        return configs


    async def call_chat(self, messages, role='CHAT', model=None, json_mode=False, schema=None, options=None, profile=None, keep_alive=None, task_id=None, images=None, tools=None, **kwargs):
        """
        API giao tiếp với Bộ não Trung tâm (Ollama Dual-Engine).
        Tích hợp [DYNAMIC KEEP-ALIVE] & [COGNITIVE PROFILE].
        Hỗ trợ [NATIVE TOOL CALLING] (Function Calling).
        """
        # 🏛️ [MICROSERVICE-ROUTING]: Giao thức điều hướng trung tâm đa tầng 
        # [SELF-AWARENESS]: Chỉ chuyển hướng nếu không phải là tự gọi chính mình 
        services = [
            (self.executor_url, "EXECUTOR"),
            (self.planner_url, "PLANNER"),
            (self.brain_url, "BRAIN")
        ]
        
        for service_url, service_name in services:
            # Nếu đây là chính dịch vụ hiện tại, ta dừng chuyển hướng và tự xử lý 
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
                resp = await client.post(f"{service_url}/chat", json={
                    "messages": messages, "role": role, "model": model,
                    "json_mode": json_mode, "schema": schema, "options": options,
                    "profile": profile, "keep_alive": keep_alive, "task_id": task_id,
                    "images": images, "lock_timeout": kwargs.get('lock_timeout', 60),
                    "hlc": str(hlc.now())
                }, timeout=kwargs.get('timeout', 900.0))
                
                res_data = resp.json()
                return res_data.get('response') or res_data.get('answer') or ''
            except Exception as e:
                logger.error(f"❌ [ENGINE-CHAT-ERR]: {type(e).__name__}: {repr(e)}")
                continue
                
        # 🕒 [TIME-INJECTION]: Giao thức thời gian thực 
        import datetime
        import pytz
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.datetime.now(tz)
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        time_str = f"🕒 [SYSTEM_TIME]: Hiện tại là {current_time.strftime('%H:%M:%S')}, {days[current_time.weekday()]}, ngày {current_time.strftime('%d/%m/%Y')} (Giờ Việt Nam GMT+7)."
        
        if messages and messages[0].get('role') == 'system':
            if "[SYSTEM_TIME]" not in messages[0]['content']:
                messages[0]['content'] += f"\n\n{time_str}"
        else:
            messages.insert(0, {"role": "system", "content": time_str})
                
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
            except: pass

        # [AUTO-CONTEXT-INJECTION]: Giao thức Thấu thị Vĩnh cửu 
        if not kwargs.get('skip_memory'):
            try:
                # Trích xuất goal từ tin nhắn cuối cùng để tìm kiếm 
                query = messages[-1]['content'] if messages else ""
                if len(query) > 10:
                    vector = embed(query[:1000])
                    if vector:
                        memories = await qdrant_client.search_intel(vector, limit=3)
                        if memories:
                            mem_text = "\n".join([f"- {m.get('payload', {}).get('text', '')}" for m in memories])
                            messages.insert(0, {"role": "system", "content": f"[EXPERIENCE DNA]: Dựa trên di sản tri thức quá khứ, hãy lưu ý:\n{mem_text}"})
                            self._publish_thought(role, "[OMNIPRESENT]: Đã nạp di sản tri thức từ Qdrant .", task_id)
            except: pass

        # --- TIẾP TỤC LOGIC GỌI MODEL TRỰC TIẾP ---
        duration = 0.0
        role_cfg = self.get_role_config(role)
        final_model = model or role_cfg.get('model')
        

        max_attempts = 3
        for attempt in range(max_attempts):
            if attempt > 0:
                self.publish_mission_log("WARN", f"🔄 [FALLBACK]: Khởi chạy cơ chế dự phòng cho {final_model}...")
                try:
                    from core.utils.hardware_scheduler import hardware_scheduler
                    fb_info = await hardware_scheduler.resolve_smart_fallback(final_model, self, [role, "CHAT", "RESERVE_AGENT"])
                    if fb_info and fb_info.get("model"):
                        final_model = fb_info["model"]
                        self.publish_mission_log("INFO", f"✅ [SMART-FALLBACK]: Chuyển sang mô hình Local {final_model}")
                    else:
                        break # no fallback found
                except Exception as fb_err:
                    break

            # Estimate context length to auto-route long context queries to Gemini
            total_chars = sum(len(m.get('content', '')) for m in messages)
            estimated_tokens = total_chars // 4
            
            configs = self.load_software_rules()
            gemini_key = configs.get('gemini', {}).get('api_key')
            
            # Auto-route to Gemini 3.5 Flash for very long context
            if estimated_tokens > 8000 and gemini_key and not any(final_model.lower().startswith(p) for p in ['gemini-', 'gpt-', 'claude-']):
                self.publish_mission_log("INFO", f"🔄 Ngữ cảnh lớn ({estimated_tokens} tokens) vượt quá giới hạn local. Tự động chuyển hướng sang Gemini 3.5 Flash .")
                final_model = "gemini-3.5-flash"
                
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
            is_small = any(k in final_model.lower() for k in ["1.5b", "0.5b", "tiny", "phi3", "phi4-mini"])
            hw_col = role_cfg.get('hardware', '').upper()
            is_cpu_bound = kwargs.get('cpu_only') or is_small or ('CPU' in hw_col)
            
            if is_cpu_bound:
                final_options['num_gpu'] = 0
                # Giảm bớt ctx nếu chạy CPU để tiết kiệm RAM 
                if final_options.get('num_ctx', 4096) > 2048:
                    final_options['num_ctx'] = 2048
                
                # [NCNN-ESSENCE 1]: Tối ưu băng thông bộ nhớ NUMA (Tương tự Cache Layout của NCNN)
                # Chip Xeon E5 đa vi xử lý bắt buộc phải có NUMA-awareness để tránh thắt cổ chai bus bộ nhớ
                final_options['numa'] = True
                
                # [NCNN-ESSENCE 2]: Áp đặt bộ đệm MMAP để tối ưu I/O Load (Giống zero-copy của NCNN)
                if 'use_mmap' not in final_options:
                    final_options['use_mmap'] = True
                
                # [NCNN-ESSENCE 3]: Thread Affinity and NUMA Lock are now handled entirely by Zenith_Guardian.ps1 via OLLAMA_ENVIRONMENT variables.
                # We no longer inject num_thread here.
                
            final_keep_alive = keep_alive or role_cfg.get('keep_alive', '5m')
            
            # [TYPE-PURIFICATION]: Đảm bảo keep_alive là integer nếu là số 
            try:
                if str(final_keep_alive).replace('-', '').isdigit():
                    final_keep_alive = int(final_keep_alive)
            except: pass

            # 🖼️ [NEURAL-VISION]: Đính kèm hình ảnh vào tin nhắn cuối cùng nếu có 
            if images and len(messages) > 0:
                # Ollama expects images in the message object
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
                payload['tools'] = tools
            
            is_reasoning_model = any(k in final_model.lower() for k in ["r1", "thinking", "deepseek-v3"])
            
            if not is_reasoning_model:
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
            final_tool_calls = []
            
            try:
                last_log_time = time.time()
                now = last_log_time
                last_published_text = ""
                last_signal_check = now
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
                
                target_ollama_host = self.ollama_host_gpu if is_gpu else self.ollama_host_cpu
                
                # [PRE-FLIGHT CHECK]: Kiểm tra sự hiện diện của nơ-ron 
                if not is_cloud:
                    try:
                        ps_resp = await client.get(f'{target_ollama_host}/api/ps')
                        if ps_resp.status_code == 200:
                            ps_data = ps_resp.json()
                            is_loaded = any(final_model.lower() in m.get('name', '').lower() for m in ps_data.get('models', []))
                            if not is_loaded:
                                self._publish_thought(role, f"[NEURAL-SUMMON]: Đặc vụ `{final_model}` hiện không có mặt. Đang triệu tập gấp vào Engine (GPU={is_gpu}) ...", task_id)
                    except: pass

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
                            
                        async with client.stream('POST', req_url, headers=req_headers, json=req_payload, timeout=900.0) as resp:
                            if resp.status_code != 200:
                                logger.error(f"❌ [API-ERR] {resp.status_code}")
                                err_msg = f"Error: [API-ERR] Server/API trả về mã {resp.status_code} ."
                                self._publish_thought(role, err_msg, task_id)
                                if attempt == max_attempts - 1:
                                    return err_msg
                                else:
                                    break # break the async with to continue the attempt loop

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
                                            except: pass
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
                                            except: pass
                                else:
                                    chunk = json.loads(line)
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
                                        self._publish_thought(role, "[HỆ THỐNG]: Đang khởi động luồng tư duy sâu...", task_id)
                                        last_log_time = time.time()
                                    thinking_content += reasoning_token
                                
                                if token:
                                    # [CHUNK-AGNOSTIC DETECTION]: Phát hiện thẻ <think> bất kể bị chia nhỏ 
                                    temp_buffer = (full_content + thinking_content + token)[-20:]
                                    
                                    if not is_thinking and '<think>' in temp_buffer:
                                        is_thinking = True
                                        self._publish_thought(role, "[HỆ THỐNG]: Đang khởi động luồng tư duy sâu...", task_id)
                                    
                                    if is_thinking and '</think>' in temp_buffer:
                                        is_thinking = False
                                        # Phát sóng toàn bộ tư duy khi kết thúc
                                        self._publish_thought(role, f"[LUỒNG TƯ DUY NỘI TÂM]:\n{thinking_content}", task_id)
                                    
                                    if is_thinking:
                                        thinking_content += token
                                    else:
                                        full_content += token

                                        if display_thought:
                                            msg = f"{display_thought}"
                                            if msg != last_published_text:
                                                self._publish_thought(role, msg, task_id, stream_id=stream_id)
                                                last_published_text = msg
                                                last_log_time = now
                                else:
                                    # Cập nhật soạn thảo văn bản mỗi 3.0 giây
                                    now = time.time()
                                    if now - last_log_time > 3.0 and full_content.strip():
                                        display_text = full_content.strip()
                                        msg = f"{display_text}"
                                        if msg != last_published_text:
                                            self._publish_thought(role, msg, task_id, stream_id=stream_id)
                                            last_published_text = msg
                                            last_log_time = now

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
                    except: pass

                self._publish_thought(role, f"Hoàn tất trong {duration:.2f}s. (Size: {len(full_content)} chars)", task_id)

                # [LATENCY-REPORT]: Báo cáo thời gian phản hồi cho Master
                latency_payload = json.dumps({
                    "tag": "LATENCY",
                    "msg": f"⏱️ [{role}] {final_model}: {duration:.2f}s",
                    "ts": time.time(),
                    "task_id": task_id or "system"
                }, ensure_ascii=False)
                r = self._get_redis()
                if r: r.publish("monitor:log_channel", latency_payload)

                if final_tool_calls:
                    self._publish_thought(role, f"🛠️ [NATIVE-TOOL-CALL]: Nơ-ron quyết định sử dụng {len(final_tool_calls)} công cụ.", task_id)
                    return {"answer": full_content, "tool_calls": final_tool_calls}

                if json_mode or schema:
                    try: 
                        # [ROBUST JSON EXTRACTION]: Chỉ trích xuất khi được yêu cầu 
                        return self._extract_json_from_text(full_content)
                    except: 
                        self._publish_thought(role, f"Lỗi parse JSON. Trả về text thô.", task_id)
                        return full_content
                
                # 📜 [LEGACY-COMPATIBILITY]: Luôn trả về chuỗi văn bản cho các Đặc vụ cũ 
                return str(full_content)
                
            except Exception as e:
                err_msg = f"Error: [NEURAL-ENGINE-ERR] {str(e)}"
                logger.error(err_msg)
                self._publish_thought(role, err_msg, task_id)
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
        except: pass
        
        # 2. Tìm trong Markdown Code Blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group(1))
            except: pass
            
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
            except:
                continue
        
        if 'last_valid' in locals():
            return last_valid
            
        # 4. Cố gắng làm sạch text thô nếu không tìm thấy khối nào hoàn hảo
        # (Xóa các phần <think>...</think> nếu còn sót lại)
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        if cleaned_text.startswith('{') and cleaned_text.endswith('}'):
            try:
                return json.loads(cleaned_text)
            except: pass
            
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
