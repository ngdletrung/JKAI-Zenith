# -*- coding: utf-8 -*-
"""
Unit test suite cho ResourceGovernor v2.0 (Zero-Config Adaptive Resource Governor)
"""

import pytest
from core.governor.resource_governor import ResourceGovernor, BackendAllocation
from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelMemoryProfile, ModelClass
)
from core.governor.hardware_monitor import HardwareState


class TestResourceGovernorV2:
    """Kiểm tra các tính năng nâng cao của ResourceGovernor v2.0."""

    @pytest.fixture
    def sample_profile(self):
        mem = ModelMemoryProfile(
            weight_file_size_gb=4.0,  # ~4096MB
            quantization="Q4_K_M",
            bytes_per_param=0.5,
            total_parameters_b=4.0,
            active_parameters_b=4.0,
            num_layers=32,
        )
        return ModelCapabilityProfile(
            model_name="test-model:4b",
            model_classes={ModelClass.GENERAL},
            memory=mem,
        )

    @pytest.fixture
    def sample_hardware(self):
        return HardwareState(
            vram_total_mb=8192,
            vram_free_mb=6000,
            ram_total_gb=64.0,
            ram_free_gb=48.0,
            gpu_load_pct=0.10,
        )

    def test_allocate_latency_vs_memory_efficient(self, sample_profile, sample_hardware):
        # 1. Latency mode (mặc định: dùng tối đa VRAM)
        alloc_lat = ResourceGovernor.allocate(
            capability=sample_profile,
            hw=sample_hardware,
            objective="latency"
        )

        # 2. Memory efficient mode (giữ lại VRAM dự phòng)
        alloc_eff = ResourceGovernor.allocate(
            capability=sample_profile,
            hw=sample_hardware,
            objective="memory_efficient"
        )

        assert alloc_lat.num_gpu_layers > alloc_eff.num_gpu_layers

    def test_allocate_with_gpu_utilization_throttling(self, sample_profile, sample_hardware):
        # Bình thường: GPU idle
        alloc_normal = ResourceGovernor.allocate(
            capability=sample_profile,
            hw=sample_hardware
        )

        # Khi GPU đang bị chiếm 90%
        busy_hw = HardwareState(
            vram_total_mb=8192,
            vram_free_mb=6000,
            ram_total_gb=64.0,
            ram_free_gb=48.0,
            gpu_load_pct=0.90,
        )

        alloc_throttled = ResourceGovernor.allocate(
            capability=sample_profile,
            hw=busy_hw
        )

        assert alloc_throttled.num_gpu_layers < alloc_normal.num_gpu_layers

    def test_allocate_recommendations_on_inviable(self, sample_profile):
        # Giả lập máy cạn kiệt RAM
        tiny_hw = HardwareState(
            vram_total_mb=1024,
            vram_free_mb=200,
            ram_total_gb=2.0,
            ram_free_gb=0.5,
            gpu_load_pct=0.0,
        )

        alloc = ResourceGovernor.allocate(
            capability=sample_profile,
            hw=tiny_hw
        )

        assert alloc.is_viable is False
        assert len(alloc.recommendations) > 0
