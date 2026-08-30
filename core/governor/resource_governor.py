# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ADAPTIVE MODEL GOVERNOR: RESOURCE GOVERNOR v2.0  ║
║   Tự Động Tính Toán Ngân Sách GPU/RAM Thích Ứng (Zero-Config)   ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Phân Bổ Tài Nguyên Đa Mục Tiêu. 🏛️⚡🧠*
"""

from __future__ import annotations
import time
import math
import logging
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelMemoryProfile,
)
from core.governor.hardware_monitor import HardwareState

logger = logging.getLogger("AMG_ResourceGovernor")


@dataclass
class BackendAllocation:
    """
    Phân bổ phần cứng hoàn chỉnh cho quá trình thực thi mô hình.
    """
    # Compute backend
    backend: str             # "GPU" | "HYBRID" | "CPU"

    # Memory layout
    memory_layout: str       # "VRAM_ONLY" | "VRAM_RAM_SPLIT" | "RAM_ONLY"

    # Layer allocation
    num_gpu_layers: int      # Layers offloaded to GPU VRAM
    num_cpu_layers: int      # Remaining layers in RAM

    # Estimated memory breakdown (MB)
    gpu_resident_mb: float   # Weights on GPU
    ram_resident_mb: float   # Weights on RAM
    kv_cache_mb: float       # KV cache on GPU

    # Trạng thái khả thi
    is_viable: bool
    reason: str              # Giải thích lý do
    recommendations: List[str] = field(default_factory=list)

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
    🏛️ Bộ Điều Phối Tài Nguyên Tự Động Thích Ứng (Zero-Config Adaptive Resource Governor):
    Tự động suy luận ngân sách VRAM theo tỷ lệ % phần cứng thực tế, hỗ trợ đa mục tiêu (latency, balanced, memory_efficient).
    """

    @classmethod
    def allocate(
        cls,
        capability: ModelCapabilityProfile,
        hw: HardwareState,
        context_len: int = 4096,
        requested_hardware: str = "auto",
        objective: str = "latency",  # "latency" | "balanced" | "memory_efficient"
    ) -> BackendAllocation:
        """
        Tính toán phân bổ phần cứng tối ưu theo mục tiêu và tải thực tế.
        """
        t0 = time.perf_counter()
        mem = capability.memory
        if mem is None:
            return cls._safe_default(capability.model_name)

        req_hw = requested_hardware.upper().strip()

        # 1. Ép CPU nếu được chỉ định
        if "CPU" in req_hw and "GPU" not in req_hw and req_hw != "AUTO":
            alloc = cls._cpu_allocation(mem)
            cls._record_metric(alloc, (time.perf_counter() - t0) * 1000)
            return alloc

        # 2. Tự động tính dynamic buffers theo tỷ lệ VRAM thực tế (Zero-Config)
        compute_buffers_mb = max(256, int(hw.vram_total_mb * 0.03))  # 3% VRAM
        safety_margin_mb = max(256, int(hw.vram_total_mb * 0.03))    # 3% VRAM

        # 3. Tính toán VRAM budget
        kv_cache_mb = mem.kv_cache_for_context(context_len)
        usable_vram_mb = max(0.0, hw.vram_safe_budget_mb - kv_cache_mb - compute_buffers_mb - safety_margin_mb)

        # 4. Điều chỉnh theo chiến lược mục tiêu (Objective Scaling)
        if objective == "memory_efficient":
            usable_vram_mb *= 0.40  # Giữ lại 60% VRAM dự phòng
        elif objective == "balanced":
            usable_vram_mb *= 0.70  # Giữ lại 30% VRAM dự phòng

        # 5. Điều chỉnh theo tải thực tế GPU (gpu_load_pct)
        if hw.gpu_load_pct >= 0.85:
            usable_vram_mb *= 0.50  # Hạ tải GPU khi đang bận
            logger.info(f"[RESOURCE-GOV]: GPU load high ({hw.gpu_load_pct*100:.0f}%). Throttling VRAM allocation.")

        total_weight_mb = mem.weight_file_size_gb * 1024.0
        per_layer_mb = total_weight_mb / max(mem.num_layers, 1)

        # Kiểm tra tính khả thi của RAM
        ram_needed_gb = total_weight_mb / 1024.0
        ram_viable = hw.ram_safe_budget_gb >= ram_needed_gb

        # Tính toán số layers offload an toàn
        if usable_vram_mb <= 0 or per_layer_mb <= 0:
            safe_gpu_layers = 0
        else:
            safe_gpu_layers = min(mem.num_layers, math.floor(usable_vram_mb / per_layer_mb))

        gpu_resident_mb = safe_gpu_layers * per_layer_mb
        ram_resident_mb = max(0.0, total_weight_mb - gpu_resident_mb)

        mem.estimated_gpu_resident_mb = round(gpu_resident_mb, 0)
        mem.estimated_ram_resident_mb = round(ram_resident_mb, 0)

        # --- Quyết định Phân bổ Backend ---
        if safe_gpu_layers >= mem.num_layers:
            alloc = BackendAllocation(
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
            alloc = BackendAllocation(
                backend="HYBRID",
                memory_layout="VRAM_RAM_SPLIT",
                num_gpu_layers=safe_gpu_layers,
                num_cpu_layers=mem.num_layers - safe_gpu_layers,
                gpu_resident_mb=gpu_resident_mb,
                ram_resident_mb=ram_resident_mb,
                kv_cache_mb=kv_cache_mb,
                is_viable=True,
                reason=f"{safe_gpu_layers}/{mem.num_layers} layers in VRAM, remainder in {hw.ram_free_gb:.0f}GB free RAM",
            )
        elif ram_viable:
            alloc = BackendAllocation(
                backend="CPU",
                memory_layout="RAM_ONLY",
                num_gpu_layers=0,
                num_cpu_layers=mem.num_layers,
                gpu_resident_mb=0.0,
                ram_resident_mb=total_weight_mb,
                kv_cache_mb=0.0,
                is_viable=True,
                reason=f"Insufficient VRAM ({hw.vram_free_mb}MB free). Routing to {hw.ram_free_gb:.0f}GB RAM.",
            )
        else:
            recs = [
                f"Giảm context_len xuống < {context_len // 2} tokens.",
                f"Nâng cấp thêm RAM vật lý (hiện có {hw.ram_free_gb:.1f}GB / cần {ram_needed_gb:.1f}GB).",
                "Chuyển sang mô hình có số lượng tham số nhỏ hơn qua ModelFallback."
            ]
            alloc = BackendAllocation(
                backend="CPU",
                memory_layout="RAM_ONLY",
                num_gpu_layers=0,
                num_cpu_layers=mem.num_layers,
                gpu_resident_mb=0.0,
                ram_resident_mb=total_weight_mb,
                kv_cache_mb=0.0,
                is_viable=False,
                reason=f"Model requires ~{ram_needed_gb:.1f}GB RAM, only {hw.ram_safe_budget_gb:.1f}GB available.",
                recommendations=recs
            )

        cls._record_metric(alloc, (time.perf_counter() - t0) * 1000)
        return alloc

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

    @classmethod
    def _record_metric(cls, alloc: BackendAllocation, duration_ms: float) -> None:
        try:
            from core.telemetry.observability_engine import observability_engine
            observability_engine.record_span(
                name="amg_resource_allocation",
                category="AMG",
                duration_ms=duration_ms,
                metadata={
                    "backend": alloc.backend,
                    "memory_layout": alloc.memory_layout,
                    "viable": alloc.is_viable,
                    "gpu_layers": alloc.num_gpu_layers
                }
            )
        except Exception:
            pass


resource_governor = ResourceGovernor()
