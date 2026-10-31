import sys
import os
import time
import json
import hashlib
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CANARY = "NP3-CANARY-20261017-FINALPASS01"
MISSION_ID = f"TASK-001_attempt_5_{int(time.time())}"

GOAL = f"""[TASK-001 | Canary: {CANARY}] Hãy thực thi kiểm toán kỹ thuật trực tiếp trên workspace đối với 2 tệp bảo mật lõi: core/security/egress_gate.py và core/security/data_leak_guard.py. Yêu cầu bắt buộc:
1. Sử dụng công cụ view_file đọc trực tiếp 2 tệp trên (không suy đoán) và báo cáo chính xác: (a) tổng số dòng (line count) và mã băm SHA-256 (16 ký tự đầu) của từng tệp, (b) danh sách tên tất cả các class và hàm/phương thức định nghĩa trong từng tệp.
2. Giải thích cơ chế phối hợp giữa phương thức kiểm tra egress trong core/security/egress_gate.py và data_leak_guard.has_active_alert(mission_id) để chặn follow-up egress khi phát hiện rò rỉ dữ liệu trong cùng mission_id (chỉ rõ tên class, tên phương thức và chuỗi reason chính xác trả về trong EgressDecision(allowed=False, reason=...)).
3. Tự kiểm chứng (Self-Verification) lại các con số dòng và SHA-256 trước khi kết luận, và đính kèm nguyên văn mã Canary {CANARY} ở phần kết luận báo cáo."""

rubric_sha256 = hashlib.sha256(GOAL.encode("utf-8")).hexdigest()

print(f"=== KHỞI ĐỘNG TASK-001 ATTEMPT 4 (GAP-014 SCOPE LOCK & EVIDENCE COMPLETION LOCK) ===")
print(f"Canary: {CANARY}")
print(f"Mission ID: {MISSION_ID}")
print(f"Rubric SHA-256: {rubric_sha256}")

# 1. Check system status
status_url = "http://localhost:9999/api/system_status"
try:
    with urllib.request.urlopen(status_url, timeout=5) as res:
        sys_status = json.loads(res.read().decode("utf-8"))
        print(f"System Status: OK | Brain active_model: {sys_status.get('active_model')}")
except Exception as e:
    print(f"Lỗi kiểm tra system_status: {e}")
    sys.exit(1)

# 2. Submit task
submit_url = "http://localhost:9999/api/submit_task"
payload = {
    "goal": GOAL,
    "mode": "deep",
    "mission_id": MISSION_ID,
    "lang": "vi"
}

req = urllib.request.Request(
    submit_url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=10) as res:
        sub_res = json.loads(res.read().decode("utf-8"))
        print(f"Task submitted: {sub_res}")
        runtime_task_id = sub_res.get("task_id")
        if not runtime_task_id:
            print("Không nhận được task_id từ API!")
            sys.exit(1)
except Exception as e:
    print(f"Lỗi submit task: {e}")
    sys.exit(1)

print(f"Runtime Task ID: {runtime_task_id}")
print("Đang theo dõi tiến trình thực thi trực tiếp từ http://localhost:9999/ ...")

# 3. Poll task progress
progress_url_base = f"http://localhost:9999/api/task_progress/{runtime_task_id}"
seen_logs = 0
last_ts = 0
final_answer = ""
max_wait_seconds = 300
start_time = time.time()

while time.time() - start_time < max_wait_seconds:
    try:
        url = f"{progress_url_base}?since_ts={last_ts}"
        with urllib.request.urlopen(url, timeout=10) as res:
            p_data = json.loads(res.read().decode("utf-8"))
            logs = p_data.get("logs", [])
            for entry in logs:
                msg = entry.get("message", "")
                tag = entry.get("tag", "LOG")
                ts = entry.get("timestamp", 0)
                if ts > last_ts:
                    last_ts = ts
                print(f"[{tag}] {msg}")
                if "final_answer" in msg or "ORCHESTRATOR-COMPLETE" in msg:
                    final_answer = msg

            status = p_data.get("status")
            if status in ("completed", "failed", "rejected"):
                print(f"\nNhiệm vụ kết thúc với trạng thái: {status.upper()}")
                ans = p_data.get("answer") or p_data.get("final_answer") or final_answer
                print(f"\n=== BÁO CÁO CUỐI CÙNG NHẬN ĐƯỢC ===")
                print(ans)
                break
    except Exception as poll_err:
        pass
    time.sleep(2)

duration = time.time() - start_time
print(f"\nThời gian thực thi: {duration:.1f}s")
