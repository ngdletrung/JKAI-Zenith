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
    vram_total_mb: int = 8192            # AMD RX 6600 default
    vram_free_mb: int = 5500             # Estimated usable (after driver reserve)
    gpu_load_pct: float = 0.0            # 0.0–1.0

    # System RAM
    ram_total_gb: float = 128.0
    ram_free_gb: float = 80.0
    ram_load_pct: float = 0.0

    # Staleness
    snapshot_ts: float = 0.0             # Unix timestamp of this snapshot
    is_stale: bool = False               # True if > CACHE_TTL_SEC seconds old

    CACHE_TTL_SEC: float = 3.0           # Refresh state every 3 seconds

    @property
    def vram_safe_budget_mb(self) -> int:
        """
        Conservative usable VRAM: leave 512MB headroom for OS / display.
        On AMD Vulkan, this prevents OOM crashes.
        """
        return max(0, self.vram_free_mb - 512)

    @property
    def ram_safe_budget_gb(self) -> float:
        """Conservative usable RAM: leave 8GB for OS processes."""
        return max(0.0, self.ram_free_gb - 8.0)


class HardwareMonitor:
    """
    Thread-safe hardware resource monitor.
    Caches the last reading and refreshes every CACHE_TTL_SEC seconds.

    Usage:
        state = HardwareMonitor.get_state()
        if state.vram_safe_budget_mb > model.estimated_gpu_resident_mb:
            backend = "GPU"
    """

    _lock = threading.Lock()
    _last_state: HardwareState = HardwareState(snapshot_ts=0.0)
    CACHE_TTL_SEC = 3.0

    # Static hardware constants (updated from environment at class load)
    TOTAL_VRAM_MB: int = int(os.getenv("TOTAL_VRAM_MB", "8192"))
    RESERVED_VRAM_MB: int = int(os.getenv("RESERVED_VRAM_MB", "2560"))  # 2.5GB Vulkan reserve
    TOTAL_RAM_GB: float = float(os.getenv("TOTAL_RAM_GB", "128"))

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
        Reads actual hardware metrics.
        Falls back to conservative estimates if monitoring unavailable.
        """
        state = HardwareState(
            vram_total_mb=cls.TOTAL_VRAM_MB,
            ram_total_gb=cls.TOTAL_RAM_GB,
            snapshot_ts=time.monotonic(),
        )

        # --- RAM via psutil (available in container) ---
        try:
            import psutil
            vm = psutil.virtual_memory()
            state.ram_free_gb = round(vm.available / (1024 ** 3), 1)
            state.ram_load_pct = vm.percent / 100.0
        except ImportError:
            # Fallback: assume 60% RAM free
            state.ram_free_gb = cls.TOTAL_RAM_GB * 0.6
            state.ram_load_pct = 0.4

        # --- VRAM via AMD ROCm sysfs (Linux only) ---
        vram_free_mb = cls._read_amd_vram_free_mb()
        if vram_free_mb is not None:
            state.vram_free_mb = vram_free_mb
        else:
            # Fallback: assume (total - reserved) VRAM available
            state.vram_free_mb = cls.TOTAL_VRAM_MB - cls.RESERVED_VRAM_MB

        logger.debug(
            f"[HW-MONITOR] VRAM={state.vram_free_mb}MB free | "
            f"RAM={state.ram_free_gb:.1f}GB free | "
            f"RAM load={state.ram_load_pct*100:.0f}%"
        )
        return state

    @classmethod
    def _read_amd_vram_free_mb(cls) -> int | None:
        """
        Reads free VRAM from AMD ROCm sysfs.
        Returns None if unavailable (Windows, no ROCm, etc.).
        """
        # AMD sysfs path: /sys/class/drm/card0/device/mem_info_vram_used
        # May vary by driver version and card index.
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
        return None  # Monitoring unavailable — caller uses fallback
