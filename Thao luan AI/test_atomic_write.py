import os
import sys
import threading
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from file_lock import file_lock, atomic_write, read_locked

TEST_FILE = SCRIPT_DIR / "test_scratch.txt"

def test_atomic_write_basic():
    print("[TEST 1] Kiem tra atomic_write co ban...")
    atomic_write(str(TEST_FILE), "Line 1: Initial content\n")
    assert TEST_FILE.exists()
    content = read_locked(str(TEST_FILE))
    assert "Line 1: Initial content" in content
    print("  ✅ atomic_write va read_locked thanh cong!")

def test_concurrent_writes():
    print("[TEST 2] Kiem tra ghi dong thoi tu 5 threads voi file_lock...")
    TEST_FILE.write_text("", encoding="utf-8")
    
    errors = []
    def worker(worker_id):
        try:
            for i in range(10):
                with file_lock(str(TEST_FILE)):
                    current = TEST_FILE.read_text(encoding="utf-8")
                    atomic_write(str(TEST_FILE), current + f"W{worker_id}-I{i}\n")
                time.sleep(0.01)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(errors) == 0, f"Co loi trong threads: {errors}"
    lines = [l for l in TEST_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 50, f"Ky vong 50 dong nhung thuc te {len(lines)}"
    print("  ✅ 50/50 thao tac ghi dong thoi hoan toan nguyen tu khong mat du lieu!")

if __name__ == "__main__":
    try:
        test_atomic_write_basic()
        test_concurrent_writes()
        print("\n🎉 TAT CA TEST CASES CUA file_lock.py DA PASS 100%!")
    finally:
        if TEST_FILE.exists():
            try: TEST_FILE.unlink()
            except Exception: pass
        lock_file = Path(f"{TEST_FILE}.lock")
        if lock_file.exists():
            try: lock_file.unlink()
            except Exception: pass
