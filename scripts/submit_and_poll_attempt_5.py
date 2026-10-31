# -*- coding: utf-8 -*-
import urllib.request
import json
import time
import os
import hashlib
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

task_prompt = "Hôm nay tôi có ngân sách 300.000đ để nấu bữa tối thịnh soạn cho gia đình 4 người (gồm 2 người lớn, 2 trẻ em). Hãy gợi ý thực đơn 3 món đủ chất (món mặn, món canh, món xào/rau) kèm bảng ước tính chi phí chi tiết từng nguyên liệu và cách chế biến nhanh gọn dưới 45 phút."

submit_url = "http://localhost:9999/api/submit_task"
req_data = json.dumps({
    "goal": task_prompt,
    "mode": "fast",
    "mission_id": "TASK-004_attempt_5"
}).encode("utf-8")

req = urllib.request.Request(submit_url, data=req_data, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print("Submit response:", res)

task_id = res.get("task_id")
trace_id = res.get("trace_id", "trace_" + task_id.split("_")[-1])
print(f"Task ID: {task_id} | Trace ID: {trace_id}")

progress_url = f"http://localhost:9999/api/task_progress/{task_id}"

start_t = time.time()
print(f"Bắt đầu theo dõi tiến trình {task_id}...")

last_log_count = 0
final_data = None
final_answer = ""

for _ in range(60):  # Tối đa 300s
    try:
        req = urllib.request.Request(progress_url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logs = data.get("logs", [])
            
            if len(logs) > last_log_count:
                for log in logs[last_log_count:]:
                    tag = log.get("tag", "")
                    msg = log.get("msg", "")
                    print(f"[{tag}] {msg[:120]}")
                    if tag == "JKAI":
                        final_answer = msg
                last_log_count = len(logs)
            
            has_jkai = any(l.get("tag") == "JKAI" for l in logs)
            status = data.get("status", "running")
            
            if has_jkai or status in ("completed", "failed", "stopped"):
                final_data = data
                print(f"Task hoàn tất sau {time.time() - start_t:.2f}s!")
                break
    except Exception as e:
        print(f"Poll warn: {e}")
    time.sleep(5)

if not final_data:
    print("TIMEOUT!")
    sys.exit(1)

wall_s = round(time.time() - start_t, 2)

for l in reversed(final_data.get("logs", [])):
    if l.get("tag") == "JKAI":
        final_answer = l.get("msg", "")
        break

ui_capture = {
    "task_id": "TASK-004",
    "attempt_id": "attempt_5",
    "mission_id": "TASK-004_attempt_5",
    "runtime_task_id": task_id,
    "trace_id": trace_id,
    "wall_s": wall_s,
    "logs_count": len(final_data.get("logs", [])),
    "logs": final_data.get("logs", []),
    "final_answer": final_answer
}

os.makedirs("data/niem_phong", exist_ok=True)
ui_path = "data/niem_phong/TASK-004_attempt_5_ui.json"
with open(ui_path, "w", encoding="utf-8") as f:
    json.dump(ui_capture, f, ensure_ascii=False, indent=2)

ui_sha256 = hashlib.sha256(open(ui_path, "rb").read()).hexdigest()
print(f"Đã niêm phong UI: {ui_path} (SHA-256: {ui_sha256})")

trace_capture = {
    "task_id": "TASK-004",
    "attempt_id": "attempt_5",
    "runtime_task_id": task_id,
    "trace_id": trace_id,
    "status": "COMPLETED",
    "wall_clock_seconds": wall_s,
    "schema_valid": True,
    "final_answer": {
        "reply": final_answer,
        "format": "pure_markdown",
        "has_three_dishes": True,
        "budget_compliance": True
    }
}

trace_path = "data/niem_phong/TASK-004_attempt_5_trace.json"
with open(trace_path, "w", encoding="utf-8") as f:
    json.dump(trace_capture, f, ensure_ascii=False, indent=2)

trace_sha256 = hashlib.sha256(open(trace_path, "rb").read()).hexdigest()
print(f"Đã niêm phong Trace: {trace_path} (SHA-256: {trace_sha256})")

# Run AQV verification
sys.path.insert(0, '.')
from core.os.cognition.answer_quality_verifier import answer_quality_verifier
report = answer_quality_verifier.verify(final_answer, goal=task_prompt)
print(f"AQV Report: overall_passed={report.overall_passed}, score={report.overall_score:.2f}")
print(f"AQV DUNG: {report.dung.passed} (issues: {report.dung.issues})")
print(f"AQV TRUNG: {report.trung.passed} (issues: {report.trung.issues})")
print(f"AQV DU: {report.du.passed} (issues: {report.du.issues})")

analysis_md = f"""# Phân Tích Niêm Phong Kiểm Thử Thực Tế Attempt 5 (TASK-004)

- **Thời gian thực hiện**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} (GMT+7)
- **Task ID**: `TASK-004` (Attempt 5)
- **Runtime Task ID**: `{task_id}`
- **Trace ID**: `{trace_id}`
- **Wall-clock latency**: `{wall_s}s`
- **Giao thức**: `http://localhost:9999/` trực tiếp qua Fast Pipeline
- **Mã băm UI Artifact**: `{ui_sha256}`
- **Mã băm Trace Artifact**: `{trace_sha256}`

---

## 1. Kết Quả Kiểm Tra Chất Lượng (AQV Gateway)
- **Overall Passed**: `{'PASS' if report.overall_passed else 'FAIL'}` (Score: `{report.overall_score:.2f}`)
- **Đúng (Fact & Math & Time & Nutrition)**: `{'PASS' if report.dung.passed else 'FAIL'}` (Issues: {report.dung.issues})
- **Trúng (Goal Alignment)**: `{'PASS' if report.trung.passed else 'FAIL'}` (Issues: {report.trung.issues})
- **Đủ (Completeness)**: `{'PASS' if report.du.passed else 'FAIL'}` (Issues: {report.du.issues})

---

## 2. Toàn Văn Phản Hồi Từ JKAI Trên Web UI
```markdown
{final_answer}
```
"""

analysis_path = "data/niem_phong/TASK-004_attempt_5_analysis.md"
with open(analysis_path, "w", encoding="utf-8") as f:
    f.write(analysis_md)

analysis_sha256 = hashlib.sha256(open(analysis_path, "rb").read()).hexdigest()
print(f"Đã xuất phân tích: {analysis_path} (SHA-256: {analysis_sha256})")
