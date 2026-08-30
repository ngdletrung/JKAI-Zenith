"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — HARDWARE MONITOR
File: core/governor/hardware_monitor.py

Purpose:
    Provides real-time HardwareState (VRAM free, RAM free, load) to
    PortfolioGovernor so that pool/backend decisions are based on
    actual runtime resource availability, not static estimates.

    This is what makes the 'A' (Adaptive) in AMG real:
        Same model + 6GB VRAM free → GPU
        Same model + 2GB VRAM free → HYBRID
        Same model + 1GB VRAM free → CPU
"""

from __future__ import annotations
import logging
import os
import time
import threading
from dataclasses import dataclass

logger = logging.getLogger("AMG_HardwareMonitor")


@dataclass
class HardwareState:
    """
    Snapshot of available hardware resources at a point in time.
    Consumed by ResourceGovernor and PortfolioGovernor.
    """
    # GPU
    gpu_name: str = "AMD Radeon RX 6600"
    vram_total_mb: int = 8192            # AMD RX 6600 default (8GB)
    vram_free_mb: int = 2800             # Estimated usable
    vram_used_mb: int = 5300             # Estimated used
    gpu_load_pct: float = 0.0            # 0.0–1.0

    # System CPU & RAM
    cpu_count_logical: int = 44          # Intel Xeon E5-2699 v4 (44 Threads)
    cpu_count_physical: int = 22
    cpu_load_pct: float = 0.10           # 0.0–1.0
    ram_total_gb: float = 64.0
    ram_free_gb: float = 32.0
    ram_load_pct: float = 0.50

    # Staleness
    snapshot_ts: float = 0.0             # Unix timestamp of this snapshot
    is_stale: bool = False               # True if > CACHE_TTL_SEC seconds old

    CACHE_TTL_SEC: float = 3.0           # Refresh state every 3 seconds

    @property
    def vram_safe_budget_mb(self) -> int:
        """
        Dynamic VRAM Headroom:
        Thay vì trừ hao cứng 1024MB gây lãng phí VRAM, hệ thống tính toán động:
        - Đảm bảo tối thiểu 512MB cho Windows DWM / màn hình.
        - Cho phép AI tận dụng tới ~7.5GB / 8GB VRAM (tối đa 94% công suất card AMD RX 6600).
        """
        # Nếu đã có đo lường VRAM thực tế, để dành đệm tối thiểu 512MB hoặc 8% VRAM tổng
        min_reserve = max(512, int(self.vram_total_mb * 0.08))
        return max(0, self.vram_free_mb - min_reserve)

    @property
    def ram_safe_budget_gb(self) -> float:
        """Conservative usable RAM: leave 6GB for OS and Core Docker processes."""
        return max(0.0, self.ram_free_gb - 6.0)

    def get_dynamic_ai_threads(self, base_threads: int = 22) -> int:
        """
        Exact Mathematical CPU Allocator (Xeon E5-2699 v4):
        Tận dụng tối đa công suất của 22 Physical Cores mà không gây nghẽn 100% CPU.
        - Tính chính xác số luồng rảnh theo tải thực tế của máy: available = 44 * (1 - load) - 4
        - Chừa cứng 4 luồng (~10% CPU) cho Windows OS / Docker background.
        - Giới hạn trần tối ưu = 22 threads (bằng đúng số Physical Cores để đạt token/s cao nhất).
        - Giới hạn sàn tối thiểu = 4 threads khi hệ thống chịu tải rất cao.
        """
        available_threads = int(self.cpu_count_logical * (1.0 - self.cpu_load_pct) - 4)
        max_physical = self.cpu_count_physical if self.cpu_count_physical > 0 else 22
        target_limit = min(base_threads, max_physical)
        return max(4, min(target_limit, available_threads))


class HardwareMonitor:
    """
    Thread-safe hardware resource monitor.
    Caches the last reading and refreshes every CACHE_TTL_SEC seconds.
    Supports dynamic AMD Radeon detection on Windows (Vulkan Native).
    """

    _lock = threading.Lock()
    _last_state: HardwareState = HardwareState(snapshot_ts=0.0)
    CACHE_TTL_SEC = 3.0

    # Static hardware constants (updated dynamically from environment or sensors)
    TOTAL_VRAM_MB: int = int(os.getenv("TOTAL_VRAM_MB", "8192"))
    RESERVED_VRAM_MB: int = int(os.getenv("RESERVED_VRAM_MB", "1024"))  # 1GB Windows DWM reserve
    TOTAL_RAM_GB: float = float(os.getenv("TOTAL_RAM_GB", "64"))

    @classmethod
    def get_state(cls) -> HardwareState:
        """
        Returns current hardware state. Uses cached value if fresh enough.
        Thread-safe — safe to call from async contexts.
        """
        with cls._lock:
            now = time.monotonic()
            age = now - cls._last_state.snapshot_ts
            if age < cls.CACHE_TTL_SEC and cls._last_state.snapshot_ts > 0:
                return cls._last_state

            state = cls._read_hardware()
            cls._last_state = state
            return state

    @classmethod
    def _read_hardware(cls) -> HardwareState:
        """
        Reads actual hardware metrics dynamically.
        Detects AMD GPU via Windows Performance Counters / CIM or Linux ROCm sysfs.
        """
        state = HardwareState(
            vram_total_mb=cls.TOTAL_VRAM_MB,
            ram_total_gb=cls.TOTAL_RAM_GB,
            snapshot_ts=time.monotonic(),
        )

        # --- 1. CPU & RAM via psutil (Real-time Host Metrics) ---
        try:
            import psutil
            state.cpu_count_logical = psutil.cpu_count(logical=True) or 44
            state.cpu_count_physical = psutil.cpu_count(logical=False) or 22
            state.cpu_load_pct = round(psutil.cpu_percent(interval=None) / 100.0, 2)
            
            vm = psutil.virtual_memory()
            state.ram_total_gb = round(vm.total / (1024 ** 3), 1)
            state.ram_free_gb = round(vm.available / (1024 ** 3), 1)
            state.ram_load_pct = round(vm.percent / 100.0, 2)
        except ImportError:
            state.ram_free_gb = cls.TOTAL_RAM_GB * 0.5
            state.ram_load_pct = 0.5
            state.cpu_load_pct = 0.1

        # --- 2. GPU Detection (AMD Radeon RX 6600 on Windows) ---
        vram_info = cls._read_amd_windows_vram()
        if vram_info:
            state.gpu_name = vram_info.get("name", "AMD Radeon RX 6600")
            state.vram_total_mb = vram_info.get("total_mb", cls.TOTAL_VRAM_MB)
            state.vram_used_mb = vram_info.get("used_mb", 5000)
            state.vram_free_mb = max(0, state.vram_total_mb - state.vram_used_mb)
            state.gpu_load_pct = round(state.vram_used_mb / max(1, state.vram_total_mb), 2)
        else:
            # Linux ROCm fallback
            vram_free_linux = cls._read_amd_vram_free_mb()
            if vram_free_linux is not None:
                state.vram_free_mb = vram_free_linux
                state.vram_used_mb = max(0, state.vram_total_mb - vram_free_linux)
            else:
                # Conservative fallback based on Ollama ps API
                state.vram_free_mb = max(0, cls.TOTAL_VRAM_MB - cls.RESERVED_VRAM_MB)

        logger.debug(
            f"[HW-MONITOR] GPU='{state.gpu_name}' VRAM={state.vram_free_mb}MB free / {state.vram_total_mb}MB | "
            f"CPU={state.cpu_load_pct*100:.0f}% ({state.cpu_count_logical}T) | "
            f"RAM={state.ram_free_gb:.1f}GB free / {state.ram_total_gb:.1f}GB"
        )
        return state

    @classmethod
    def _read_amd_windows_vram(cls) -> dict | None:
        """
        Queries Windows Performance Counter and Registry for AMD GPU details.
        Returns {'name': str, 'total_mb': int, 'used_mb': int} or None.
        """
        if os.name != "nt":
            return None

        try:
            import subprocess
            # Query live used VRAM via PowerShell Performance Counter
            ps_cmd = "(Get-Counter '\\GPU Process Memory(*)\\Local Usage' -ErrorAction SilentlyContinue).CounterSamples | Measure-Object -Property CookedValue -Sum | Select-Object -ExpandProperty Sum"
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=1.5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    used_bytes = float(proc.stdout.strip())
                    used_mb = int(used_bytes / (1024 * 1024))
                    return {
                        "name": "AMD Radeon RX 6600",
                        "total_mb": 8192,
                        "used_mb": used_mb
                    }
                except ValueError:
                    pass
        except Exception:
            pass
        return None

    @classmethod
    def _read_amd_vram_free_mb(cls) -> int | None:
        """
        Reads free VRAM from AMD ROCm sysfs (Linux).
        Returns None if unavailable.
        """
        sysfs_paths = [
            "/sys/class/drm/card0/device/mem_info_vram_used",
            "/sys/class/drm/card1/device/mem_info_vram_used",
        ]
        total_b = cls.TOTAL_VRAM_MB * 1024 * 1024
        for path in sysfs_paths:
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        used_b = int(f.read().strip())
                    free_mb = (total_b - used_b) // (1024 * 1024)
                    return max(0, free_mb)
            except Exception:
                continue
        return None
