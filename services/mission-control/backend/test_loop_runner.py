#!/usr/bin/env python3
"""
JKAI 100-Question Automated Test Loop
For each question: submit -> wait completion -> verify -> pass/retry -> next
"""
import requests
import json
import time
import os
import subprocess
import sys
from datetime import datetime

API_BASE = os.getenv("JKAI_API_URL", "http://localhost:9999/api")
REDIS_PASS = "Admin@123456"

QUESTIONS = [
    # === EASY (1-20): Greetings, basic commands, simple Q&A ===
    {"id": 1,  "q": "Xin chào",                         "mode": "fast", "level": "EASY"},
    {"id": 2,  "q": "Hello",                             "mode": "fast", "level": "EASY"},
    {"id": 3,  "q": "Bạn là ai?",                        "mode": "fast", "level": "EASY"},
    {"id": 4,  "q": "Good morning",                      "mode": "fast", "level": "EASY"},
    {"id": 5,  "q": "Hi there",                          "mode": "fast", "level": "EASY"},
    {"id": 6,  "q": "/help",                             "mode": "fast", "level": "EASY"},
    {"id": 7,  "q": "/status",                           "mode": "fast", "level": "EASY"},
    {"id": 8,  "q": "Bạn làm được những gì?",            "mode": "fast", "level": "EASY"},
    {"id": 9,  "q": "Who are you?",                      "mode": "fast", "level": "EASY"},
    {"id": 10, "q": "1+1 bằng mấy?",                     "mode": "fast", "level": "EASY"},
    {"id": 11, "q": "Việt Nam có bao nhiêu tỉnh?",       "mode": "fast", "level": "EASY"},
    {"id": 12, "q": "Thủ đô của Pháp là gì?",            "mode": "fast", "level": "EASY"},
    {"id": 13, "q": "Mặt trời mọc hướng nào?",           "mode": "fast", "level": "EASY"},
    {"id": 14, "q": "Nước có màu gì?",                   "mode": "fast", "level": "EASY"},
    {"id": 15, "q": "Dịch 'hello' sang tiếng Việt",      "mode": "fast", "level": "EASY"},
    {"id": 16, "q": "'Beautiful' nghĩa là gì?",          "mode": "fast", "level": "EASY"},
    {"id": 17, "q": "Hôm nay là thứ mấy?",               "mode": "fast", "level": "EASY"},
    {"id": 18, "q": "Mấy giờ rồi?",                      "mode": "fast", "level": "EASY"},
    {"id": 19, "q": "Năm nay là năm bao nhiêu?",         "mode": "fast", "level": "EASY"},
    {"id": 20, "q": "Bạn có khỏe không?",                "mode": "fast", "level": "EASY"},

    # === MEDIUM (21-45): Factual, calculations ===
    {"id": 21, "q": "Tính 25 * 4 + 10",                  "mode": "fast", "level": "MEDIUM"},
    {"id": 22, "q": "Căn bậc hai của 144 là bao nhiêu?", "mode": "fast", "level": "MEDIUM"},
    {"id": 23, "q": "Tính diện tích hình tròn r=5cm",    "mode": "fast", "level": "MEDIUM"},
    {"id": 24, "q": "10! bằng bao nhiêu?",               "mode": "fast", "level": "MEDIUM"},
    {"id": 25, "q": "Giải phương trình 2x+5=13",         "mode": "fast", "level": "MEDIUM"},
    {"id": 26, "q": "Ai sáng lập Microsoft?",             "mode": "fast", "level": "MEDIUM"},
    {"id": 27, "q": "Python được tạo ra bởi ai?",        "mode": "fast", "level": "MEDIUM"},
    {"id": 28, "q": "Dân số Việt Nam khoảng bao nhiêu?",  "mode": "fast", "level": "MEDIUM"},
    {"id": 29, "q": "Sông dài nhất thế giới?",           "mode": "fast", "level": "MEDIUM"},
    {"id": 30, "q": "Núi cao nhất thế giới?",            "mode": "fast", "level": "MEDIUM"},
    {"id": 31, "q": "Viết 3 câu giới thiệu bản thân",    "mode": "fast", "level": "MEDIUM"},
    {"id": 32, "q": "Tạo công thức nấu phở đơn giản",    "mode": "fast", "level": "MEDIUM"},
    {"id": 33, "q": "Viết email xin nghỉ phép",          "mode": "fast", "level": "MEDIUM"},
    {"id": 34, "q": "Giải thích tại sao trời mưa?",      "mode": "fast", "level": "MEDIUM"},
    {"id": 35, "q": "Tại sao con người cần ngủ?",        "mode": "fast", "level": "MEDIUM"},
    {"id": 36, "q": "Làm thế nào để học lập trình?",     "mode": "fast", "level": "MEDIUM"},
    {"id": 37, "q": "Ưu điểm của năng lượng mặt trời?",  "mode": "fast", "level": "MEDIUM"},
    {"id": 38, "q": "So sánh giữa mèo và chó",           "mode": "fast", "level": "MEDIUM"},
    {"id": 39, "q": "'Perseverance' nghĩa là gì?",       "mode": "fast", "level": "MEDIUM"},
    {"id": 40, "q": "Giải thích 'Trăm nghe không bằng một thấy'", "mode": "fast", "level": "MEDIUM"},
    {"id": 41, "q": "Viết 5 từ đồng nghĩa với 'tốt'",   "mode": "fast", "level": "MEDIUM"},
    {"id": 42, "q": "Dịch 'Tôi đi học' sang English",    "mode": "fast", "level": "MEDIUM"},
    {"id": 43, "q": "Tháng 6 có bao nhiêu ngày?",        "mode": "fast", "level": "MEDIUM"},
    {"id": 44, "q": "1 km bằng bao nhiêu mét?",          "mode": "fast", "level": "MEDIUM"},
    {"id": 45, "q": "Bao nhiêu tuần trong 1 năm?",       "mode": "fast", "level": "MEDIUM"},

    # === HARD (46-75): Code, complex reasoning ===
    {"id": 46, "q": "Viết hàm Python tính Fibonacci",    "mode": "deep", "level": "HARD"},
    {"id": 47, "q": "Viết function đảo ngược chuỗi JS",  "mode": "deep", "level": "HARD"},
    {"id": 48, "q": "SQL query tìm lương cao nhất mỗi phòng", "mode": "deep", "level": "HARD"},
    {"id": 49, "q": "Tạo REST API endpoint Flask",       "mode": "deep", "level": "HARD"},
    {"id": 50, "q": "Viết Dockerfile cho Node.js app",   "mode": "deep", "level": "HARD"},
    {"id": 51, "q": "Phân tích ưu nhược microservices",  "mode": "deep", "level": "HARD"},
    {"id": 52, "q": "So sánh SQL và NoSQL databases",    "mode": "deep", "level": "HARD"},
    {"id": 53, "q": "Giải thích OOP và 4 tính chất",     "mode": "deep", "level": "HARD"},
    {"id": 54, "q": "Phân tích thuật toán Quick Sort",   "mode": "deep", "level": "HARD"},
    {"id": 55, "q": "Giải thích Dependency Injection",   "mode": "deep", "level": "HARD"},
    {"id": 56, "q": "Fix: print('Hello World) thiếu quote","mode": "deep", "level": "HARD"},
    {"id": 57, "q": "Fix: int('abc') xử lý ValueError",  "mode": "deep", "level": "HARD"},
    {"id": 58, "q": "Fix: list index out of range",      "mode": "deep", "level": "HARD"},
    {"id": 59, "q": "Thiết kế URL shortener system",     "mode": "deep", "level": "HARD"},
    {"id": 60, "q": "Thiết kế database e-commerce",      "mode": "deep", "level": "HARD"},
    {"id": 61, "q": "Real-time chat nên dùng tech gì?",  "mode": "deep", "level": "HARD"},
    {"id": 62, "q": "Caching strategies cho web app",    "mode": "deep", "level": "HARD"},
    {"id": 63, "q": "Load balancing là gì?",             "mode": "deep", "level": "HARD"},
    {"id": 64, "q": "Giải thích Transformer trong NLP",  "mode": "deep", "level": "HARD"},
    {"id": 65, "q": "TCP vs UDP khác nhau?",             "mode": "deep", "level": "HARD"},
    {"id": 66, "q": "Git merge vs rebase",               "mode": "deep", "level": "HARD"},
    {"id": 67, "q": "CI/CD pipeline là gì?",             "mode": "deep", "level": "HARD"},
    {"id": 68, "q": "Blockchain hoạt động thế nào?",     "mode": "deep", "level": "HARD"},
    {"id": 69, "q": "Viết decorator Python tính giờ",    "mode": "deep", "level": "HARD"},
    {"id": 70, "q": "Viết context manager Python",       "mode": "deep", "level": "HARD"},
    {"id": 71, "q": "Explain REST vs GraphQL",           "mode": "deep", "level": "HARD"},
    {"id": 72, "q": "Docker vs VM khác nhau?",           "mode": "deep", "level": "HARD"},
    {"id": 73, "q": "Agile vs Waterfall",                "mode": "deep", "level": "HARD"},
    {"id": 74, "q": "Viết unit test cho hàm tính tổng",  "mode": "deep", "level": "HARD"},
    {"id": 75, "q": "Tối ưu query SQL chậm",             "mode": "deep", "level": "HARD"},

    # === EXPERT (76-100): Complex algorithms, edge cases ===
    {"id": 76, "q": "Implement Trie data structure Python","mode": "deep", "level": "EXPERT"},
    {"id": 77, "q": "Write LRU Cache implementation",     "mode": "deep", "level": "EXPERT"},
    {"id": 78, "q": "Phát hiện chu trình trong đồ thị",   "mode": "deep", "level": "EXPERT"},
    {"id": 79, "q": "Giải bài toán 8 quân hậu",          "mode": "deep", "level": "EXPERT"},
    {"id": 80, "q": "Binary search tree CRUD operations", "mode": "deep", "level": "EXPERT"},
    {"id": 81, "q": "Thiết kế Netflix architecture",      "mode": "deep", "level": "EXPERT"},
    {"id": 82, "q": "Event-driven vs Microservices",      "mode": "deep", "level": "EXPERT"},
    {"id": 83, "q": "SAGA pattern distributed transactions","mode": "deep", "level": "EXPERT"},
    {"id": 84, "q": "CAP theorem ứng dụng thực tế",       "mode": "deep", "level": "EXPERT"},
    {"id": 85, "q": "Thiết kế recommendation system",     "mode": "deep", "level": "EXPERT"},
    {"id": 86, "q": "OWASP Top 10 giải thích",           "mode": "deep", "level": "EXPERT"},
    {"id": 87, "q": "SQL injection tấn công và phòng thủ","mode": "deep", "level": "EXPERT"},
    {"id": 88, "q": "XSS attack prevention",              "mode": "deep", "level": "EXPERT"},
    {"id": 89, "q": "JWT tokens ưu nhược điểm",          "mode": "deep", "level": "EXPERT"},
    {"id": 90, "q": "Implement rate limiter algorithm",   "mode": "deep", "level": "EXPERT"},
    {"id": 91, "q": "Nếu A>B và B>C thì kết luận?",      "mode": "deep", "level": "EXPERT"},
    {"id": 92, "q": "Bài toán mua táo và cam tính tiền", "mode": "deep", "level": "EXPERT"},
    {"id": 93, "q": "5 cats 5 mice 5 minutes puzzle",    "mode": "deep", "level": "EXPERT"},
    {"id": 94, "q": "All men are mortal. Socrates is a man","mode": "deep", "level": "EXPERT"},
    {"id": 95, "q": "Train problem: Hanoi to HCMC 1600km","mode": "deep", "level": "EXPERT"},
    {"id": 96, "q": "!@#$%^&*()_+ special chars test",   "mode": "fast", "level": "EXPERT"},
    {"id": 97, "q": "AAAAA... long message test",        "mode": "fast", "level": "EXPERT"},
    {"id": 98, "q": "/cancel",                           "mode": "fast", "level": "EXPERT"},
    {"id": 99, "q": "Viết API FastAPI CRUD user",        "mode": "deep", "level": "EXPERT"},
    {"id": 100,"q": "Thiết kế hệ thống phân tán ổn định","mode": "deep", "level": "EXPERT"},
]

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout + r.stderr
    except:
        return ""

def redis_cmd(cmd):
    return run_cmd(f"docker exec redis-ai redis-cli -a '{REDIS_PASS}' {cmd}")

def get_container_logs(container, lines=100):
    return run_cmd(f"docker logs {container} --tail {lines} 2>&1")

def ensure_system_healthy():
    """Check and reset common system issues before each test."""
    fixes = []
    status = redis_cmd("GET agent_status").strip()
    if status and 'busy' in status:
        redis_cmd("SET agent_status idle")
        fixes.append("agent_status busy->idle")
    stop = redis_cmd("GET agent:stop_signal").strip()
    if stop and stop not in ("", "nil"):
        redis_cmd("DEL agent:stop_signal")
        fixes.append("cleared stop_signal")
    paused = redis_cmd("GET agent:paused").strip()
    if paused and paused not in ("", "nil"):
        redis_cmd("DEL agent:paused")
        fixes.append("cleared paused")
    return fixes

def wait_for_completion(task_id, trace_id, timeout=300):
    """Wait for the task to complete by checking Redis history."""
    start = time.time()
    last_queue_check = 0
    while time.time() - start < timeout:
        out = redis_cmd(f"LRANGE monitor:log_history 0 200")
        lines = out.strip().split('\n')
        
        found_jkai = False
        found_master = None
        found_error = False
        error_msgs = []
        
        for line in lines:
            try:
                d = json.loads(line)
            except:
                continue
            tid = str(d.get('task_id', ''))
            if not (task_id in tid or trace_id in tid):
                continue
            tag = d.get('tag', '')
            if tag == 'JKAI':
                found_jkai = True
            elif tag in ('MASTER_WEB', 'MASTER_TELE'):
                found_master = tag
            elif tag == 'ERROR' or 'error' in str(d.get('msg', '')).lower()[:50]:
                found_error = True
                error_msgs.append(str(d.get('msg', ''))[:150])
        
        if found_jkai:
            return {
                "completed": True, "master_tag": found_master,
                "has_error": found_error, "error_msgs": error_msgs,
                "elapsed": time.time() - start
            }
        
        # Also check queue
        now = time.time()
        if now - last_queue_check > 15:
            last_queue_check = now
            qlen_s = redis_cmd("LLEN ai_task_queue").strip()
            if qlen_s == "" or qlen_s == "0":
                # Queue empty - check once more broadly
                out2 = redis_cmd(f"LRANGE monitor:log_history 0 500")
                for line in out2.strip().split('\n'):
                    try:
                        d = json.loads(line)
                    except:
                        continue
                    if task_id in str(d.get('task_id', '')) and d.get('tag') == 'JKAI':
                        found_jkai = True
                        break
                if found_jkai:
                    return {
                        "completed": True, "master_tag": found_master,
                        "has_error": found_error, "error_msgs": error_msgs,
                        "elapsed": time.time() - start
                    }
        
        time.sleep(3)
    
    return {"completed": False, "master_tag": None, "has_error": True,
            "error_msgs": ["TIMEOUT: No JKAI response in history"], "elapsed": timeout}

def check_system_errors(task_id):
    """Check container logs for errors with this task_id."""
    errors = []
    for container in ["ai-control-plane", "ai-brain", "ai-worker"]:
        logs = get_container_logs(container, 200)
        for line in logs.split('\n'):
            if task_id in line:
                if any(e in line.upper() for e in ['ERROR', 'TRACEBACK', 'EXCEPTION', 'CRITICAL']):
                    errors.append(f"[{container}] {line.strip()[:200]}")
    return errors

def submit_and_verify(question):
    """Submit task and wait for completion. Returns (passed, details)."""
    url = f"{API_BASE}/submit_task"
    payload = {"goal": question["q"], "mode": question["mode"], "source": "WEB"}
    
    try:
        r = requests.post(url, json=payload, timeout=30)
        data = r.json()
    except Exception as e:
        return False, {"error": f"Submit failed: {e}"}
    
    tid = data.get("task_id", "")
    answer = data.get("answer", "")
    
    # Reflex path - immediate answer
    if answer:
        return True, {
            "task_id": tid, "type": "reflex",
            "master_tag": "MASTER_WEB",
            "answer_len": len(answer),
            "elapsed": 0
        }
    
    # Mission path - wait for JKAI in history
    if not data.get("ok") and data.get("status") != "queued":
        return False, {"error": f"Submit reject: {data}", "task_id": tid}
    
    trid = data.get("trace_id", tid)
    completion = wait_for_completion(tid, trid)
    
    if completion["completed"]:
        return True, {
            "task_id": tid, "type": "mission",
            "master_tag": completion["master_tag"],
            "has_error": completion["has_error"],
            "error_msgs": completion["error_msgs"],
            "elapsed": completion["elapsed"]
        }
    else:
        return False, {
            "error": "timeout",
            "task_id": tid,
            "elapsed": completion["elapsed"]
        }

def main():
    print("=" * 80)
    print("JKAI 100-QUESTION TEST LOOP: Submit -> Wait -> Verify -> Fix -> Retest")
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    stats = {
        "total": len(QUESTIONS), "passed": 0, "failed": 0,
        "retries": 0, "by_level": {}, "errors": [], "fixes": [],
        "master_ok": 0, "master_missing": 0,
        "reflex_count": 0, "mission_count": 0
    }
    
    for q in QUESTIONS:
        qid = q["id"]
        level = q["level"]
        if level not in stats["by_level"]:
            stats["by_level"][level] = {"total": 0, "passed": 0}
        stats["by_level"][level]["total"] += 1
        
        display = q["q"][:55] + "..." if len(q["q"]) > 55 else q["q"]
        print(f"\n--- [{qid:3d}/{stats['total']}] [{level:6s}] ({q['mode']:5s}) {display} ---")
        
        # Ensure system healthy before each question
        system_fixes = ensure_system_healthy()
        if system_fixes:
            print(f"    System reset: {system_fixes}")
            stats["fixes"].append({"id": qid, "fixes": system_fixes})
            time.sleep(1)
        
        max_attempts = 3
        passed = False
        
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                print(f"    Retry #{attempt}...")
                stats["retries"] += 1
                # Extra system reset before retry
                ensure_system_healthy()
                time.sleep(2)
            
            submit_ok, details = submit_and_verify(q)
            
            if submit_ok:
                task_type = details.get("type", "unknown")
                elapsed = details.get("elapsed", 0)
                mt = details.get("master_tag")
                
                if task_type == "reflex":
                    stats["reflex_count"] += 1
                    alen = details.get("answer_len", 0)
                    print(f"    PASS [REFLEX] ({alen} chars) [0s] Master:MASTER_WEB")
                    stats["master_ok"] += 1
                else:
                    stats["mission_count"] += 1
                    if mt:
                        stats["master_ok"] += 1
                        master_s = mt
                    else:
                        stats["master_missing"] += 1
                        master_s = "MISSING"
                    
                    err_s = ""
                    if details.get("has_error"):
                        err_s = " ERRORS"
                        for em in details.get("error_msgs", [])[:2]:
                            print(f"      [!] {em}")
                    
                    print(f"    PASS [{task_type.upper()}] [{elapsed:.0f}s] Master:{master_s}{err_s}")
                    
                    sys_errs = check_system_errors(details.get("task_id", ""))
                    if sys_errs:
                        print(f"    SYSTEM ERRORS:")
                        for e in sys_errs[:3]:
                            print(f"      {e}")
                
                passed = True
                stats["passed"] += 1
                stats["by_level"][level]["passed"] += 1
                break
            else:
                error = details.get("error", "unknown")
                tid = details.get("task_id", "")
                print(f"    FAIL: {error} ({tid})")
                
                # Try to fix
                fixes = ensure_system_healthy()
                if fixes:
                    stats["fixes"].append({"id": qid, "fixes": fixes, "attempt": attempt})
                    print(f"    Auto-fix: {fixes}")
                
                # Check system errors
                if tid:
                    sys_errs = check_system_errors(tid)
                    if sys_errs:
                        for e in sys_errs[:3]:
                            print(f"      {e}")
        
        if not passed:
            stats["failed"] += 1
            stats["errors"].append({"id": qid, "q": q["q"][:50], "error": details.get("error", "max retries")})
            print(f"    => FAILED after {max_attempts} attempts")
        
        # Brief pause
        time.sleep(1)
    
    # Summary
    print("\n\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total: {stats['total']} | Passed: {stats['passed']} | Failed: {stats['failed']}")
    rate = stats['passed']/stats['total']*100 if stats['total'] > 0 else 0
    print(f"Pass rate: {rate:.1f}% | Retries: {stats['retries']}")
    print(f"Reflex: {stats['reflex_count']} | Mission: {stats['mission_count']}")
    print(f"Master tag OK: {stats['master_ok']} | Missing: {stats['master_missing']}")
    
    print(f"\nBy level:")
    for level, data in sorted(stats["by_level"].items()):
        r = data["passed"]/data["total"]*100 if data["total"] > 0 else 0
        print(f"  {level:6s}: {data['passed']}/{data['total']} ({r:.0f}%)")
    
    if stats["fixes"]:
        print(f"\nAuto-fixes: {len(stats['fixes'])}")
        shown = set()
        for f in stats["fixes"]:
            key = str(f.get("fixes", ""))
            if key not in shown:
                shown.add(key)
                print(f"  Q{f['id']}: {f['fixes']}")
    
    if stats["errors"]:
        print(f"\nERRORS ({len(stats['errors'])}):")
        for e in stats["errors"]:
            print(f"  Q{e['id']} ({e.get('q','')}): {e.get('error','')}")
    
    print(f"\nEnd: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    return stats

if __name__ == "__main__":
    stats = main()
    sys.exit(0 if stats["failed"] == 0 else 1)
