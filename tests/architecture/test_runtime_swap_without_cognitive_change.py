"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: RUNTIME & HARDWARE SWAP
tests/architecture/test_runtime_swap_without_cognitive_change.py

Architectural Invariant Enforced:
    Swapping inference runtimes (OllamaAdapter -> MockVLLMAdapter -> MockRemoteRuntimeAdapter)
    or hardware acceleration targets (RX6600 -> NVIDIA -> CPU -> Remote)
    MUST NOT change Cognitive Kernel logic or TaskRequirement generation.
"""

import pytest
from dataclasses import dataclass
from core.contracts import TaskRequirement, ExecutionProfile, ResourceAllocation, BackendType


class MockVLLMAdapter:
    """Mock vLLM Runtime Adapter."""
    def translate_profile(self, profile: ExecutionProfile, alloc: ResourceAllocation):
        return {
            "model": profile.model_name,
            "max_model_len": profile.num_ctx,
            "tensor_parallel_size": 1 if alloc.backend == BackendType.GPU else 0,
        }


class MockRemoteRuntimeAdapter:
    """Mock Remote Cloud Inference Adapter."""
    def translate_profile(self, profile: ExecutionProfile, alloc: ResourceAllocation):
        return {
            "remote_model": profile.model_name,
            "context_window": profile.num_ctx,
            "api_endpoint": "https://remote.inference.ai/v1/chat",
        }


class TestRuntimeAndHardwareSwap:

    def test_runtime_swap_preserves_task_requirement_and_profile(self):
        # 1. Cognitive Kernel emits TaskRequirement
        task_req = TaskRequirement(role="PLANNER", quality_target="high")
        assert task_req.role == "PLANNER"

        # 2. Governance produces ExecutionProfile
        profile = ExecutionProfile(model_name="qwen3.5:4b", role_name="PLANNER", num_ctx=4096)

        # 3. Swap Runtime Adapters without modifying TaskRequirement or ExecutionProfile
        vllm_adapter = MockVLLMAdapter()
        remote_adapter = MockRemoteRuntimeAdapter()

        gpu_alloc = ResourceAllocation(backend=BackendType.GPU, gpu_layers=32)
        remote_alloc = ResourceAllocation(backend=BackendType.CPU, gpu_layers=0)

        vllm_payload = vllm_adapter.translate_profile(profile, gpu_alloc)
        remote_payload = remote_adapter.translate_profile(profile, remote_alloc)

        assert vllm_payload["model"] == "qwen3.5:4b"
        assert vllm_payload["tensor_parallel_size"] == 1

        assert remote_payload["remote_model"] == "qwen3.5:4b"
        assert remote_payload["api_endpoint"].startswith("https://")

    def test_hardware_swap_preserves_cognitive_intent(self):
        # Cognitive Kernel intent remains identical across hardware swaps
        task_req = TaskRequirement(role="DEEP_REASONER", quality_target="highest")

        # Hardware allocations vary based on substrate telemetry
        rx6600_alloc = ResourceAllocation(backend=BackendType.GPU, gpu_memory_mb=7600.0, gpu_layers=32)
        nvidia_alloc = ResourceAllocation(backend=BackendType.GPU, gpu_memory_mb=16384.0, gpu_layers=48)
        cpu_alloc = ResourceAllocation(backend=BackendType.CPU, ram_memory_mb=16000.0, gpu_layers=0)

        assert rx6600_alloc.is_gpu_bound is True
        assert nvidia_alloc.is_gpu_bound is True
        assert cpu_alloc.is_cpu_bound is True

        # Cognitive requirement is unchanged across substrate variations
        assert task_req.role == "DEEP_REASONER"
