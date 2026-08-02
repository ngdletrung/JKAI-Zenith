# [ZENITH FILE DIRECTIVE]
# - File: core/os/world_state.py
# - Role: World State representation and active Monitor v2
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v2.0 (Integrated)

import os
import json
import time
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Thư viện dùng chung của lõi
from core.utils.engine import engine
from core.config import settings

class HardwareTelemetry(BaseModel):
    cpu_percent: int = 0
    ram_percent: int = 0
    gpu_percent: int = 0
    timestamp: float = 0.0

class WorkspaceState(BaseModel):
    path: str = ""
    active_branch: str = "main"
    is_dirty: bool = False
    modified_files: List[str] = Field(default_factory=list)

class WorldState(BaseModel):
    hardware: HardwareTelemetry = Field(default_factory=HardwareTelemetry)
    workspace: WorkspaceState = Field(default_factory=WorkspaceState)
    available_tools: List[str] = Field(default_factory=list)
    infrastructure_health: Dict[str, str] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class CircuitBreaker:
    """Simple in-memory circuit breaker cho infrastructure health checks."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_count: Dict[str, int] = {}
        self.last_failure: Dict[str, float] = {}
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

    def allow_request(self, service: str) -> bool:
        now = time.time()
        failures = self.failure_count.get(service, 0)
        last_fail = self.last_failure.get(service, 0.0)
        if failures >= self.failure_threshold and (now - last_fail) < self.recovery_timeout:
            return False
        if failures >= self.failure_threshold:
            self.failure_count[service] = 0
        return True

    def record_failure(self, service: str) -> None:
        self.failure_count[service] = self.failure_count.get(service, 0) + 1
        self.last_failure[service] = time.time()

    def record_success(self, service: str) -> None:
        self.failure_count[service] = 0


class WorldStateMonitor:
    _circuit_breaker = CircuitBreaker()

    @staticmethod
    async def _check_with_retry(name: str, url: str, expected_status: int = 200, max_retries: int = 2) -> bool:
        """Health check với retry + circuit breaker."""
        for attempt in range(max_retries):
            if not WorldStateMonitor._circuit_breaker.allow_request(name):
                return False
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    res = await client.get(url)
                    if res.status_code == expected_status:
                        WorldStateMonitor._circuit_breaker.record_success(name)
                        return True
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                continue
        WorldStateMonitor._circuit_breaker.record_failure(name)
        return False

    @staticmethod
    async def get_hardware_telemetry() -> HardwareTelemetry:
        """Lấy telemetry phần cứng. Fallback sang gọi trực tiếp Host Bridge nếu cache quá 5s."""
        # 1. Đọc thử từ Redis cache
        try:
            r = engine._get_redis()
            if r:
                cache = r.get("hardware_pulse_cache")
                if cache:
                    data = json.loads(cache)
                    ts = float(data.get("ts") or data.get("timestamp") or 0)
                    # Staleness check: Nếu cache mới hơn TTL cấu hình, trả về ngay
                    ttl = getattr(settings, "OS_STALE_CACHE_TTL", 5.0)
                    if time.time() - ts <= ttl:
                        return HardwareTelemetry(
                            cpu_percent=int(data.get("cpu", 0)),
                            ram_percent=int(data.get("ram", 0)),
                            gpu_percent=int(data.get("gpu", 0)),
                            timestamp=ts
                        )
        except Exception:
            pass

        # 2. Fallback: Truy vấn API trực tiếp từ Host Bridge (nếu cache bị quá hạn hoặc mất kết nối Redis)
        if WorldStateMonitor._circuit_breaker.allow_request("host_bridge"):
            try:
                token = os.getenv("AKAI_SECURE_TOKEN", "AKAI_DEVEL_SECRET_2025")
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.get(
                        "http://host.docker.internal:9997/telemetry",
                        headers={"X-AKAI-TOKEN": token}
                    )
                    if res.status_code == 200:
                        data = res.json()
                        WorldStateMonitor._circuit_breaker.record_success("host_bridge")
                        return HardwareTelemetry(
                            cpu_percent=int(round(float(data.get("cpu", 0)))),
                            ram_percent=int(round(float(data.get("ram", 0)))),
                            gpu_percent=int(round(float(data.get("gpu", 0)))),
                            timestamp=time.time()
                        )
            except Exception:
                WorldStateMonitor._circuit_breaker.record_failure("host_bridge")

        return HardwareTelemetry(timestamp=time.time())

    @staticmethod
    async def get_workspace_state(workspace_path: str = "/workspace") -> WorkspaceState:
        """Phân tích trạng thái thư mục làm việc bằng asyncio subprocess (không blocking)."""
        state = WorkspaceState(path=workspace_path)
        if not os.path.exists(workspace_path):
            return state

        try:
            # 1. Lấy tên nhánh hiện tại
            proc_branch = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--abbrev-ref", "HEAD",
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc_branch.communicate(), timeout=2.0)
            if proc_branch.returncode == 0:
                state.active_branch = stdout.decode().strip()

            # 2. Lấy danh sách file bị sửa đổi
            proc_status = await asyncio.create_subprocess_exec(
                "git", "status", "--porcelain",
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc_status.communicate(), timeout=2.0)
            if proc_status.returncode == 0:
                lines = stdout.decode().strip().split("\n")
                modified = []
                for line in lines:
                    if line.strip():
                        filepath = line.strip().split(maxsplit=1)[-1]
                        modified.append(filepath)
                state.modified_files = modified
                state.is_dirty = len(modified) > 0
        except Exception:
            pass
        return state

    @staticmethod
    async def check_infrastructure_health() -> Dict[str, str]:
        """Kiểm tra sức khỏe hạ tầng (Redis, Qdrant, Ollama) một cách song song."""
        health = {"redis": "offline", "qdrant": "offline", "ollama": "offline"}

        async def check_redis():
            try:
                r = engine._get_redis()
                if r and r.ping():
                    health["redis"] = "online"
            except Exception:
                pass

        async def check_qdrant():
            qdrant_url = getattr(settings, "RAG_API_URL", "http://qdrant:6333").rstrip("/")
            if await WorldStateMonitor._check_with_retry("qdrant", f"{qdrant_url}/healthz"):
                health["qdrant"] = "online"

        async def check_ollama():
            ollama_url = getattr(settings, "OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/")
            if await WorldStateMonitor._check_with_retry("ollama", f"{ollama_url}/"):
                health["ollama"] = "online"

        await asyncio.gather(check_redis(), check_qdrant(), check_ollama())
        return health

    @classmethod
    async def capture_state(cls, workspace_path: str = "/workspace") -> WorldState:
        """Thu thập toàn bộ trạng thái thế giới đồng thời, bất đồng bộ hoàn toàn."""
        # Chạy song song thu thập telemetry phần cứng, workspace và sức khỏe hạ tầng
        hw_task = cls.get_hardware_telemetry()
        ws_task = cls.get_workspace_state(workspace_path)
        health_task = cls.check_infrastructure_health()

        hw, ws, health = await asyncio.gather(hw_task, ws_task, health_task)

        # Lấy danh sách kỹ năng (dùng asyncio.to_thread để không block)
        tools = []
        try:
            from core.utils.skill_deck_index import SkillDeckIndex

            def _load_deck():
                deck = SkillDeckIndex.get()
                deck.ensure_loaded()
                return list(deck._by_deck.keys())

            tools = await asyncio.to_thread(_load_deck)
        except Exception:
            pass

        return WorldState(
            hardware=hw,
            workspace=ws,
            available_tools=tools,
            infrastructure_health=health,
            timestamp=time.time()
        )
