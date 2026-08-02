"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — RESOURCE GOVERNOR
File: core/governor/resource_governor.py

Purpose:
    Computes precise GPU layer allocation and backend routing based on
    actual hardware state and model memory profile.

    VRAM Budget Stack (Lock-in Point #1):
        VRAM_FREE
        - RUNTIME_RESERVE      (Vulkan/ROCm driver overhead)
        - KV_CACHE             (proportional to context length)
        - COMPUTE_BUFFERS      (intermediate activation buffers)
        - SAFETY_MARGIN        (fragmentation + misc)
        ─────────────────
        = USABLE_VRAM
        ÷ per_layer_mb
        = safe_gpu_layers

    Backend vs Memory Layout (Lock-in Point #5):
        backend       = COMPUTE path (GPU | HYBRID | CPU)
        memory_layout = where weights live (VRAM_ONLY | VRAM_RAM_SPLIT | RAM_ONLY)
        These are SEPARATE concerns — a HYBRID backend = VRAM_RAM_SPLIT memory.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Tuple

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelMemoryProfile,
)
from core.governor.hardware_monitor import HardwareState

logger = logging.getLogger("AMG_ResourceGovernor")


# ---------------------------------------------------------------------------
# VRAM overhead constants (AMD RX 6600 / Vulkan tuned)
# ---------------------------------------------------------------------------
RUNTIME_RESERVE_MB: int   = 512   # Vulkan driver + display compositor overhead
COMPUTE_BUFFERS_MB: int   = 256   # Intermediate activation buffers per inference
SAFETY_MARGIN_MB: int     = 256   # Fragmentation + misc allocator waste
# KV cache is dynamic — calculated per call based on context_len


@dataclass
class BackendAllocation:
    """
    Fully computed hardware allocation for a model execution.
    Produced by ResourceGovernor, consumed by PortfolioGovernor + ExecutionPolicy.
    """
    # Compute backend
    backend: str             # "GPU" | "HYBRID" | "CPU"

    # Memory layout (separate concept from compute backend)
    memory_layout: str       # "VRAM_ONLY" | "VRAM_RAM_SPLIT" | "RAM_ONLY"

    # Layer allocation
    num_gpu_layers: int      # Layers offloaded to GPU VRAM
    num_cpu_layers: int      # Remaining layers in RAM

    # Estimated memory breakdown (MB)
    gpu_resident_mb: float   # Weights on GPU
    ram_resident_mb: float   # Weights on RAM
    kv_cache_mb: float       # KV cache on GPU

    # Whether allocation is viable given current hardware
    is_viable: bool
    reason: str              # Human-readable explanation

    def log_summary(self) -> str:
        return (
            f"Backend={self.backend} | Layout={self.memory_layout} | "
            f"GPU_layers={self.num_gpu_layers} | "
            f"GPU_weights={self.gpu_resident_mb:.0f}MB | "
            f"RAM_weights={self.ram_resident_mb:.0f}MB | "
            f"KV={self.kv_cache_mb:.0f}MB | "
            f"Viable={self.is_viable}"
        )


class ResourceGovernor:
    """
    Hardware-aware backend and layer allocation calculator.

    Takes a ModelCapabilityProfile + HardwareState and computes the
    optimal BackendAllocation. Does NOT touch model names or families.
    """

    @classmethod
    def allocate(
        cls,
        capability: ModelCapabilityProfile,
        hw: HardwareState,
        context_len: int = 4096,
        requested_hardware: str = "auto",
    ) -> BackendAllocation:
        """
        Compute optimal backend allocation.

        Args:
            capability:         Model capability profile (with memory profile)
            hw:                 Current hardware state (real VRAM/RAM readings)
            context_len:        Requested context length (affects KV cache)
            requested_hardware: "auto" | "gpu" | "cpu" | "hybrid"
                                If "cpu" → force CPU regardless of VRAM

        Returns:
            BackendAllocation with backend, memory_layout, layer counts, estimates.
        """
        mem = capability.memory
        if mem is None:
            # Minimal profile — use safe defaults
            return cls._safe_default(capability.model_name)

        req_hw = requested_hardware.upper().strip()

        # Force CPU if explicitly requested (e.g. EXECUTOR role in rule_hardware.md)
        if "CPU" in req_hw and "GPU" not in req_hw and req_hw != "AUTO":
            return cls._cpu_allocation(mem)

        # Calculate VRAM budget stack
        kv_cache_mb = mem.kv_cache_for_context(context_len)
        usable_vram_mb = cls._compute_usable_vram(hw.vram_safe_budget_mb, kv_cache_mb)

        total_weight_mb = mem.weight_file_size_gb * 1024.0
        per_layer_mb    = total_weight_mb / max(mem.num_layers, 1)

        # RAM viability check
        ram_needed_gb = total_weight_mb / 1024.0
        ram_viable = hw.ram_safe_budget_gb >= ram_needed_gb

        # Determine how many layers fit in usable VRAM
        if usable_vram_mb <= 0 or per_layer_mb <= 0:
            safe_gpu_layers = 0
        else:
            import math
            safe_gpu_layers = min(mem.num_layers, math.floor(usable_vram_mb / per_layer_mb))

        gpu_resident_mb = safe_gpu_layers * per_layer_mb
        ram_resident_mb = max(0.0, total_weight_mb - gpu_resident_mb)

        # Update memory profile estimates in-place (for observability)
        mem.estimated_gpu_resident_mb = round(gpu_resident_mb, 0)
        mem.estimated_ram_resident_mb = round(ram_resident_mb, 0)

        # --- Backend decision ---
        if safe_gpu_layers >= mem.num_layers:
            # Entire model fits in VRAM
            return BackendAllocation(
                backend="GPU",
                memory_layout="VRAM_ONLY",
                num_gpu_layers=mem.num_layers,
                num_cpu_layers=0,
                gpu_resident_mb=gpu_resident_mb,
                ram_resident_mb=0.0,
                kv_cache_mb=kv_cache_mb,
                is_viable=True,
                reason="Model fits entirely in VRAM budget",
            )

        elif safe_gpu_layers > 0 and ram_viable:
            # Partial VRAM + RAM split
            return BackendAllocation(
                backend="HYBRID",
                memory_layout="VRAM_RAM_SPLIT",
                num_gpu_layers=safe_gpu_layers,
                num_cpu_layers=mem.num_layers - safe_gpu_layers,
                gpu_resident_mb=gpu_resident_mb,
                ram_resident_mb=ram_resident_mb,
                kv_cache_mb=kv_cache_mb,
                is_viable=True,
                reason=(
                    f"{safe_gpu_layers}/{mem.num_layers} layers in VRAM, "
                    f"remainder in {hw.ram_free_gb:.0f}GB free RAM"
                ),
            )

        elif ram_viable:
            # Not enough VRAM for even partial offload → pure CPU/RAM
            return BackendAllocation(
                backend="CPU",
                memory_layout="RAM_ONLY",
                num_gpu_layers=0,
                num_cpu_layers=mem.num_layers,
                gpu_resident_mb=0.0,
                ram_resident_mb=total_weight_mb,
                kv_cache_mb=0.0,  # KV cache stays in RAM too
                is_viable=True,
                reason=(
                    f"Insufficient VRAM ({hw.vram_free_mb}MB free). "
                    f"Routing to {hw.ram_free_gb:.0f}GB RAM."
                ),
            )

        else:
            # Neither VRAM nor RAM can hold model — not viable
            return BackendAllocation(
                backend="CPU",
                memory_layout="RAM_ONLY",
                num_gpu_layers=0,
                num_cpu_layers=mem.num_layers,
                gpu_resident_mb=0.0,
                ram_resident_mb=total_weight_mb,
                kv_cache_mb=0.0,
                is_viable=False,
                reason=(
                    f"Model requires ~{ram_needed_gb:.1f}GB RAM, "
                    f"only {hw.ram_safe_budget_gb:.1f}GB available. "
                    "Routing anyway — may cause OOM."
                ),
            )

    @classmethod
    def _compute_usable_vram(cls, vram_budget_mb: int, kv_cache_mb: float) -> float:
        """
        VRAM budget stack:
            VRAM_SAFE_BUDGET (from HardwareMonitor — already minus driver reserve)
            - KV_CACHE
            - COMPUTE_BUFFERS
            - SAFETY_MARGIN
            = USABLE_VRAM for model weights
        """
        usable = (
            vram_budget_mb
            - kv_cache_mb
            - COMPUTE_BUFFERS_MB
            - SAFETY_MARGIN_MB
        )
        logger.debug(
            f"[VRAM-BUDGET] Budget={vram_budget_mb}MB "
            f"- KV={kv_cache_mb:.0f}MB "
            f"- Compute={COMPUTE_BUFFERS_MB}MB "
            f"- Safety={SAFETY_MARGIN_MB}MB "
            f"= Usable={usable:.0f}MB"
        )
        return max(0.0, usable)

    @classmethod
    def _cpu_allocation(cls, mem: ModelMemoryProfile) -> BackendAllocation:
        return BackendAllocation(
            backend="CPU",
            memory_layout="RAM_ONLY",
            num_gpu_layers=0,
            num_cpu_layers=mem.num_layers,
            gpu_resident_mb=0.0,
            ram_resident_mb=mem.weight_file_size_gb * 1024.0,
            kv_cache_mb=0.0,
            is_viable=True,
            reason="Forced CPU/RAM by role configuration",
        )

    @classmethod
    def _safe_default(cls, model_name: str) -> BackendAllocation:
        """Conservative default when memory profile is unavailable."""
        logger.warning(f"[RESOURCE-GOV] No memory profile for '{model_name}' — using safe default")
        return BackendAllocation(
            backend="CPU",
            memory_layout="RAM_ONLY",
            num_gpu_layers=0,
            num_cpu_layers=32,
            gpu_resident_mb=0.0,
            ram_resident_mb=4096.0,
            kv_cache_mb=0.0,
            is_viable=True,
            reason="No memory profile — conservative CPU fallback",
        )
