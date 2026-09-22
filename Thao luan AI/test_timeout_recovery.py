import os
import sys
import json
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "state.json"
WAIT_SCRIPT = SCRIPT_DIR / "wait_for_opencode_reply.py"

def test_timeout_and_error_state():
    print("[TEST 1] Kiểm tra timeout và chuyển trạng thái sang ERROR_RECOVERY với mã thoát chuẩn 20...")
    # Run waiter with 2s timeout
    res = subprocess.run(
        [sys.executable, str(WAIT_SCRIPT), "--timeout", "2", "--interval", "1"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    # Must exit with standardized code 20 (EXIT_TIMEOUT)
    assert res.returncode == 20, f"Kỳ vọng exit code 20 nhưng thực tế trả về: {res.returncode}"
    assert "TIMEOUT" in res.stderr or "TIMEOUT" in res.stdout
    print("  ✅ Waiter thoát đúng exit code 20 (EXIT_TIMEOUT) khi timeout!")

    # Check state.json
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    assert state.get("status") == "ERROR_RECOVERY", f"Trạng thái sai: {state.get('status')}"
    assert state.get("last_error") == "TIMEOUT_EXCEEDED"
    print("  ✅ state.json ghi nhận đúng ERROR_RECOVERY và TIMEOUT_EXCEEDED!")

if __name__ == "__main__":
    test_timeout_and_error_state()
    print("\n🎉 TẤT CẢ TEST CASES CỦA TIMEOUT RECOVERY ĐÃ PASS 100%!")
