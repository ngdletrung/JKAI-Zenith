import os
import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZenithSteward")

class ZenithSteward:
    def __init__(self):
        self.gpu_lock = asyncio.Lock()
        self.current_tenant = None  # 'ollama' or 'stable-diffusion'
        self.ollama_host = os.getenv("OLLAMA_INTERNAL_HOST", "http://host.docker.internal:11434")
        self.sd_host = os.getenv("SD_INTERNAL_HOST", "http://stable-diffusion:7860")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_gpu_permission(self, requested_service: str, model_name: str = None):
        """
        Quy tắc vĩ mô Elite: Một thẻ đồ họa, một chủ nhân.
        Bật/Tắt container để giải phóng 100% VRAM khi cần thiết.
        """
        if requested_service == 'cpu-only':
            return True

        try:
            # 🕒 [DEADLOCK-PROTECTION]: Giới hạn thời gian chờ khóa GPU
            await asyncio.wait_for(self.gpu_lock.acquire(), timeout=60.0)
            
            if self.current_tenant == requested_service:
                # Nếu là SD, kiểm tra xem nó còn sống không
                if requested_service == 'stable-diffusion':
                    if not await self._is_container_running('stable-diffusion'):
                        await self._start_container('stable-diffusion')
                return True
        except asyncio.TimeoutError:
            logger.error("🚨 [STEWARD] GPU Lock Timeout! Bypassing or forcing release...")
            self.gpu_lock.release() # Force release if possible
            return False

            try:
                # 1. Giải phóng chủ nhân cũ
                if self.current_tenant == 'ollama':
                    await self._unload_ollama()
                elif self.current_tenant == 'stable-diffusion':
                    await self._stop_container('stable-diffusion')
    
                # 2. Kích hoạt chủ nhân mới
                if requested_service == 'stable-diffusion':
                    await self._start_container('stable-diffusion')
                
                self.current_tenant = requested_service
                return True
            finally:
                if self.gpu_lock.locked():
                    self.gpu_lock.release()

    async def _unload_ollama(self):
        """Dọn dẹp VRAM Ollama triệt để."""
        try:
            ps = await self._client.get(f"{self.ollama_host}/api/ps")
            if ps.status_code == 200:
                for m in ps.json().get("models", []):
                    await self._client.post(f"{self.ollama_host}/api/generate", 
                        json={"model": m['name'], "keep_alive": 0}, timeout=5.0)
            logger.info("🗑️ [STEWARD] Ollama VRAM purged.")
        except Exception as e:
            logger.error(f"❌ [STEWARD] Failed to unload Ollama: {e}")

    async def _is_container_running(self, name: str):
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "-q", "-f", f"name={name}",
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return bool(stdout.strip())
        except: return False

    async def _start_container(self, name: str):
        logger.info(f"🚀 [STEWARD] Starting {name} container...")
        proc = await asyncio.create_subprocess_exec("docker", "start", name)
        await proc.wait()
        await asyncio.sleep(5) 

    async def _stop_container(self, name: str):
        logger.info(f"🛑 [STEWARD] Stopping {name} container to reclaim VRAM...")
        proc = await asyncio.create_subprocess_exec("docker", "stop", name)
        await proc.wait()

    async def report_completion(self, service: str):
        if service == 'stable-diffusion':
            logger.info("✅ [STEWARD] Graphics task done. Auto-closing SD to free VRAM.")
            await self._stop_container('stable-diffusion')
            self.current_tenant = None
        else:
            logger.info(f"✅ [STEWARD] {service} task done. Keeping in VRAM for performance.")

steward = ZenithSteward()
