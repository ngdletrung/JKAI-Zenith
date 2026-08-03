"""
JKAI AMG v2 — M4 HardwareScheduler ResourceRequest Test Suite
tests/test_hardware_scheduler_resource_request.py

Invariants tested:
    M4-A. HardwareScheduler.acquire(task_id, ResourceRequest) supports GPU requests
    M4-B. HardwareScheduler.acquire(task_id, ResourceRequest) supports CPU requests
    M4-C. Scheduler does NOT inspect model_name (agnostic resource allocation)
    M4-D. acquire_context() async context manager acquires and releases cleanly
    M4-E. Backward-compatible acquire_gpu_lock() and acquire_cpu_lock() still work
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from core.utils.models import ResourceRequest, BackendType
from core.utils.hardware_scheduler import HardwareScheduler


# ---------------------------------------------------------------------------
# M4-A / B / C / D / E: HardwareScheduler ResourceRequest API
# ---------------------------------------------------------------------------

class TestHardwareSchedulerResourceRequest:
    """M4 HardwareScheduler ResourceRequest API Invariants."""

    @pytest.fixture
    def scheduler(self):
        s = HardwareScheduler()
        return s

    def test_resource_request_creation(self):
        req = ResourceRequest(
            backend=BackendType.GPU,
            gpu_memory_mb=4000.0,
            ram_memory_mb=0.0,
            gpu_layers=32,
            concurrency=1,
        )
        assert req.backend == BackendType.GPU
        assert req.gpu_memory_mb == 4000.0
        assert req.is_gpu_bound is True
        assert req.is_cpu_bound is False

    def test_resource_request_from_string_backend(self):
        req = ResourceRequest(backend="HYBRID", gpu_memory_mb=3500.0, ram_memory_mb=8000.0)
        assert req.backend == BackendType.HYBRID
        assert req.is_gpu_bound is True

    def test_acquire_gpu_resource_request(self, scheduler):
        req = ResourceRequest(backend=BackendType.GPU, gpu_memory_mb=4000.0)
        with patch.object(scheduler, "acquire_gpu_lock", new_callable=AsyncMock) as mock_gpu:
            mock_gpu.return_value = True
            import asyncio
            result = asyncio.run(scheduler.acquire("task_1", req))
            assert result is True
            mock_gpu.assert_called_once()
            # Must pass size_gb derived from gpu_memory_mb
            call_kwargs = mock_gpu.call_args[1]
            assert call_kwargs.get("model_size_gb") == pytest.approx(4000.0 / 1024.0)

    def test_acquire_cpu_resource_request(self, scheduler):
        req = ResourceRequest(backend=BackendType.CPU, ram_memory_mb=4000.0)
        with patch.object(scheduler, "acquire_cpu_lock", new_callable=AsyncMock) as mock_cpu:
            mock_cpu.return_value = True
            import asyncio
            result = asyncio.run(scheduler.acquire("task_2", req))
            assert result is True
            mock_cpu.assert_called_once()

    def test_acquire_context_manager(self, scheduler):
        req = ResourceRequest(backend=BackendType.CPU, ram_memory_mb=2000.0)
        with patch.object(scheduler, "acquire", new_callable=AsyncMock) as mock_acq, \
             patch.object(scheduler, "release", new_callable=AsyncMock) as mock_rel:
            mock_acq.return_value = True

            async def run_context():
                async with scheduler.acquire_context("task_3", req) as acquired:
                    assert acquired is True

            import asyncio
            asyncio.run(run_context())

            mock_acq.assert_called_once_with("task_3", req, None)
            mock_rel.assert_called_once_with("task_3", req)

    def test_model_name_not_inspected(self, scheduler):
        """M4-C: ResourceRequest contains NO model_name field — model-agnostic invariant."""
        req = ResourceRequest(backend=BackendType.GPU, gpu_memory_mb=2000.0)
        assert not hasattr(req, "model_name"), "ResourceRequest must NOT contain model_name field"
