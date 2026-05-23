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
                except: pass
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
        except: pass

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
        except: pass
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
                except: pass
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
        except: pass

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
        🧠 [UNIFIED-SMART-FALLBACK v4.0]: Quản lý dự phòng thông minh tập trung.
        Tôn trọng ĐÚNG phần cứng được chỉ định trong rule_hardware.md:
          - Role cấu hình GPU/VRAM → chỉ tìm fallback trong GPU Ollama (port 11434)
          - Role cấu hình CPU/RAM  → chỉ tìm fallback trong CPU Ollama (port 11435)

        Ưu tiên theo chiến thuật 3 tầng:
          Tầng 1 — HOT (đang nạp sẵn trong đúng phần cứng): Tránh độ trễ nạp.
          Tầng 2 — AVAILABLE (có sẵn trong thư viện đúng phần cứng): Cần warm-up ngắn.
          Tầng 3 — ORDERED (thứ tự ưu tiên vai trò, đúng phần cứng): Cứu cánh tối hậu.

        Args:
            failed_model: Tên model vừa thất bại để loại trừ.
            router: Instance ModelRouter để phân giải động vai trò từ rule_hardware.md.
            fallback_roles: Danh sách thứ tự ưu tiên vai trò dự phòng (e.g. ["RESERVE_AGENT", "CHAT"]).

        Returns:
            dict {"role": str, "model": str, "hardware": str} hoặc None nếu kiệt sức.
        """
        import os
        ollama_gpu_host = os.getenv('OLLAMA_HOST_GPU', 'http://host.docker.internal:11434')
        ollama_cpu_host = os.getenv('OLLAMA_HOST_CPU', 'http://host.docker.internal:11435')

        # Bước 1: Phân giải động danh sách ứng viên từ Router
        role_candidates = []
        for role_name in fallback_roles:
            fb_cfg = router.get_role_config(role_name)
            if fb_cfg and fb_cfg.get("model"):
                hw = fb_cfg.get("hardware", "CPU/RAM")
                role_candidates.append({
                    "role": role_name,
                    "model": fb_cfg.get("model"),
                    "hardware": hw,
                    # Chọn đúng Ollama host theo phần cứng được chỉ định
                    "ollama_host": ollama_gpu_host if "GPU" in hw.upper() else ollama_cpu_host
                })

        def _is_failed(model_name: str) -> bool:
            return model_name == failed_model or model_name.split(":")[0] == failed_model.split(":")[0]

        def _in_set(model_name: str, model_set: set) -> bool:
            return model_name in model_set or model_name.split(":")[0] in model_set

        # Bước 2: Truy xuất HOT & AVAILABLE cho từng host riêng biệt
        # (Cache theo host để tránh gọi trùng)
        host_hot_cache: dict[str, set] = {}
        host_available_cache: dict[str, set] = {}

        async def _fetch_host_models(host: str):
            if host in host_hot_cache:
                return
            hot = set()
            avail = set()
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    ps_resp = await client.get(f"{host}/api/ps")
                    if ps_resp.status_code == 200:
                        for m in ps_resp.json().get("models", []):
                            hot.add(m["name"])
                            hot.add(m["name"].split(":")[0])

                    tags_resp = await client.get(f"{host}/api/tags")
                    if tags_resp.status_code == 200:
                        for m in tags_resp.json().get("models", []):
                            avail.add(m["name"])
                            avail.add(m["name"].split(":")[0])
            except Exception as e:
                logger.warning(f"⚠️ [SMART-FALLBACK]: Lỗi kết nối {host}: {e}")
            host_hot_cache[host] = hot
            host_available_cache[host] = avail

        # Fetch models cho từng host cần thiết
        needed_hosts = set(c["ollama_host"] for c in role_candidates)
        for h in needed_hosts:
            await _fetch_host_models(h)

        # Tầng 1: HOT — nạp sẵn ĐÚNG phần cứng
        for candidate in role_candidates:
            m = candidate["model"]
            host = candidate["ollama_host"]
            hw = candidate["hardware"]
            hot_set = host_hot_cache.get(host, set())
            if not _is_failed(m) and _in_set(m, hot_set):
                logger.info(f"✅ [SMART-FALLBACK] Tầng 1 HOT [{hw}]: role={candidate['role']} model={m} host={host}")
                return {**candidate, "note": f"Nơ-ron sẵn sàng thực chiến HOT [{hw}]."}

        # Tầng 2: AVAILABLE — có sẵn trong thư viện ĐÚNG phần cứng
        for candidate in role_candidates:
            m = candidate["model"]
            host = candidate["ollama_host"]
            hw = candidate["hardware"]
            avail_set = host_available_cache.get(host, set())
            if not _is_failed(m) and _in_set(m, avail_set):
                logger.info(f"✅ [SMART-FALLBACK] Tầng 2 AVAILABLE [{hw}]: role={candidate['role']} model={m} host={host}")
                return {**candidate, "note": f"Nơ-ron dự bị từ Thư viện AVAILABLE [{hw}]."}

        # Tầng 3: ORDERED — cứu cánh theo thứ tự, vẫn giữ đúng phần cứng
        for candidate in role_candidates:
            m = candidate["model"]
            hw = candidate["hardware"]
            if not _is_failed(m):
                logger.info(f"✅ [SMART-FALLBACK] Tầng 3 ORDERED [{hw}]: role={candidate['role']} model={m}")
                return {**candidate, "note": f"Nơ-ron theo thứ tự ưu tiên ORDERED [{hw}]."}

        logger.error("❌ [SMART-FALLBACK] OMEGA: Kiệt lực hoàn toàn — không tìm được fallback đúng phần cứng.")
        return None

    # Legacy bridge — giữ tương thích với code cũ còn sót lại
    async def get_autonomous_fallback(self, role: str, failed_model: str) -> dict:
        return {}

    def apply_cpu_affinity(self):
        """🚀 [QUANTUM-LEAP]: Giao thức Xeon Affinity."""
        pass

# Singleton
hardware_scheduler = HardwareScheduler()
