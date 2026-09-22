import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from core.utils.pipeline_cache import (
    PipelineCache,
    _is_cacheable_result,
    _is_error_response,
)


@pytest.fixture
def clean_cache():
    cache = PipelineCache()
    cache._local.clear()
    cache._redis = False  # force in-memory local testing
    return cache


def test_is_error_response_detection():
    assert _is_error_response("error: connection refused") is True
    assert _is_error_response("failed to execute command") is True
    assert _is_error_response("aborted by master") is True
    assert _is_error_response("Traceback (most recent call last):\n  File 'main.py'...") is True
    assert _is_error_response("Đây là phương trình bậc 2 hoàn chỉnh") is False


def test_is_cacheable_result_validation():
    # Valid SUCCESS
    assert _is_cacheable_result({
        "status": "SUCCESS",
        "answer": "Kết quả tính phương trình bậc 2 là x1=2, x2=3",
        "judicial_review": {"verdict": "PASS", "passed": True}
    }) is True

    # Missing / empty answer
    assert _is_cacheable_result({"status": "SUCCESS", "answer": ""}) is False

    # Status FAILED
    assert _is_cacheable_result({
        "status": "FAILED",
        "answer": "Không tìm thấy kết quả",
    }) is False

    # Fallback report string
    assert _is_cacheable_result({
        "status": "SUCCESS",
        "answer": "Báo cáo Master! Chuỗi hành pháp chuyên sâu T2-T6 cho yêu cầu: giải pt đã được điều phối...",
    }) is False

    # Judicial review FAIL
    assert _is_cacheable_result({
        "status": "SUCCESS",
        "answer": "def solve(): pass",
        "judicial_review": {"verdict": "FAIL", "passed": False}
    }) is False

    # Execution steps all failed
    assert _is_cacheable_result({
        "status": "SUCCESS",
        "answer": "Xong",
        "execution": {
            "step_1": {"status": "error", "output": "SyntaxError"},
            "step_2": {"status": "failed", "output": "Not found"}
        }
    }) is False


@pytest.mark.asyncio
async def test_pipeline_cache_set_and_get(clean_cache):
    goal = "Tính tổng hai số 5 và 10"
    mode = "fast"
    valid_res = {
        "status": "SUCCESS",
        "answer": "Tổng của 5 và 10 là 15.",
        "task_id": "test_t1"
    }

    await clean_cache.set(goal, mode, valid_res)
    retrieved = await clean_cache.get(goal, mode)
    assert retrieved is not None
    assert retrieved["answer"] == "Tổng của 5 và 10 là 15."

    # Now attempt to cache a FAILED response for the same goal in another mode
    failed_res = {
        "status": "FAILED",
        "answer": "Lỗi thực thi",
        "error": "Timeout"
    }
    await clean_cache.set(goal, "deep", failed_res)
    assert await clean_cache.get(goal, "deep") is None

    # Invalidate
    await clean_cache.invalidate(goal, mode)
    assert await clean_cache.get(goal, mode) is None


@pytest.mark.asyncio
async def test_deep_pipeline_hard_timeout_fires_and_records_checkpoint():
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    dp = DeepPipeline()

    task_id = "test_timeout_mission_001"
    goal = "Chạy tác vụ siêu nặng bị treo"

    # Set timeout to 1 second for drill test
    with patch.dict(os.environ, {"MISSION_HARD_TIMEOUT_SECONDS": "1"}):
        # Mock _execute_mission_loop to simulate hanging / slow child tasks
        async def slow_mission_loop(*args, **kwargs):
            await asyncio.sleep(5)
            return {"status": "SUCCESS", "answer": "Done"}

        dp._execute_mission_loop = slow_mission_loop

        result = await dp.execute(goal=goal, task_id=task_id)

        assert result["status"] == "FAILED"
        assert "hard timeout" in result["error"].lower()
        assert result["judicial_review"]["verdict"] == "FAIL"

        # Verify durable checkpoint was recorded as FAILED
        from core.kernel.durable_checkpoint import get_checkpoint_engine
        cp_engine = get_checkpoint_engine()
        cp = cp_engine.load_latest_checkpoint(task_id)
        assert cp is not None
        assert cp.status == "FAILED"
        assert cp.step_id == -1
        assert "MISSION_HARD_TIMEOUT" in cp.idempotency_key
