"""
scripts/run_calibration_mission1.py
Harness for Mission 1 Calibration:
Tests whether JKAI Agent Loop can autonomously read, diagnose, repair, and verify
the sealed exam in tests/test_agent_autonomy/ using local Ollama.
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=" * 80)
    print("  JKAI ZENITH: MISSION 1 CALIBRATION BENCHMARK (SEALED EXAM)")
    print("  Target: Fix bug in mission1_invoice.py to achieve 4/4 PASS on test_mission1_invoice.py")
    print("=" * 80)

    # 1. Pre-flight test check
    print("\n🔍 Step 1: Pre-flight Verification of Current Red State...")
    pre_res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_agent_autonomy/test_mission1_invoice.py", "-q"],
        capture_output=True,
        text=True
    )
    print("Pre-flight exit code:", pre_res.returncode)
    print("Pre-flight output:\n", pre_res.stdout.strip() or pre_res.stderr.strip())

    # 2. Setup Agent Loop
    print("\n🚀 Step 2: Initializing Sovereign ProjectAgentLoop...")
    import httpx
    root_dir = str(Path(".").resolve())
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    sys.path.insert(0, str(Path("services/ai-brain").resolve()))
    from receptionist.executor_gateway import ExecutorGateway
    from core.kernel.project_agent_loop import ProjectAgentLoop

    http_client = httpx.AsyncClient(timeout=120.0)
    gateway = ExecutorGateway(http_client=http_client)
    
    trace_file = Path("results/calibration_mission1_trace.jsonl")
    if trace_file.exists():
        trace_file.unlink()

    agent = ProjectAgentLoop(
        executor_gateway=gateway,
        project_root="tests/test_agent_autonomy",
        mode="fix",
        max_steps=12,
        trace_file=trace_file
    )

    goal = (
        "Kiểm tra tệp tests/test_agent_autonomy/test_mission1_invoice.py để biết lỗi test gì đang xảy ra. "
        "Sau đó đọc tests/test_agent_autonomy/mission1_invoice.py, xác định nguyên nhân tính sai tiền và "
        "dùng replace_file_content để sửa lỗi trong mission1_invoice.py. "
        "Sau khi sửa xong, chạy lệnh 'python -m pytest tests/test_agent_autonomy/test_mission1_invoice.py' để đảm bảo 100% tests pass."
    )

    import time
    task_id = f"calib_mission_01_run_{int(time.time())}"
    print(f"Goal: {goal}")
    print(f"Task ID: {task_id}")
    print(f"Blackbox Trace File: {trace_file}\n")

    # 3. Run Agent Loop
    print("⏳ Step 3: Running Autonomous Agent Loop (Local Ollama)...")
    ans = await agent.run(goal=goal, task_id=task_id, trace_id=f"trace_{task_id}")
    print("\n🏁 Agent Execution Output:")
    print("-" * 60)
    print(ans)
    print("-" * 60)

    # 4. Post-flight verification
    print("\n🔍 Step 4: Independent Physical Verification on Disk...")
    post_res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_agent_autonomy/test_mission1_invoice.py", "-v"],
        capture_output=True,
        text=True
    )
    print(f"Post-flight exit code: {post_res.returncode}")
    print("Post-flight test output:\n", post_res.stdout.strip() or post_res.stderr.strip())

    is_passed = (post_res.returncode == 0)
    print("\n" + "=" * 80)
    if is_passed:
        print("  🎉 CALIBRATION MISSION 1: PASSED 100% (4/4 TESTS PASS)!")
        print("  Physical proof verified. JKAI Agent autonomous loop is fully functional.")
    else:
        print("  ❌ CALIBRATION MISSION 1: FAILED! Tests did not pass 100%.")
    print("=" * 80)

    await http_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
