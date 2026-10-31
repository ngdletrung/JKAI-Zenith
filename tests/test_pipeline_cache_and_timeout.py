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



# ==============================================================================
# PHASE R0 INVARIANT TESTS (Turn 43 Remediation: R0.1 - R0.5)
# ==============================================================================

@pytest.mark.asyncio
async def test_r0_1_task_id_trace_id_propagation_and_no_task_none():
    """
    R0.1: task_id/trace_id must propagate to T2-T6 and ScopedMemoryManager.distill.
    task_id=None is strictly rejected, and zero '[Task: None]' logs are emitted.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from mission_state.memory import ScopedMemoryManager
    from mission_state.schema import ScopedMemory
    from core.utils.log_engine import log_engine

    dp = DeepPipeline()

    # 1. task_id=None or "None" must raise ValueError
    with pytest.raises(ValueError, match="TASK_ID_REQUIRED"):
        await dp.execute(goal="Test", task_id=None)
    with pytest.raises(ValueError, match="TASK_ID_REQUIRED"):
        await dp.execute(goal="Test", task_id="None")

    mem = ScopedMemory()
    with pytest.raises(ValueError, match="TASK_ID_REQUIRED"):
        await ScopedMemoryManager.distill(mem, '{"step_1": {"status": "success"}}', task_id=None)

    # 2. Deterministic distillation binds task_id & trace_id without calling LLM SUMMARIZER
    log_engine.clear_stopped_state()
    log_engine._test_log_buffer.clear()
    digest = await ScopedMemoryManager.distill(
        mem,
        '{"plan_01": {"status": "success", "output": "Headline VietnamNet 2026"}}',
        task_id="ZENITH_R0_001",
        trace_id="trace_R0_001",
        use_llm=False,
    )
    assert "task_id=ZENITH_R0_001" in digest
    assert "trace_id=trace_R0_001" in digest
    assert len(mem.mission_memory["lessons_learned"]) == 1


@pytest.mark.asyncio
async def test_r0_2_stop_token_discards_late_summary_and_callbacks():
    """
    R0.2: STOPPED = no later summary.
    If STOP signal fires while T6 SUMMARIZER is running, output is discarded and
    late callbacks/thoughts after STOP are dropped.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.utils.log_engine import log_engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    dp = DeepPipeline()
    task_id = "ZENITH_R0_STOP_002"
    trace_id = "trace_R0_STOP_002"
    log_engine.clear_stopped_state()
    log_engine._test_log_buffer.clear()

    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(return_value={
        "final_plan": {"steps": [{"id": "plan_01", "tool": "BROWSER_CONTROL", "args": {"url": "https://vietnamnet.vn/"}}]},
    })

    async def fake_step_exec(*args, **kwargs):
        return True, {"content": "VietnamNet headlines verified content over 50 chars for T4"}, []

    async def fake_call_chat(*args, **kwargs):
        role = kwargs.get("role", "")
        if role == "CRITIC":
            return {"verdict": "SUCCESS", "accuracy_score": 0.95, "feedback": "Verified"}
        if role == "SUMMARIZER":
            # Simulate Master pressing STOP while Summarizer is generating
            log_engine.mark_task_stopped(task_id)
            return "Bản tóm tắt muộn sau khi đã bấm STOP không được phép xuất hiện"
        return "ok"

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_exec), \
         patch.object(engine, "call_chat", side_effect=fake_call_chat), \
         patch.object(engine, "_get_redis", return_value=None):
        res = await dp.execute(goal="Mở trang vietnamnet.vn", task_id=task_id, trace_id=trace_id)

    assert res["status"] == "STOPPED"
    assert res["answer"] == ""
    assert res["summary_published"] is False
    assert res["discarded_after_stop"] is True

    # Any late thought published for this stopped task_id must be discarded
    before_discard = log_engine._discarded_after_stop_count
    log_engine.publish_thought("SUMMARIZER", "Dưới đây là tóm tắt thông tin muộn sau STOP...", task_id=task_id)
    assert log_engine._discarded_after_stop_count > before_discard
    late_summaries = [
        entry for entry in log_engine._test_log_buffer
        if entry.get("task_id") == task_id and "tóm tắt thông tin muộn" in entry.get("msg", "")
    ]
    assert len(late_summaries) == 0
    log_engine.clear_stopped_state()


@pytest.mark.asyncio
async def test_r0_3_critic_fail_hard_gate_exits_before_t6_no_published_summary():
    """
    R0.3: Critic FAIL -> early exit before T6 (FAIL = no published summary).
    Summarizer must NEVER be called when Critic rejects the attempt.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.utils.log_engine import log_engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    dp = DeepPipeline()
    task_id = "ZENITH_R0_FAIL_003"
    trace_id = "trace_R0_FAIL_003"
    log_engine.clear_stopped_state()

    attempt_counter = {"n": 0}
    async def fake_plan_exec(state):
        attempt_counter["n"] += 1
        return {
            "final_plan": {
                "steps": [{
                    "id": f"plan_0{attempt_counter['n']}",
                    "tool": "BROWSER_CONTROL",
                    "args": {"url": "https://vietnamnet.vn/", "attempt": attempt_counter["n"]}
                }]
            }
        }
    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(side_effect=fake_plan_exec)

    async def fake_step_exec(*args, **kwargs):
        step_id = kwargs.get("step_id", "s")
        return True, {"content": f"Evidence for {step_id} with sufficient length > 50 characters."}, []

    summarizer_calls = []
    critic_calls = []

    async def fake_call_chat(*args, **kwargs):
        role = kwargs.get("role", "")
        if role == "CRITIC":
            critic_calls.append(kwargs.get("task_id"))
            return {"verdict": "FAIL", "accuracy_score": 0.20, "feedback": "Unverified evidence"}
        if role == "SUMMARIZER":
            summarizer_calls.append(kwargs.get("task_id"))
            return "Should never be called on FAIL"
        return "ok"

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_exec), \
         patch.object(engine, "call_chat", side_effect=fake_call_chat), \
         patch.object(engine, "_get_redis", return_value=None):
        res = await dp.execute(goal="Mở trang vietnamnet.vn", task_id=task_id, trace_id=trace_id)

    assert len(summarizer_calls) == 0, f"T6 Summarizer must not run on Critic FAIL, got {len(summarizer_calls)} calls"
    assert len(critic_calls) == 3
    assert res["status"] == "FAILED"
    assert res["answer"] == ""
    assert res["summary_published"] is False


@pytest.mark.asyncio
async def test_r0_4_no_checkpoint_restore_after_critic_fail_and_abort_on_identical_evidence():
    """
    R0.4: Do NOT restore old checkpoint after Critic FAIL.
    If replan produces identical plan and identical evidence as the rejected attempt,
    abort early without calling Critic/Summarizer again.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.utils.log_engine import log_engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    dp = DeepPipeline()
    task_id = "ZENITH_R0_CKPT_004"
    trace_id = "trace_R0_CKPT_004"
    log_engine.clear_stopped_state()

    # Planner returns the exact same 1-step plan on Attempt 1 and Attempt 2
    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(return_value={
        "final_plan": {
            "steps": [{"id": "plan_01", "tool": "BROWSER_CONTROL", "args": {"url": "https://vietnamnet.vn/"}}]
        }
    })

    # Fake Redis with checkpoint data to verify invalidation and non-restoration on Attempt 2
    fake_redis_store = {
        f"jkai:checkpoint:{task_id}": {
            "plan_01": '{"status": "success", "output": {"content": "Stale cached content from before"}}'
        }
    }
    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    fake_redis.hgetall.side_effect = lambda k: fake_redis_store.get(k, {})
    fake_redis.hset.side_effect = lambda k, field, val: fake_redis_store.setdefault(k, {}) .__setitem__(field, val)
    fake_redis.delete.side_effect = lambda k: fake_redis_store.pop(k, None)

    t4_exec_count = {"n": 0}
    async def fake_step_exec(*args, **kwargs):
        t4_exec_count["n"] += 1
        return True, {"content": "Identical browser output across attempts with length > 50 chars"}, []

    critic_calls = {"n": 0}
    async def fake_call_chat(*args, **kwargs):
        if kwargs.get("role") == "CRITIC":
            critic_calls["n"] += 1
            return {"verdict": "FAIL", "accuracy_score": 0.25, "feedback": "Rejected attempt 1"}
        return "ok"

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_exec), \
         patch.object(engine, "call_chat", side_effect=fake_call_chat), \
         patch.object(engine, "_get_redis", return_value=fake_redis):
        # Clear initial fake store so Attempt 1 executes fresh, saves to Redis, then Critic FAIL invalidates it
        fake_redis_store.clear()
        res = await dp.execute(goal="Mở trang vietnamnet.vn", task_id=task_id, trace_id=trace_id)

    # Attempt 1 executed T4 (1) and Critic (1 -> FAIL, deleting checkpoint).
    # Attempt 2 did NOT restore checkpoint (restored_steps == 0), executed T4 fresh (2),
    # saw identical plan_hash + evidence_hash, and aborted BEFORE calling Critic a second time!
    assert t4_exec_count["n"] == 2
    assert critic_calls["n"] == 1
    assert res["status"] == "FAILED"
    assert res["abort_replan_no_new_evidence"] is True
    assert res["step_metrics"]["restored_steps"] == 0
    assert res["step_metrics"]["executed_steps"] == 1


@pytest.mark.asyncio
async def test_r0_5_task_dedup_lock_blocks_concurrent_same_task_id():
    """
    R0.5: same task_id = one in-flight mission.
    Concurrent execution of the same task_id (e.g. 600s retry trigger) is blocked immediately.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.log_engine import log_engine

    dp = DeepPipeline()
    task_id = "ZENITH_2810-2141_b6923a_DEDUP"
    log_engine.clear_stopped_state()

    async def slow_loop(goal, task_id, **kwargs):
        await asyncio.sleep(0.25)
        return {
            "status": "SUCCESS",
            "answer": "Completed primary mission",
            "mission_id": task_id,
            "task_id": task_id,
            "trace_id": kwargs.get("trace_id", "trace_1"),
            "summary_published": True,
        }

    dp._execute_mission_loop = slow_loop

    res1, res2 = await asyncio.gather(
        dp.execute(goal="Mở trang vietnamnet.vn", task_id=task_id, trace_id="trace_primary"),
        dp.execute(goal="Mở trang vietnamnet.vn", task_id=task_id, trace_id="trace_duplicate_600s"),
    )

    statuses = {res1["status"], res2["status"]}
    assert statuses == {"SUCCESS", "REJECTED_DUPLICATE_IN_FLIGHT"}
    dup_res = res2 if res2["status"] == "REJECTED_DUPLICATE_IN_FLIGHT" else res1
    assert dup_res["duplicate_blocked"] is True
    assert dup_res["summary_published"] is False


@pytest.mark.asyncio
async def test_r0_blocker_1_rollback_step_1_no_error(caplog):
    """
    R0-Blocker 1: MissionRuntime.rollback(1) must succeed cleanly on initial state
    without logging '[ROLLBACK-ERR] Step 1 not found in snapshots.'
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from mission_state.kernel import MissionRuntime

    rt = MissionRuntime(user_goal="Test rollback step 1")
    ok = await rt.rollback(1)
    assert ok is True
    assert "[ROLLBACK-ERR]" not in caplog.text


def test_r0_blocker_2_cross_process_dedup_two_real_subprocesses_and_lease_fail_closed(tmp_path):
    """
    R0-Blocker 2 (R0_CROSS_PROCESS_DEDUP):
    1. Spawn two REAL OS subprocesses (different PIDs) sharing JKAI_LEASE_LOCK_DIR and the same task_id.
       Exactly one process must acquire the lock (ACQUIRED) while the second process is rejected (REJECTED).
    2. When get_lease_manager() raises an exception, _acquire_inflight_lock must fail-closed (False).
    """
    import subprocess
    import sys
    from pathlib import Path
    from unittest.mock import patch

    repo_root = str(Path(__file__).parent.parent)
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline, _INFLIGHT_MISSIONS

    lock_dir = str(tmp_path / "shared_leases")
    worker_script = tmp_path / "worker_dedup.py"
    worker_script.write_text(
        f"""import os, sys, time, json
sys.path.insert(0, {repo_root!r})
sys.path.insert(0, {brain_dir!r})
os.environ["JKAI_LEASE_LOCK_DIR"] = {lock_dir!r}
from deep_pipeline import DeepPipeline

task_id = sys.argv[1]
trace_id = sys.argv[2]
hold_sec = float(sys.argv[3])
delay_sec = float(sys.argv[4])
if delay_sec > 0:
    time.sleep(delay_sec)
ok, holder_id, token = DeepPipeline._acquire_inflight_lock(task_id, trace_id, ttl=30)
print(json.dumps({{"pid": os.getpid(), "acquired": ok, "holder_id": holder_id, "token": bool(token)}}), flush=True)
if ok:
    time.sleep(hold_sec)
    DeepPipeline._release_inflight_lock(task_id, holder_id, token)
""",
        encoding="utf-8",
    )

    p1 = subprocess.Popen(
        [sys.executable, str(worker_script), "ZENITH_XPROC_001", "trace_proc1", "1.2", "0.0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p2 = subprocess.Popen(
        [sys.executable, str(worker_script), "ZENITH_XPROC_001", "trace_proc2", "0.1", "0.25"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out1, err1 = p1.communicate(timeout=15)
    out2, err2 = p2.communicate(timeout=15)
    assert p1.returncode == 0, f"p1 failed: {err1}"
    assert p2.returncode == 0, f"p2 failed: {err2}"

    import json
    r1 = json.loads(out1.strip().splitlines()[-1])
    r2 = json.loads(out2.strip().splitlines()[-1])
    assert r1["pid"] != r2["pid"], "Must run in two distinct OS processes"
    assert r1["acquired"] is True
    assert r2["acquired"] is False, f"Second process must be rejected across OS processes: r1={r1}, r2={r2}"

    # Verify fail-closed when get_lease_manager raises an exception
    _INFLIGHT_MISSIONS.clear()
    with patch("core.kernel.lds_risk_governance.get_lease_manager", side_effect=RuntimeError("Simulated lease storage failure")):
        ok_fc, holder_fc, token_fc = DeepPipeline._acquire_inflight_lock("ZENITH_FAIL_CLOSED_001", "trace_fc", ttl=30)
    assert ok_fc is False
    assert holder_fc is None
    assert token_fc is None
    assert "ZENITH_FAIL_CLOSED_001" not in _INFLIGHT_MISSIONS


@pytest.mark.asyncio
async def test_r0_blocker_3_malformed_critic_fail_closed():
    """
    R0-Blocker 3 (R0_MALFORMED_CRITIC_FAIL_CLOSED):
    When Critic returns malformed non-JSON text, missing verdict, or raises an exception,
    DeepPipeline must fail-closed (verdict=FAIL, passed=False, status=FAILED, summary_published=False)
    and NEVER downgrade to PARTIAL or invoke T6 Summarizer.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.utils.log_engine import log_engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    # Unit check on _normalize_critic_review
    norm_garbage = DeepPipeline._normalize_critic_review("NOT_VALID_JSON_AT_ALL {{{")
    assert norm_garbage["verdict"] == "FAIL"
    assert norm_garbage["passed"] is False
    assert norm_garbage["reason_code"] in ("MALFORMED_CRITIC_RESPONSE", "MALFORMED_CRITIC_JSON")

    norm_empty = DeepPipeline._normalize_critic_review({"feedback": "Missing verdict key"})
    assert norm_empty["verdict"] == "FAIL"
    assert norm_empty["passed"] is False

    # Full pipeline check when Critic returns non-JSON garbage on every attempt
    dp = DeepPipeline()
    task_id = "ZENITH_MALFORMED_CRITIC_003"
    trace_id = "trace_MALFORMED_CRITIC_003"
    log_engine.clear_stopped_state()

    attempt_counter = {"n": 0}
    async def fake_plan(state):
        attempt_counter["n"] += 1
        return {
            "final_plan": {
                "steps": [{"id": f"plan_0{attempt_counter['n']}", "tool": "SEARCH_WEB_GLOBAL", "args": {"query": f"q_{attempt_counter['n']}"}}]
            }
        }
    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(side_effect=fake_plan)

    async def fake_step_exec(*args, **kwargs):
        return True, {"content": f"Valid search output for attempt {attempt_counter['n']} with > 50 characters content."}, []

    critic_calls = []
    summarizer_calls = []
    async def fake_call_chat(*args, **kwargs):
        role = kwargs.get("role", "")
        if role == "CRITIC":
            critic_calls.append(kwargs)
            return "Malformed raw string from LLM without JSON structure"
        if role == "SUMMARIZER":
            summarizer_calls.append(kwargs)
            return "Should never be called"
        return "ok"

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_exec), \
         patch.object(engine, "call_chat", side_effect=fake_call_chat), \
         patch.object(engine, "_get_redis", return_value=None):
        res = await dp.execute(goal="Tìm hiểu tin tức", task_id=task_id, trace_id=trace_id)

    assert len(critic_calls) == 3, f"Expected 3 Critic calls, got {len(critic_calls)}"
    assert len(summarizer_calls) == 0
    assert res["status"] == "FAILED"
    assert res["summary_published"] is False
    assert res["judicial_review"]["verdict"] == "FAIL"
    assert res["judicial_review"]["passed"] is False
    assert res["judicial_review"]["malformed_critic"] is True


@pytest.mark.asyncio
async def test_r1_1_to_r1_3_browser_evidence_schema_and_summary_binding(tmp_path):
    """
    R1.1, R1.2, R1.3:
    - BrowserEvidence schema requires existing screenshot file on disk, matching 64-hex SHA-256,
      non-empty headlines/dom_excerpt, and matching task_id + trace_id.
    - If browser step returns success without valid BrowserEvidence (or mismatched task_id/hash),
      DeepPipeline blocks with status='BLOCKED' before T5/T6 and summary_published=False.
    - When valid BrowserEvidence is provided with matching task_id/trace_id and real screenshot file,
      DeepPipeline verifies it and allows T6 Summarizer to publish.
    """
    import hashlib
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.utils.log_engine import log_engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    dp = DeepPipeline()
    log_engine.clear_stopped_state()

    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(return_value={
        "final_plan": {
            "steps": [{
                "id": "plan_01",
                "tool": "BROWSER_CONTROL",
                "args": {
                    "action": "load_page",
                    "url": "https://vietnamnet.vn/",
                    "capture_screenshot": True,
                    "extract_headlines": True,
                }
            }]
        }
    })

    # Case A: Browser step claims 'success' but has NO screenshot file / BrowserEvidence -> MUST BLOCK
    async def fake_step_missing_artifact(*args, **kwargs):
        return True, {"status": "success", "content": "Opened page without screenshot artifact"}, []

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_missing_artifact), \
         patch.object(engine, "_get_redis", return_value=None):
        res_blocked = await dp.execute(
            goal="Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm",
            task_id="ZENITH_R1_BLOCKED_001",
            trace_id="trace_R1_BLOCKED_001",
        )

    assert res_blocked["status"] == "BLOCKED"
    assert res_blocked["summary_published"] is False
    assert res_blocked["browser_evidence_check"]["valid"] is False

    # Case B: Browser step produces real screenshot file + SHA256 + headlines bound to task_id & trace_id -> VERIFIED & SUCCESS
    shot_file = tmp_path / "eye_vietnamnet_r1.png"
    shot_bytes = b"\x89PNG\r\n\x1a\nFAKE_PNG_PAYLOAD_FOR_R1_VERIFICATION"
    shot_file.write_bytes(shot_bytes)
    shot_sha256 = hashlib.sha256(shot_bytes).hexdigest()

    task_id_ok = "ZENITH_R1_VERIFIED_002"
    trace_id_ok = "trace_R1_VERIFIED_002"

    async def fake_step_valid_artifact(*args, **kwargs):
        return True, {
            "status": "success",
            "content": "Tiêu điểm Vietnamnet hôm nay: Kinh tế vĩ mô tăng trưởng mạnh.",
            "browser_evidence": {
                "evidence_id": "bev_test_001",
                "task_id": task_id_ok,
                "trace_id": trace_id_ok,
                "source_url": "https://vietnamnet.vn/",
                "final_url": "https://vietnamnet.vn/",
                "captured_at": "2026-10-28T14:43:00+00:00",
                "screenshot_path": str(shot_file),
                "screenshot_sha256": shot_sha256,
                "headlines": [
                    "Kinh tế vĩ mô Việt Nam quý 4/2026 tăng trưởng tích cực",
                    "Chuyển đổi số quốc gia đạt cột mốc mới năm 2026"
                ],
                "dom_excerpt": "Tiêu điểm Vietnamnet hôm nay: Kinh tế vĩ mô Việt Nam quý 4/2026 tăng trưởng tích cực.",
            }
        }, []

    async def fake_chat_ok(*args, **kwargs):
        role = kwargs.get("role", "")
        if role == "CRITIC":
            return {
                "verdict": "PASS",
                "claim_classification": "SUPPORTED",
                "accuracy_score": 0.96,
                "feedback": "Bằng chứng trình duyệt đầy đủ, ảnh chụp khớp SHA-256.",
            }
        if role == "SUMMARIZER":
            return "Báo cáo tổng hợp tiêu điểm Vietnamnet kèm ảnh chụp màn hình đã xác thực."
        return "ok"

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_valid_artifact), \
         patch.object(engine, "call_chat", side_effect=fake_chat_ok), \
         patch.object(engine, "_get_redis", return_value=None):
        res_ok = await dp.execute(
            goal="Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm",
            task_id=task_id_ok,
            trace_id=trace_id_ok,
        )

    assert res_ok["status"] == "SUCCESS"
    assert res_ok["summary_published"] is True
    assert "Báo cáo tổng hợp tiêu điểm Vietnamnet" in res_ok["answer"]


@pytest.mark.asyncio
async def test_r1_4_and_r1_5_kernel_temporal_context_and_critic_unverified():
    """
    R1.4 & R1.5:
    - TemporalContext is supplied deterministically by the runtime kernel (not LLM training cutoff).
    - Critic distinguishes SUPPORTED / UNVERIFIED / CONTRADICTED; when Critic returns UNVERIFIED
      or claims '2026 is future/impossible' without contradicting evidence, it does not falsely label
      2026 as FALSE and blocks T6 summary publication with status='UNVERIFIED'.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from mission_state.schema import TemporalContext
    from deep_pipeline import DeepPipeline

    t_ctx = TemporalContext.from_kernel(now_utc="2026-10-28T14:43:00+00:00")
    assert t_ctx.kernel_year == 2026
    assert "2026" in t_ctx.to_prompt_directive()

    # Check temporal consistency gate accepts 2026 as current year (not future!)
    tc_res = DeepPipeline.check_temporal_consistency("Sự kiện diễn ra ngày 28/10/2026", temporal_ctx=t_ctx)
    assert tc_res["ok"] is True
    assert tc_res["kernel_year"] == 2026

    # Check _normalize_critic_review downgrades training-cutoff hallucination ("năm 2026 là năm tương lai -> FALSE") to UNVERIFIED
    cutoff_hallucination = DeepPipeline._normalize_critic_review(
        {
            "verdict": "FAIL",
            "claim_classification": "CONTRADICTED",
            "accuracy_score": 0.1,
            "feedback": "Tin tức ghi năm 2026 là năm tương lai bất khả thi (FALSE).",
        },
        temporal_ctx=t_ctx,
    )
    assert cutoff_hallucination["claim_classification"] == "UNVERIFIED"
    assert cutoff_hallucination["verdict"] == "UNVERIFIED"
    assert cutoff_hallucination["passed"] is False


@pytest.mark.asyncio
async def test_r1_6_fast_single_url_visual_read_routing_and_evidence_gate(tmp_path):
    """
    R1.6:
    - Single-URL visual read & summarize requests route to FAST by default via PipelineResolver.
    - FastPipeline blocks (status='BLOCKED', summary_published=False) when screenshot or page content
      is missing, and succeeds when valid screenshot + page content are returned.
    """
    import hashlib
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from core.os.orchestrator.pipeline_resolver import PipelineResolver
    from core.os.routing.intent_router import IntentMode, ActionType, RouteDecision
    from fast_pipeline import FastPipeline
    from core.utils.engine import engine

    goal = "Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm"
    assert PipelineResolver.is_single_url_visual_read(goal) is True
    route_dec = RouteDecision(
        mode=IntentMode.REALTIME,
        role="RECEPTIONIST",
        action_type=ActionType.READ,
        tags=["BROWSER", "REALTIME"],
    )
    from types import SimpleNamespace
    from core.os.cognition.execution_governor import ExecutionTopology
    fake_plan = SimpleNamespace(
        goal=goal,
        route_decision=route_dec,
        os_intent="realtime",
        capability_tags=["BROWSER", "REALTIME"],
        kwargs_patch={},
    )
    fake_policy = SimpleNamespace(
        requires_policy_gate=False,
        topology=ExecutionTopology.SINGLE_AGENT,
    )
    resolved_mode, is_fast, is_deep, _ = PipelineResolver.resolve(
        plan=fake_plan,
        exec_policy=fake_policy,
        requested_mode="auto",
        user_explicit_deep=False,
        log_event=False,
    )
    assert resolved_mode == "fast" and is_fast is True and is_deep is False

    fp = FastPipeline()

    # Subcase 1: Browser service returns no screenshot file -> FastPipeline MUST return status='BLOCKED'
    class _FakeRespFail:
        status_code = 500
        def json(self):
            return {}

    class _FakeAsyncClientFail:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            return _FakeRespFail()

    import httpx
    with patch.object(httpx, "AsyncClient", _FakeAsyncClientFail):
        res_block = await fp.execute(
            goal=goal,
            task_id="ZENITH_FAST_R1_BLOCK",
            trace_id="trace_FAST_R1_BLOCK",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )

    assert res_block["status"] == "BLOCKED"
    assert res_block["summary_published"] is False
    assert res_block["answer"] == ""

    # Subcase 2: Browser service returns real screenshot file on disk + page content -> FastPipeline verifies & synthesizes
    shot_path = tmp_path / "eye_fast_vietnamnet.png"
    shot_bytes = b"\x89PNG\r\n\x1a\nFAST_PIPELINE_VALID_SCREENSHOT"
    shot_path.write_bytes(shot_bytes)
    shot_sha = hashlib.sha256(shot_bytes).hexdigest()

    class _FakeRespOk:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
        def json(self):
            return self._payload

    class _FakeAsyncClientOk:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            if url.endswith("/screenshot"):
                return _FakeRespOk({
                    "filename": str(shot_path),
                    "screenshot_path": str(shot_path),
                    "screenshot_sha256": shot_sha,
                    "final_url": "https://vietnamnet.vn/",
                    "captured_at": "2026-10-28T14:45:00+00:00",
                })
            return _FakeRespOk({
                "content": "Tiêu điểm Vietnamnet 28/10/2026: Kinh tế số bứt phá mạnh mẽ.\nChính phủ đẩy mạnh hạ tầng AI quốc gia.",
                "headlines": [
                    "Kinh tế số Việt Nam bứt phá mạnh mẽ năm 2026",
                    "Chính phủ đẩy mạnh hạ tầng AI quốc gia"
                ],
            })

    with patch.object(httpx, "AsyncClient", _FakeAsyncClientOk), \
         patch.object(engine, "call_chat", AsyncMock(return_value={"answer": "Tổng hợp tiêu điểm Vietnamnet ngày 28/10/2026 thành công."})):
        res_fast_ok = await fp.execute(
            goal=goal,
            task_id="ZENITH_FAST_R1_OK",
            trace_id="trace_FAST_R1_OK",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )

    assert res_fast_ok["status"] == "SUCCESS"
    assert res_fast_ok["summary_published"] is True
    assert res_fast_ok["browser_evidence"]["screenshot_sha256"] == shot_sha
    assert res_fast_ok["browser_evidence"]["task_id"] == "ZENITH_FAST_R1_OK"
    assert res_fast_ok["browser_evidence"]["trace_id"] == "trace_FAST_R1_OK"


@pytest.mark.asyncio
async def test_r2_1_task_scoped_file_write_and_test_stream_isolation(tmp_path, monkeypatch):
    """
    R2.1:
    - write_to_file enforces task_id scope when enforce_task_scope=True or JKAI_ENFORCE_TASK_SCOPED_WRITE=1,
      rejecting missing/sys task_id and rejecting cross-task writes (task_id != expected_task_id).
    - Valid task-scoped write_to_file emits an HMAC-SHA256 ArtifactReceipt bound to (task_id, trace_id, path, sha256).
    - In JKAI_TEST_MODE=1, publish_mission_log isolates logs from the production Redis stream.
    """
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import write_to_file
    from mission_state.schema import ArtifactReceipt
    from core.utils.log_engine import log_engine

    target_file = tmp_path / "r2_scoped_note.txt"

    # 1. Missing/default 'sys' task_id rejected when task scope enforced
    res_missing = await write_to_file(
        target_path=str(target_file),
        target_content="should not write",
        task_id="sys",
        enforce_task_scope=True,
    )
    assert res_missing["status"] == "error"
    assert res_missing["code"] == "MISSING_TASK_ID_SCOPE"
    assert not target_file.exists()

    # 2. Cross-task write (task_id != expected_task_id) rejected
    res_cross = await write_to_file(
        target_path=str(target_file),
        target_content="cross task write attempt",
        task_id="ZENITH_OTHER_TASK_999",
        expected_task_id="ZENITH_ACTIVE_TASK_001",
        enforce_task_scope=True,
    )
    assert res_cross["status"] == "error"
    assert res_cross["code"] == "CROSS_TASK_FILE_WRITE_REJECTED"
    assert not target_file.exists()

    # 3. Valid task-scoped write succeeds and issues verifiable ArtifactReceipt
    monkeypatch.setenv("JKAI_TEST_MODE", "1")
    fake_redis = MagicMock()
    with patch.object(log_engine, "_get_redis", return_value=fake_redis):
        res_ok = await write_to_file(
            target_path=str(target_file),
            target_content="Hello R2.1 Verified Task Scope!",
            task_id="ZENITH_ACTIVE_TASK_001",
            trace_id="trace_R2_001",
            expected_task_id="ZENITH_ACTIVE_TASK_001",
            enforce_task_scope=True,
        )
        # Verify JKAI_TEST_MODE prevented publishing to production Redis stream
        fake_redis.publish.assert_not_called()

    assert res_ok["status"] == "success"
    assert target_file.exists()
    rcpt_dict = res_ok.get("artifact_receipt")
    assert isinstance(rcpt_dict, dict)
    assert rcpt_dict["task_id"] == "ZENITH_ACTIVE_TASK_001"
    assert rcpt_dict["trace_id"] == "trace_R2_001"
    assert rcpt_dict["artifact_sha256"] == res_ok["sha256"]
    rcpt_obj = ArtifactReceipt(**rcpt_dict)
    assert rcpt_obj.verify() is True


@pytest.mark.asyncio
async def test_r2_2_step_metrics_reconciliation_planned_admitted_executed(tmp_path):
    """
    R2.2:
    - PolicyStage does not silently inject extra prevention steps after DAG waves are locked,
      preventing the 'Planned: 3 | Admitted: 1' drift.
    - DeepPipeline emits reconciled step_metrics where planned_steps == admitted_steps == executed_steps.
    """
    import hashlib
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from planning_pipeline import PolicyStage
    from planner import Blueprint, PlanStep
    from deep_pipeline import DeepPipeline
    from core.utils.engine import engine
    from core.os.cognition.in_flight_chain import in_flight_chain_executor

    # 1. PolicyStage preserves exact step count when pre_flight warnings exist
    bp = Blueprint(
        steps=[
            PlanStep(
                id="plan_01",
                tool="BROWSER_CONTROL",
                args={"action": "load_page", "url": "https://vietnamnet.vn/"},
                assigned_agent="agent_executor_beta.md",
                hardware_target="BETA",
            )
        ],
        execution_waves=[["plan_01"]],
    )
    fake_planner = MagicMock()
    fake_planner._attach_policies = AsyncMock(side_effect=lambda d, c, t: d)
    fake_planner._inject_prevention_steps = MagicMock()

    stage = PolicyStage()
    with patch.object(engine, "publish_progress", MagicMock()):
        st_out = await stage.run({
            "planner_instance": fake_planner,
            "blueprint_obj": bp,
            "context": "",
            "task_id": "ZENITH_R2_METRICS_001",
            "trace_id": "trace_R2_METRICS_001",
            "pre_flight": ["Warning 1: Slow network", "Warning 2: Check selector"],
        })

    final_plan = st_out["final_plan"]
    assert len(final_plan["steps"]) == 1
    assert final_plan.get("pre_flight_warnings") == ["Warning 1: Slow network", "Warning 2: Check selector"]
    fake_planner._inject_prevention_steps.assert_not_called()

    # 2. DeepPipeline reconciles step_metrics (planned == admitted == executed == 1)
    dp = DeepPipeline()
    dp._planning = MagicMock()
    dp._planning.execute = AsyncMock(return_value={"final_plan": final_plan})

    shot_file = tmp_path / "eye_r2_metrics.png"
    shot_bytes = b"\x89PNG\r\n\x1a\nR2_STEP_METRICS_PNG"
    shot_file.write_bytes(shot_bytes)
    shot_sha = hashlib.sha256(shot_bytes).hexdigest()

    async def fake_step_exec(*args, **kwargs):
        return True, {
            "status": "success",
            "content": "Tiêu điểm Vietnamnet ngày 28/10/2026.",
            "browser_evidence": {
                "evidence_id": "bev_r2_metrics",
                "task_id": "ZENITH_R2_METRICS_001",
                "trace_id": "trace_R2_METRICS_001",
                "source_url": "https://vietnamnet.vn/",
                "final_url": "https://vietnamnet.vn/",
                "captured_at": "2026-10-28T15:00:00+00:00",
                "screenshot_path": str(shot_file),
                "screenshot_sha256": shot_sha,
                "headlines": ["Tiêu điểm kinh tế số Việt Nam ngày 28/10/2026"],
                "dom_excerpt": "Tiêu điểm kinh tế số Việt Nam ngày 28/10/2026 tăng trưởng mạnh.",
            },
        }, []

    async def fake_chat(*args, **kwargs):
        if kwargs.get("role") == "CRITIC":
            return {"verdict": "PASS", "claim_classification": "SUPPORTED", "accuracy_score": 0.98, "feedback": "OK"}
        return "Báo cáo tổng hợp đã đối soát."

    with patch.object(in_flight_chain_executor, "execute_step_with_chain", side_effect=fake_step_exec), \
         patch.object(engine, "call_chat", side_effect=fake_chat), \
         patch.object(engine, "_get_redis", return_value=None):
        res = await dp.execute(
            goal="Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm",
            task_id="ZENITH_R2_METRICS_001",
            trace_id="trace_R2_METRICS_001",
        )

    assert res["status"] == "SUCCESS"
    sm = res["step_metrics"]
    assert sm["planned_steps"] == 1
    assert sm["admitted_steps"] == 1
    assert sm["rejected_steps"] == 0
    assert sm["executed_steps"] == 1
    assert sm["reconciled"] is True
    assert isinstance(res.get("summary_receipt"), dict)
    assert len(res.get("artifact_receipts", [])) >= 2


@pytest.mark.asyncio
async def test_r2_3_and_r2_4_artifact_receipts_ssrf_redirect_and_fast_stop(tmp_path):
    """
    R2.3 & R2.4:
    - BrowserEvidence.validate_integrity blocks SSRF / internal IPs (127.0.0.1, 169.254.169.254, localhost)
      and blocks cross-domain redirects (https://vietnamnet.vn/ -> https://evil-phishing.org/).
    - FastPipeline honours STOP/cancel signal and discards late LLM callbacks (status='STOPPED',
      summary_published=False, discarded_after_stop=True).
    - FastPipeline issues verifiable HMAC-SHA256 summary_receipt and artifact_receipts linking
      screenshot_sha256 + evidence_id + summary_sha256.
    """
    import hashlib
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from mission_state.schema import BrowserEvidence, ArtifactReceipt
    from fast_pipeline import FastPipeline
    from core.os.routing.intent_router import IntentMode, ActionType, RouteDecision
    from core.utils.log_engine import log_engine
    from core.utils.engine import engine

    shot_file = tmp_path / "eye_r2_security.png"
    shot_bytes = b"\x89PNG\r\n\x1a\nR2_SECURITY_SCREENSHOT"
    shot_file.write_bytes(shot_bytes)
    shot_sha = hashlib.sha256(shot_bytes).hexdigest()

    # 1. SSRF URL blocked by BrowserEvidence.validate_integrity
    ev_ssrf = BrowserEvidence(
        evidence_id="ev_ssrf_01",
        task_id="TASK_SSRF",
        trace_id="trace_SSRF",
        source_url="http://169.254.169.254/latest/meta-data/",
        final_url="http://169.254.169.254/latest/meta-data/",
        captured_at="2026-10-28T15:00:00+00:00",
        screenshot_path=str(shot_file),
        screenshot_sha256=shot_sha,
        headlines=["Internal metadata"],
        dom_excerpt="Internal metadata content",
    )
    chk_ssrf = ev_ssrf.validate_integrity(expected_task_id="TASK_SSRF", expected_trace_id="trace_SSRF")
    assert chk_ssrf["valid"] is False
    assert "EVIDENCE_SSRF_BLOCKED" in chk_ssrf["reason"]

    # 2. Cross-domain redirect blocked by BrowserEvidence.validate_integrity
    ev_redirect = BrowserEvidence(
        evidence_id="ev_redir_01",
        task_id="TASK_REDIR",
        trace_id="trace_REDIR",
        source_url="https://vietnamnet.vn/",
        final_url="https://malicious-redirect.example.org/fake-news",
        captured_at="2026-10-28T15:00:00+00:00",
        screenshot_path=str(shot_file),
        screenshot_sha256=shot_sha,
        headlines=["Fake headline after redirect"],
        dom_excerpt="Fake content after cross-domain redirect",
    )
    chk_redir = ev_redirect.validate_integrity(expected_task_id="TASK_REDIR", expected_trace_id="trace_REDIR")
    assert chk_redir["valid"] is False
    assert "EVIDENCE_REDIRECT_DOMAIN_MISMATCH" in chk_redir["reason"]

    # 3. FastPipeline STOP/cancel discards late LLM output
    fp = FastPipeline()
    goal = "Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm"
    route_dec = RouteDecision(
        mode=IntentMode.REALTIME,
        role="RECEPTIONIST",
        action_type=ActionType.READ,
        tags=["BROWSER", "REALTIME"],
    )

    class _FakeRespOk:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
        def json(self):
            return self._payload

    class _FakeAsyncClientOk:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            if url.endswith("/screenshot"):
                return _FakeRespOk({
                    "filename": str(shot_file),
                    "screenshot_path": str(shot_file),
                    "screenshot_sha256": shot_sha,
                    "final_url": "https://vietnamnet.vn/",
                    "captured_at": "2026-10-28T15:05:00+00:00",
                })
            return _FakeRespOk({
                "content": "Tiêu điểm Vietnamnet 28/10/2026: Hạ tầng số quốc gia vận hành ổn định.",
                "headlines": ["Hạ tầng số quốc gia vận hành ổn định ngày 28/10/2026"],
            })

    stop_task_id = "ZENITH_FAST_STOP_001"
    log_engine.clear_stopped_state()

    async def fake_chat_triggers_stop(*args, **kwargs):
        # Simulate user pressing STOP while LLM inference is in-flight
        log_engine._stopped_tasks.add(stop_task_id)
        return {"answer": "Late LLM output that MUST be discarded after STOP"}

    import httpx
    with patch.object(httpx, "AsyncClient", _FakeAsyncClientOk), \
         patch.object(engine, "call_chat", side_effect=fake_chat_triggers_stop):
        res_stopped = await fp.execute(
            goal=goal,
            task_id=stop_task_id,
            trace_id="trace_FAST_STOP_001",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )

    log_engine.clear_stopped_state()
    assert res_stopped["status"] == "STOPPED"
    assert res_stopped["summary_published"] is False
    assert res_stopped["discarded_after_stop"] is True
    assert res_stopped["answer"] == ""

    # 4. FastPipeline normal completion emits verifiable summary_receipt and artifact_receipts
    with patch.object(httpx, "AsyncClient", _FakeAsyncClientOk), \
         patch.object(engine, "call_chat", AsyncMock(return_value={"answer": "Bản tin tiêu điểm Vietnamnet ngày 28/10/2026 đã xác thực."})):
        res_receipts = await fp.execute(
            goal=goal,
            task_id="ZENITH_FAST_RECEIPT_002",
            trace_id="trace_FAST_RECEIPT_002",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )

    assert res_receipts["status"] == "SUCCESS"
    assert res_receipts["summary_published"] is True
    sum_rcpt = res_receipts.get("summary_receipt")
    assert isinstance(sum_rcpt, dict)
    assert ArtifactReceipt(**sum_rcpt).verify() is True
    art_rcpts = res_receipts.get("artifact_receipts", [])
    assert len(art_rcpts) >= 2
    for ar in art_rcpts:
        assert ArtifactReceipt(**ar).verify() is True


@pytest.mark.asyncio
async def test_r2_5_to_r2_8_headline_source_binding_contamination_block_and_stage_latencies(tmp_path):
    """
    R2.5, R2.6, R2.7, R2.8:
    - HeadlineRecord requires (evidence_ref, title, article_url, source_url) where article_url shares
      the registrable domain with source_url/final_url.
    - llms.txt, robots.txt, sitemap.xml, <UNTRUSTED_EXTERNAL_REFERENCE>, and policy headers
      (Truth Policy, Tool Policy, etc.) are strictly blocked from headlines, dom_excerpt, and summary.
    - FastPipeline emits raw stage_latencies_ms breakdown (browser_load_and_screenshot_ms,
      dom_extraction_ms, evidence_validation_ms, llm_synthesis_ms, receipt_issuance_ms).
    """
    import hashlib
    import sys
    from pathlib import Path
    brain_dir = str(Path(__file__).parent.parent / "services" / "ai-brain")
    if brain_dir not in sys.path:
        sys.path.insert(0, brain_dir)
    from mission_state.schema import BrowserEvidence, HeadlineRecord, ArtifactReceipt
    from fast_pipeline import FastPipeline
    from core.os.routing.intent_router import IntentMode, ActionType, RouteDecision
    from core.utils.engine import engine

    shot_file = tmp_path / "eye_r2_5.png"
    shot_bytes = b"\x89PNG\r\n\x1a\nR2_5_SCREENSHOT_BYTES"
    shot_file.write_bytes(shot_bytes)
    shot_sha = hashlib.sha256(shot_bytes).hexdigest()

    # 1. llms.txt / untrusted wrapper in headlines or dom_excerpt -> BLOCKED
    ev_llms = BrowserEvidence(
        evidence_id="ev_llms_01",
        task_id="T_LLMS",
        trace_id="tr_LLMS",
        source_url="https://vietnamnet.vn/",
        final_url="https://vietnamnet.vn/",
        captured_at="2026-10-28T16:40:00+00:00",
        screenshot_path=str(shot_file),
        screenshot_sha256=shot_sha,
        headlines=['<UNTRUSTED_EXTERNAL_REFERENCE url="https://vietnamnet.vn/llms.txt">'],
        dom_excerpt="# Báo VietNamNet\nGiấy phép hoạt động số 146/GP-BVHTTDL",
    )
    chk_llms = ev_llms.validate_integrity(expected_task_id="T_LLMS", expected_trace_id="tr_LLMS")
    assert chk_llms["valid"] is False
    assert "CONTAMINATION" in chk_llms["reason"]

    # 2. HeadlineRecord with cross-domain article_url -> BLOCKED
    ev_bad_art = BrowserEvidence(
        evidence_id="ev_bad_art_01",
        task_id="T_ART",
        trace_id="tr_ART",
        source_url="https://vietnamnet.vn/",
        final_url="https://vietnamnet.vn/",
        captured_at="2026-10-28T16:40:00+00:00",
        screenshot_path=str(shot_file),
        screenshot_sha256=shot_sha,
        headlines=["Tin tiêu điểm kiểm thử"],
        headline_records=[
            HeadlineRecord(
                evidence_ref="hl_01",
                title="Tin tiêu điểm dẫn sang tên miền lạ",
                article_url="https://external-phishing.org/bai-viet-gia.html",
                source_url="https://vietnamnet.vn/",
            )
        ],
        dom_excerpt="Tin tiêu điểm kiểm thử trên trang chủ.",
    )
    chk_bad_art = ev_bad_art.validate_integrity(
        expected_task_id="T_ART",
        expected_trace_id="tr_ART",
        require_headline_records=True,
    )
    assert chk_bad_art["valid"] is False
    assert "EVIDENCE_HEADLINE_ARTICLE_DOMAIN_MISMATCH" in chk_bad_art["reason"]

    # 3. Summary containing leaked Policy headers -> BLOCKED by validate_summary_grounding & FastPipeline
    bad_summary = "Bản tin:\n- Truth Policy: Do not state unverified facts\n- Tool Policy: Prefer precise tool execution"
    gr_bad = BrowserEvidence.validate_summary_grounding(bad_summary, {"headline_records": []})
    assert gr_bad["valid"] is False
    assert "CONTAMINATED" in gr_bad["reason"]

    # 4. FastPipeline end-to-end with valid HeadlineRecords, [hl_01] citation, and stage_latencies_ms
    fp = FastPipeline()
    goal = "Hãy mở trực quan trang https://vietnamnet.vn/ , chụp màn hình và tổng hợp các tin tiêu điểm"
    route_dec = RouteDecision(
        mode=IntentMode.REALTIME,
        role="RECEPTIONIST",
        action_type=ActionType.READ,
        tags=["BROWSER", "REALTIME"],
    )

    class _FakeRespOk:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload
        def json(self):
            return self._payload

    class _FakeAsyncClientR25:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            if url.endswith("/screenshot"):
                return _FakeRespOk({
                    "filename": str(shot_file),
                    "screenshot_path": str(shot_file),
                    "screenshot_sha256": shot_sha,
                    "final_url": "https://vietnamnet.vn/",
                    "captured_at": "2026-10-28T16:45:00+00:00",
                })
            return _FakeRespOk({
                "content": "Tin tiêu điểm VietNamNet ngày 28/10/2026: Hạ tầng số quốc gia tăng tốc.",
                "headlines": ["[hl_01] Hạ tầng số quốc gia tăng tốc mạnh mẽ trong quý 4/2026"],
                "headline_records": [
                    {
                        "evidence_ref": "hl_01",
                        "title": "Hạ tầng số quốc gia tăng tốc mạnh mẽ trong quý 4/2026",
                        "article_url": "https://vietnamnet.vn/ha-tang-so-quoc-gia-tang-toc-2336001.html",
                        "source_url": "https://vietnamnet.vn/",
                    }
                ],
            })

    import httpx
    # 4a. If LLM leaks "Truth Policy:" into summary -> FastPipeline MUST block (status='BLOCKED')
    with patch.object(httpx, "AsyncClient", _FakeAsyncClientR25), \
         patch.object(engine, "call_chat", AsyncMock(return_value={"answer": "- Truth Policy: Do not state unverified facts [hl_01]"})):
        res_contam = await fp.execute(
            goal=goal,
            task_id="ZENITH_FAST_R25_CONTAM",
            trace_id="trace_FAST_R25_CONTAM",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )
    assert res_contam["status"] == "BLOCKED"
    assert res_contam["summary_published"] is False

    # 4b. Clean grounded summary citing [hl_01] -> SUCCESS + stage_latencies_ms populated + receipt verified
    with patch.object(httpx, "AsyncClient", _FakeAsyncClientR25), \
         patch.object(engine, "call_chat", AsyncMock(return_value={"answer": "Tổng hợp tiêu điểm: Hạ tầng số quốc gia tăng tốc mạnh mẽ trong quý 4/2026 [hl_01]."})):
        res_ok = await fp.execute(
            goal=goal,
            task_id="ZENITH_FAST_R25_OK",
            trace_id="trace_FAST_R25_OK",
            context={"jkai_route_decision": route_dec, "jkai_route_goal": goal},
        )
    assert res_ok["status"] == "SUCCESS"
    assert "[hl_01]" in res_ok["answer"]
    assert ArtifactReceipt(**res_ok["summary_receipt"]).verify() is True
    lat = res_ok.get("stage_latencies_ms")
    assert isinstance(lat, dict)
    for required_lat_key in (
        "browser_load_and_screenshot_ms",
        "dom_extraction_ms",
        "evidence_validation_ms",
        "llm_synthesis_ms",
        "receipt_issuance_ms",
        "stage_1_adaptive_fork",
        "stage_3_one_pass_synthesis",
    ):
        assert required_lat_key in lat


def test_r3_1_and_r3_2_dynamic_skill_creator_sandbox_verification_and_versioned_rollback(tmp_path):
    """
    R3.1 & R3.2:
    - DynamicSkillCreator.create_skill executes candidate code in an isolated subprocess sandbox (-I)
      and rejects skills that pass AST parsing but crash at runtime (e.g. ZeroDivisionError).
    - DynamicSkillCreator supports versioned rollback via rollback_to_previous_version(skill_name, category)
      with SHA-256 verification and cryptographic rollback receipt.
    """
    from core.kernel.dynamic_skill_creator import DynamicSkillCreator

    creator = DynamicSkillCreator(
        skills_root=str(tmp_path / "skills"),
        candidates_dir=str(tmp_path / "candidates"),
        checkpoints_dir=str(tmp_path / "checkpoints"),
    )

    # 1. Skill passes AST allowlist but crashes at runtime in sandbox -> REJECTED at SANDBOX_EXECUTION_GATE
    crashing_code = (
        "def compute_ratio(a: int = 10, b: int = 0) -> float:\n"
        "    return a / b\n"
    )
    res_crash = creator.create_skill(
        skill_name="crash_ratio_skill",
        description="Skill test crash runtime",
        python_code=crashing_code,
        category="CUSTOM",
        approved=True,
        approver_id="admin_auditor",
    )
    assert res_crash["status"] == "rejected"
    assert res_crash["stage"] == "SANDBOX_EXECUTION_GATE"
    assert "SANDBOX_RUNTIME_CRASH" in res_crash["reason"]

    # 2. Publish v1.0.0 of valid skill, upgrade to v2.0.0, then rollback_to_previous_version -> v1.0.0 restored
    v1_code = (
        "def calculate_tax(amount: float = 100.0) -> float:\n"
        "    return round(amount * 0.1, 2)\n"
    )
    v2_code = (
        "def calculate_tax(amount: float = 100.0) -> float:\n"
        "    return round(amount * 0.2, 2)\n"
    )
    pub_v1 = creator.create_skill(
        skill_name="tax_calc_skill",
        description="Calculate 10% tax v1",
        python_code=v1_code,
        category="FINANCE",
        version="1.0.0",
        approved=True,
        approver_id="admin_auditor",
        require_hot_reload=False,
    )
    assert pub_v1["status"] == "success"
    v1_sha = pub_v1["code_sha256"]

    pub_v2 = creator.create_skill(
        skill_name="tax_calc_skill",
        description="Calculate 20% tax v2",
        python_code=v2_code,
        category="FINANCE",
        version="2.0.0",
        approved=True,
        approver_id="admin_auditor",
        require_hot_reload=False,
    )
    assert pub_v2["status"] == "success"
    assert pub_v2["code_sha256"] != v1_sha

    rb_res = creator.rollback_to_previous_version(
        skill_name="tax_calc_skill",
        category="FINANCE",
        task_id="TASK_R3_SKILL_ROLLBACK",
    )
    assert rb_res["status"] == "rolled_back"
    assert rb_res["restored_logic_sha256"] == v1_sha
    assert rb_res["receipt"]["hmac_signature"]


def test_r3_3_and_r3_4_shadow_harness_tool_outputs_sha256_and_dpo_contrastive_export(tmp_path):
    """
    R3.3 & R3.4:
    - ShadowHarness computes deterministic tool_outputs_sha256 and classifies tampered/mismatched
      tool_outputs as 'BAD'.
    - ShadowHarness.export_contrastive_pairs exports sanitized DPO/SFT (chosen vs rejected) pairs
      with <skill_instructions> stripped and secrets redacted.
    """
    from core.governance.shadow_harness import ShadowHarness

    harness = ShadowHarness(telemetry_dir=str(tmp_path / "telemetry"), enabled=True)
    shared_state = {
        "goal": "Tổng hợp tiêu điểm trang chủ Vietnamnet",
        "tool_outputs": [{"tool": "BROWSER_CONTROL", "headline": "Kinh tế số tăng trưởng mạnh"}],
    }
    expected_out_sha = harness.compute_tool_outputs_sha256(raw_state=shared_state)
    assert len(expected_out_sha) == 64

    # 1. Record GOOD observation (matching tool_outputs_sha256 + valid receipt)
    rec_good = harness.record_observation(
        raw_state=shared_state,
        reflex_draft={
            "answer": "<skill_instructions>INTERNAL_SECRET_SCAFFOLD</skill_instructions>Bản tin kinh tế số tăng trưởng mạnh [hl_01].",
        },
        execution_receipt={
            "receipt_id": "rcpt_good_01",
            "hmac_signature": "sig_valid_001",
            "lds_legal": True,
            "tool_outputs": shared_state["tool_outputs"],
        },
        metadata={
            "task_key": "vnnet_summary_task",
            "verification_passed": True,
            "expected_tool_outputs_sha256": expected_out_sha,
        },
    )
    assert rec_good is not None
    assert rec_good.metadata["outcome_class"] == "GOOD"
    assert rec_good.metadata["tool_outputs_sha256"] == expected_out_sha

    # 2. Record tampered observation (mismatched expected_tool_outputs_sha256 -> classified as BAD)
    rec_bad = harness.record_observation(
        raw_state=shared_state,
        reflex_draft={"answer": "Bản tin bịa đặt không có thật."},
        execution_receipt={
            "receipt_id": "rcpt_bad_02",
            "hmac_signature": "sig_valid_002",
            "lds_legal": True,
            "tool_outputs": [{"tool": "BROWSER_CONTROL", "headline": "TAMPERED_OUTPUT"}],
        },
        metadata={
            "task_key": "vnnet_summary_task",
            "verification_passed": True,
            "expected_tool_outputs_sha256": expected_out_sha,
        },
    )
    assert rec_bad is not None
    assert rec_bad.metadata["outcome_class"] == "BAD"

    # 3. Export DPO contrastive pairs and verify sanitization + pairing
    export_res = harness.export_contrastive_pairs()
    assert export_res["pairs_count"] == 1
    pair = export_res["pairs"][0]
    assert pair["chosen"]["outcome_class"] == "GOOD"
    assert pair["chosen"]["tool_outputs_sha256"] == expected_out_sha
    assert "<skill_instructions>" not in str(pair["chosen"]["reflex_draft"])
    assert pair["rejected"]["outcome_class"] == "BAD"
    assert len(export_res["dataset_sha256"]) == 64



