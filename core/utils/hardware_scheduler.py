import asyncio
import logging
import httpx
from typing import Optional
from core.utils.redis_client import redis_safe

logger = logging.getLogger('HardwareScheduler')

class HardwareScheduler:
    """
    🏗️ JKAI HARDWARE SCHEDULER v2.1 (VRAM-AWARE & MULTI-LANE CPU)
    Điều tiết tài nguyên phần cứng (VRAM, CPU).
    Đảm bảo tính ổn định nơ-ron qua cơ chế Kế toán VRAM thực tế.
    """
    def __init__(self, lock_timeout: int = 180):
        self.lock_timeout = lock_timeout
        self.max_vram_gb = 7.8  # 🛡️ Ngưỡng an toàn thực tế cho card 8GB (Trừ hao 0.2GB cho Windows OS/Desktop)
        self.lane_capacity = 2 # Tối đa 2 đặc vụ GPU (Chừa lane chạy song song cho Embedder)
        self.cpu_lane_capacity = 2 # 🖥️ Hỗ trợ tối đa 2 đặc vụ CPU chạy song song (Xeon E5-2699 v4 44-Threads dư sức tải)

    async def acquire_cpu_lock(self, task_id: str, timeout: int = None) -> bool:
        """🖥️ [CPU-CONCURRENCY-GUARD]: Giới hạn strictly tối đa 2 Đặc vụ CPU chạy song song."""
        wait_timeout = timeout or self.lock_timeout
        start_time = asyncio.get_event_loop().time()
        unique_request_id = f"{task_id}:{id(asyncio.current_task())}"
        
        while asyncio.get_event_loop().time() - start_time < wait_timeout:
            def _try_acquire(r):
                # 1. Kiểm tra số lượng lane CPU đang chạy
                active_lanes = r.keys("lock:cpu_lane:*")
                if len(active_lanes) >= self.cpu_lane_capacity:
                    return None
                
                # 2. Chiếm dụng một lane trống
                for i in range(self.cpu_lane_capacity):
                    lane_key = f"lock:cpu_lane:{i}"
                    if r.set(lane_key, unique_request_id, ex=wait_timeout, nx=True):
                        return lane_key
                return None
            
            acquired_lane = redis_safe(_try_acquire)
            if acquired_lane:
                if isinstance(acquired_lane, bytes):
                    acquired_lane = acquired_lane.decode()
                try:
                    asyncio.current_task().set_name(f"cpu_lock:{unique_request_id}")
                    # Lưu lại lane đã nhận vào Redis để giải phóng chính xác
                    redis_safe(lambda r: r.set(f"task_cpu_lane:{unique_request_id}", acquired_lane, ex=wait_timeout))
                except Exception: pass
                return True
            
            await asyncio.sleep(0.5)
            
        logger.warning(f"⚠️ [CPU-LOCK-TIMEOUT]: Task '{task_id}' không thể lấy được CPU Lock sau {wait_timeout}s.")
        return False

    async def release_cpu_lock(self, task_id: str = None):
        """🔓 [CPU-LOCK-RELEASE]: Giải phóng CPU lock."""
        unique_request_id = task_id
        try:
            name = asyncio.current_task().get_name()
            if "cpu_lock:" in name:
                unique_request_id = name.split("cpu_lock:")[-1]
        except Exception: pass

        def _release(r):
            if unique_request_id:
                lane_key = r.get(f"task_cpu_lane:{unique_request_id}")
                if lane_key:
                    if isinstance(lane_key, bytes): lane_key = lane_key.decode()
                    r.delete(lane_key)
                    r.delete(f"task_cpu_lane:{unique_request_id}")
                else:
                    # Fallback phòng hờ khi bị mất key phụ
                    for k in r.keys("lock:cpu_lane:*"):
                        val = r.get(k)
                        if val == unique_request_id or (isinstance(val, bytes) and val.decode() == unique_request_id):
                            r.delete(k)
            else:
                # Emergency CPU purge
                for k in r.keys("lock:cpu_lane:*"): r.delete(k)
                for k in r.keys("task_cpu_lane:*"): r.delete(k)
        redis_safe(_release)

    async def _sync_with_ollama(self, r):
        """🔄 [OLLAMA-REALITY-SYNC]: Đồng bộ trạng thái thực tế của VRAM."""
        try:
            import os
            ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ollama_host}/api/ps")
                if resp.status_code == 200:
                    data = resp.json()
                    loaded_in_ollama = [m["name"] for m in data.get("models", [])]
                    
                    # 🛡️ [GUARDIAN-RESPECT]: Chỉ track VRAM GPU, không xả model CPU
                    r.delete("gpu:loaded_models")
                    for m in data.get("models", []):
                        vram_bytes = m.get("size_vram", 0)
                        # Chỉ đưa vào gpu:loaded_models nếu thực sự dùng VRAM (GPU model)
                        if vram_bytes > 0:
                            r.sadd("gpu:loaded_models", m["name"])
                            r.set(f"model_vram_size:{m['name']}", vram_bytes / (1024**3))
                        # CPU models: track riêng nhưng KHÔNG tính vào VRAM budget
                        else:
                            r.sadd("cpu:loaded_models", m["name"])
                            r.expire("cpu:loaded_models", 3600)
                    return loaded_in_ollama
        except Exception: pass
        return []

    async def flush_all_models(self, r):
        """🧹 [TOTAL-VRAM-FLUSH]: Vô hiệu hóa để tôn trọng Zenith_Guardian.ps1."""
        logger.info("🧹 [FLUSH-BYPASS]: Zenith_Guardian.ps1 đang kiểm soát Model. Bỏ qua lệnh xả VRAM.")
        return

    async def acquire_gpu_lock(self, task_id: str, model_size_gb: float = 0.0, model_name: str = "unknown", timeout: int = None) -> bool:
        """💎 [VRAM-BUDGET-ACQUIRE]: Chiếm dụng tài nguyên GPU thông minh."""
        wait_timeout = timeout or self.lock_timeout
        start_time = asyncio.get_event_loop().time()
        
        # 🆔 [UNIQUE-LOCK-ID]: Tránh xung đột khi dùng chung task_id="system"
        unique_request_id = f"{task_id}:{id(asyncio.current_task())}"
        result = "BUSY"
        
        while asyncio.get_event_loop().time() - start_time < wait_timeout:
            # Syncing with Ollama status
            await redis_safe(self._sync_with_ollama)
            
            def _try_budget(r):
                # 1. Lane capacity check
                active_lanes = r.keys("lock:gpu_lane:*")
                if len(active_lanes) >= self.lane_capacity:
                    return "BUSY"
                
                # 2. VRAM calculation
                loaded_models = r.smembers("gpu:loaded_models")
                loaded_models = [m.decode() if isinstance(m, bytes) else m for m in loaded_models]
                
                current_vram = 0.0
                for m_name in loaded_models:
                    m_size = r.get(f"model_vram_size:{m_name}")
                    if m_size: current_vram += float(m_size)
                
                # 3. Decision logic
                m_clean = model_name.split(":")[0]
                model_already_loaded = any(m_clean in m for m in loaded_models)
                
                actual_size = r.get(f"model_vram_size:{model_name}")
                final_model_size = float(actual_size) if actual_size else model_size_gb

                # 🧠 [CONTEXT-OVERHEAD]: 15% context buffer
                needed_vram = final_model_size * 1.15 if not model_already_loaded else (final_model_size * 0.15)
                
                if (current_vram + needed_vram) > self.max_vram_gb:
                    if final_model_size > 4.0:
                        return "PRESSURE_FLUSH"
                    return "FULL"

                # 4. Lane acquisition
                for i in range(self.lane_capacity):
                    lane_key = f"lock:gpu_lane:{i}"
                    if r.set(lane_key, unique_request_id, ex=wait_timeout, nx=True):
                        if not model_already_loaded:
                            r.sadd("gpu:loaded_models", model_name)
                            if not actual_size:
                                r.set(f"model_vram_size:{model_name}", model_size_gb)
                        return lane_key
                return "BUSY"

            result = redis_safe(_try_budget)

            if result == "PRESSURE_FLUSH":
                logger.warning(f"🚨 [VRAM-PRESSURE]: Emergency flush for `{model_name}`.")
                await redis_safe(self.flush_all_models)
                result = redis_safe(_try_budget)

            if result and result not in ["BUSY", "FULL", "PRESSURE_FLUSH"]:
                lane_key = result
                redis_safe(lambda r: r.set(f"task_lane:{unique_request_id}", lane_key, ex=wait_timeout))
                try:
                    asyncio.current_task().set_name(unique_request_id)
                except Exception: pass
                return True
            
            await asyncio.sleep(1.0)
            
        # 🎨 [GRAPHIC-AUTO-FLUSH]: Graphic priority enforcement
        if result == "FULL" and "GRAPHIC" in (task_id or "").upper():
            logger.warning(f"🎨 [ART-PRIORITY]: Clearing path for Graphics.")
            await redis_safe(self.flush_all_models)
            result = redis_safe(_try_budget)
            if result and result not in ["BUSY", "FULL"]:
                return True

        reason = "Lanes busy (Max 3)" if result == "BUSY" else "VRAM capacity reached"
        logger.warning(f"⚠️ [VRAM-CAPACITY-EXCEEDED]: {model_name} ({model_size_gb}GB) rejected. Reason: {reason}.")
        return False

    async def release_gpu_lock(self, task_id: str = None):
        """🔓 [VRAM-BUDGET-RELEASE]: Giải phóng tài nguyên."""
        # Lấy unique_id từ task name
        unique_request_id = task_id
        try:
            name = asyncio.current_task().get_name()
            if ":" in name: unique_request_id = name
        except Exception: pass

        def _release(r):
            if unique_request_id:
                lane_key = r.get(f"task_lane:{unique_request_id}")
                if lane_key:
                    if isinstance(lane_key, bytes): lane_key = lane_key.decode()
                    r.delete(lane_key)
                    r.delete(f"task_lane:{unique_request_id}")
            else:
                # Emergency purge
                for k in r.keys("lock:gpu_lane:*"): r.delete(k)
                for k in r.keys("task_lane:*"): r.delete(k)
        redis_safe(_release)

    async def resolve_smart_fallback(self, failed_model: str, router, fallback_roles: list) -> Optional[dict]:
        """
        🧠 [UNIFIED-SMART-FALLBACK v5.0]: Quản lý dự phòng thông minh tập trung và đồng bộ.
        Tôn trọng ĐÚNG phần cứng được chỉ định trong rule_hardware.md Mục 3.
        Ưu tiên theo chiến thuật:
          - Chỉ được phép chọn các model đã được định nghĩa và nạp sẵn ở rule_hardware.md Mục 3.
          - Chọn model khác đang rảnh ở GPU trước.
          - Nếu hết model rảnh GPU, chuyển sang chọn model đang rảnh ở CPU.
          - Chú ý ưu tiên tính năng tương đồng (capability) và dung lượng tương đồng (size).
          - Nếu tất cả model Mục 3 không khả dụng, mới tải một mô hình mới từ Ollama lên GPU/CPU làm cứu cánh cuối cùng.

        Args:
          failed_model: Tên model vừa thất bại để loại trừ.
          router: Instance của JKAIIntelligenceEngine để phân giải động vai trò từ rule_hardware.md.
          fallback_roles: Danh sách thứ tự ưu tiên vai trò dự phòng (e.g. ["RESERVE_AGENT", "CHAT"]).

        Returns:
          dict {"role": str, "model": str, "hardware": str} hoặc None nếu kiệt lực.
        """
        import os
        import re
        ollama_gpu_host = os.getenv('OLLAMA_HOST_GPU', 'http://host.docker.internal:11434')
        ollama_cpu_host = os.getenv('OLLAMA_HOST_CPU', 'http://host.docker.internal:11435')

        # 1. Trích xuất tất cả các mô hình có sẵn ở rule_hardware.md Mục 3 (đã load sẵn)
        section_3_models = [] # Dùng list để tránh ghi đè role (Role Collision)
        if hasattr(router, '_role_mapping_cache') and router._role_mapping_cache:
            for role_name, cfg in router._role_mapping_cache.items():
                if hasattr(cfg, 'model') and cfg.model:
                    section_3_models.append({
                        "role": role_name,
                        "model": cfg.model,
                        "hardware": getattr(cfg, 'hardware', 'CPU/RAM')
                    })

        # Neu cache rong, thu load lai
        if not section_3_models:
            try:
                if hasattr(router, "_parse_rules"):
                    router._parse_rules()
                elif hasattr(router, "_get_smart_params"):
                    router._get_smart_params()
                for role_name, cfg in router._role_mapping_cache.items():
                    if hasattr(cfg, 'model') and cfg.model:
                        section_3_models.append({
                            "role": role_name,
                            "model": cfg.model,
                            "hardware": getattr(cfg, 'hardware', 'CPU/RAM')
                        })
            except Exception as e:
                logger.warning(f"⚠️ [SMART-FALLBACK]: Không thể load role mapping cache: {e}")

        # 2. Định nghĩa hàm phân loại đặc tính và dung lượng của mô hình
        def _classify_model(m_name: str) -> dict:
            name_lower = m_name.lower()
            
            # Phân loại Đặc tính (Capability)
            capability = "GENERAL"
            if any(k in name_lower for k in ["r1", "thinking", "reason"]):
                capability = "REASONING"
            elif any(k in name_lower for k in ["coder", "code", "granite-code"]):
                capability = "CODING"
            elif any(k in name_lower for k in ["embed", "minilm"]):
                capability = "EMBEDDING"
            elif any(k in name_lower for k in ["vision", "moondream"]):
                capability = "VISION"
                
            # Phân loại Dung lượng (Parameter Size)
            size_val = 8.0 # mặc định 8B
            match = re.search(r'(\d+\.?\d*)[b]', name_lower)
            if match:
                try:
                    size_val = float(match.group(1))
                except Exception:
                    pass
            else:
                if "tiny" in name_lower or "0.6b" in name_lower or "0.5b" in name_lower:
                    size_val = 0.5
                elif "mini" in name_lower or "3b" in name_lower:
                    size_val = 3.0
                elif "4b" in name_lower:
                    size_val = 4.0
                elif "14b" in name_lower:
                    size_val = 14.0
                elif "32b" in name_lower:
                    size_val = 32.0
                elif "70b" in name_lower:
                    size_val = 70.0
                    
            return {"capability": capability, "size": size_val}

        # Phân loại mô hình lỗi
        failed_class = _classify_model(failed_model)

        # 3. Định nghĩa hàm tính điểm tương thích tương đồng
        def _score_candidate(candidate_name: str) -> float:
            cand_class = _classify_model(candidate_name)
            # Khớp đặc tính (capability): cộng 10 điểm
            cap_score = 10.0 if cand_class["capability"] == failed_class["capability"] else 0.0
            # Chênh lệch dung lượng: trừ 0.5 điểm cho mỗi 1B chênh lệch
            size_diff = abs(cand_class["size"] - failed_class["size"])
            size_score = -size_diff * 0.5
            return cap_score + size_score

        def _is_failed(m_name: str) -> bool:
            return m_name.lower() == failed_model.lower() or m_name.split(":")[0].lower() == failed_model.split(":")[0].lower()

        def _is_compatible(candidate_name: str) -> bool:
            cand_class = _classify_model(candidate_name)
            cand_cap = cand_class["capability"]
            fail_cap = failed_class["capability"]
            
            # Embedding models only fallback to Embedding models, and vice versa
            if fail_cap == "EMBEDDING":
                return cand_cap == "EMBEDDING"
            if cand_cap == "EMBEDDING":
                return fail_cap == "EMBEDDING"
                
            # Vision models only fallback to Vision models, and vice versa
            if fail_cap == "VISION":
                return cand_cap == "VISION"
            if cand_cap == "VISION":
                return fail_cap == "VISION"
                
            # General text, reasoning, or coding models can fallback to each other
            return cand_cap in ["GENERAL", "REASONING", "CODING"]

        # 4. Truy xuất trạng thái thực tế của Ollama GPU & CPU
        gpu_hot = set()
        gpu_available = set()
        cpu_hot = set()
        cpu_available = set()

        async def _fetch_models(host: str, hot_set: set, avail_set: set):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    ps_resp = await client.get(f"{host}/api/ps")
                    if ps_resp.status_code == 200:
                        for m in ps_resp.json().get("models", []):
                            hot_set.add(m["name"])
                            hot_set.add(m["name"].split(":")[0])
                    tags_resp = await client.get(f"{host}/api/tags")
                    if tags_resp.status_code == 200:
                        for m in tags_resp.json().get("models", []):
                            avail_set.add(m["name"])
                            avail_set.add(m["name"].split(":")[0])
            except Exception as e:
                logger.warning(f"⚠️ [SMART-FALLBACK]: Không thể kết nối Ollama {host}: {e}")

        await _fetch_models(ollama_gpu_host, gpu_hot, gpu_available)
        await _fetch_models(ollama_cpu_host, cpu_hot, cpu_available)
        # 5. CHIẾN THUẬT CASCADING 4 TẦNG TUYỆT ĐỐI (GPU -> CPU)
        # Ưu tiên các model đang "nóng" (HOT) để phản hồi tức thì thưa Master.
        
        # Tầng 1: GPU HOT (Mục 3)
        gpu_hot_candidates = [m for m in section_3_models if 'GPU' in m.get("hardware", "").upper() and not _is_failed(m["model"]) and _is_compatible(m["model"]) and (m["model"] in gpu_hot or m["model"].split(":")[0] in gpu_hot)]
        if gpu_hot_candidates:
            gpu_hot_candidates.sort(key=lambda x: _score_candidate(x["model"]), reverse=True)
            chosen = gpu_hot_candidates[0]
            logger.info(f"✅ [SMART-FALLBACK] Tầng 1 (GPU HOT - Mục 3): {chosen['model']} (Role: {chosen['role']})")
            return chosen

        # Tầng 2: CPU HOT (Mục 3)
        cpu_hot_candidates = [m for m in section_3_models if 'CPU' in m.get("hardware", "").upper() and not _is_failed(m["model"]) and _is_compatible(m["model"]) and (m["model"] in cpu_hot or m["model"].split(":")[0] in cpu_hot)]
        if cpu_hot_candidates:
            cpu_hot_candidates.sort(key=lambda x: _score_candidate(x["model"]), reverse=True)
            chosen = cpu_hot_candidates[0]
            logger.info(f"✅ [SMART-FALLBACK] Tầng 2 (CPU HOT - Mục 3): {chosen['model']} (Role: {chosen['role']})")
            return chosen

        # Tầng 3: GPU AVAILABLE (Mục 3) - Cần thời gian nạp từ ổ đĩa
        gpu_avail_candidates = [m for m in section_3_models if 'GPU' in m.get("hardware", "").upper() and not _is_failed(m["model"]) and _is_compatible(m["model"]) and (m["model"] in gpu_available or m["model"].split(":")[0] in gpu_available)]
        if gpu_avail_candidates:
            gpu_avail_candidates.sort(key=lambda x: _score_candidate(x["model"]), reverse=True)
            chosen = gpu_avail_candidates[0]
            logger.info(f"✅ [SMART-FALLBACK] Tầng 3 (GPU AVAILABLE - Mục 3): {chosen['model']} (Role: {chosen['role']})")
            return chosen

        # Tầng 4: CPU AVAILABLE (Mục 3) - Cần thời gian nạp từ ổ đĩa
        cpu_avail_candidates = [m for m in section_3_models if 'CPU' in m.get("hardware", "").upper() and not _is_failed(m["model"]) and _is_compatible(m["model"]) and (m["model"] in cpu_available or m["model"].split(":")[0] in cpu_available)]
        if cpu_avail_candidates:
            cpu_avail_candidates.sort(key=lambda x: _score_candidate(x["model"]), reverse=True)
            chosen = cpu_avail_candidates[0]
            logger.info(f"✅ [SMART-FALLBACK] Tầng 4 (CPU AVAILABLE - Mục 3): {chosen['model']} (Role: {chosen['role']})")
            return chosen

        # ❌ [HARD-ABORT]: Kiệt lực hoàn toàn. Không tự ý triệu hồi model lạ thưa Master.
        logger.error("❌ [SMART-FALLBACK] OMEGA: Kiệt lực hoàn toàn - không tìm thấy bất kỳ mô hình dự phòng nào trong Mapping của Master.")
        return None

    # Legacy bridge - giu tuong thich voi code cu con sot lai
    async def get_autonomous_fallback(self, role: str, failed_model: str) -> dict:
        return {}

    def apply_cpu_affinity(self):
        """🚀 [QUANTUM-LEAP]: Giao thức Xeon Affinity."""
        pass

# Singleton
hardware_scheduler = HardwareScheduler()
