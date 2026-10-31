# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request
import json
import time
import hashlib
from datetime import datetime

TARGET_URL = "http://localhost:8001/receptionist"

test_cases = [
    {
        "id": "CASE_1_PURE_LOCAL",
        "description": "Thuần Local Logic/Math: Tính lương thực nhận",
        "goal": "Tính tiền lương thực nhận của nhân viên có lương cơ bản 15 triệu, phụ cấp 2 triệu, trừ 10.5% bảo hiểm (tính trên lương cơ bản) và trừ 500k quỹ công đoàn.",
        "expected_keywords": ["15", "10.5%", "bảo hiểm", "thực nhận"],
        "timeout": 45
    },
    {
        "id": "CASE_2_HYBRID_WEB",
        "description": "Hybrid Web Grounding: Tra cứu giá cả thị trường thực tế",
        "goal": "Giá thịt bò thăn và khoai tây hôm nay tại chợ hoặc siêu thị Việt Nam khoảng bao nhiêu tiền một kg?",
        "expected_keywords": ["thịt bò", "khoai tây", "kg", "đồng"],
        "timeout": 45
    },
    {
        "id": "CASE_3_UNIVERSAL_SCAFFOLDING",
        "description": "Universal Cognitive Scaffolding: Lập kế hoạch chi tiêu thực phẩm 160.000đ",
        "goal": "Lập kế hoạch mua sắm thực phẩm cho gia đình 4 người với ngân sách tối đa 160.000 đồng cho một bữa ăn đủ 4 nhóm chất. Trình bày bảng chi phí Markdown rõ ràng từng món gồm số lượng, đơn giá và thành tiền.",
        "expected_keywords": ["STT", "Thành tiền", "160", "Tổng"],
        "timeout": 60
    },
    {
        "id": "CASE_4_FAIL_SAFE",
        "description": "Fail-Safe Grounding: Câu hỏi về thực thể không tồn tại",
        "goal": "Giá vé tàu vũ trụ khứ hồi lên Sao Hỏa của Hãng Hàng không Vũ trụ Quốc gia Việt Nam năm 2026 là bao nhiêu?",
        "expected_keywords": ["không", "chưa", "thực tế"],
        "timeout": 45
    }
]

results = []

print("="*80)
print(f"BẮT ĐẦU CHẠY KIỂM THỬ LIVE TRỰC TIẾP TRÊN {TARGET_URL}")
print(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

for idx, tc in enumerate(test_cases, 1):
    print(f"\n[TEST {idx}/4] {tc['id']}: {tc['description']}")
    print(f"Goal: {tc['goal']}")
    payload = json.dumps({"goal": tc["goal"], "task_id": f"live_test_{idx}", "mode": "fast"}).encode("utf-8")
    
    t0 = time.perf_counter()
    status_code = None
    response_data = {}
    error = None
    
    req = urllib.request.Request(
        TARGET_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "AntigravityLiveTester/1.0"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=tc["timeout"]) as resp:
            status_code = resp.status
            raw_body = resp.read().decode("utf-8")
            response_data = json.loads(raw_body)
    except Exception as e:
        error = str(e)
        print(f"  ❌ Lỗi kết nối / timeout: {e}")
        
    latency_s = round(time.perf_counter() - t0, 2)
    answer = response_data.get("answer", "")
    
    # Check assertions
    kw_hits = [kw for kw in tc["expected_keywords"] if kw.lower() in answer.lower()]
    passed = bool(status_code == 200 and answer and len(answer) > 20 and len(kw_hits) >= 1)
    
    print(f"  Status: {status_code} | Latency: {latency_s}s | Passed: {passed}")
    print(f"  Keyword Hits: {kw_hits} / {tc['expected_keywords']}")
    preview = answer[:250].replace('\n', ' ')
    print(f"  Answer Preview:\n  {preview}...\n")
    
    results.append({
        "case_id": tc["id"],
        "description": tc["description"],
        "goal": tc["goal"],
        "status_code": status_code,
        "latency_seconds": latency_s,
        "passed": passed,
        "answer": answer,
        "keyword_hits": kw_hits,
        "error": error,
        "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else ""
    })

# Summary
all_passed = all(r["passed"] for r in results)
summary = {
    "timestamp": datetime.now().isoformat(),
    "target_url": TARGET_URL,
    "total_tests": len(results),
    "passed_count": sum(1 for r in results if r["passed"]),
    "all_passed": all_passed,
    "cases": results
}

with open("data/niem_phong/LIVE_SMOKE_TEST_EVIDENCE.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("="*80)
print(f"KẾT QUẢ KIỂM THỬ LIVE: {'TẤT CẢ ĐỀU PASS' if all_passed else 'CÓ TEST THẤT BẠI'}")
print(f"Đã ghi nhận bằng chứng vào 'data/niem_phong/LIVE_SMOKE_TEST_EVIDENCE.json'")
print("="*80)
