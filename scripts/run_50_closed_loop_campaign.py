# -*- coding: utf-8 -*-
"""
scripts/run_50_closed_loop_campaign.py
CHIẾN DỊCH 50 LƯỢT KIỂM THỬ VÒNG LẶP KHÉP KÍN 3 BÊN (SSoT v1.2)
Tuân thủ đầy đủ quy trình tại 'Thao luan AI/Quy trinh vong lap kiem thu khep kin 3 Ben.md':
1. Nạp nhiệm vụ trực tiếp qua http://localhost:9999/api/submit_task
2. Đo kiểm thời gian thực (Polling task_progress)
3. Xác minh tính đúng đắn ANSWER_CORRECTNESS & quy trình PROCESS_COMPLIANCE
4. Niêm phong Evidence Pack có mã băm SHA-256
5. Cập nhật data/niem_phong/dashboard.json
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import os
import hashlib
import urllib.request
from datetime import datetime, timezone

TARGET_SUBMIT_URL = "http://localhost:9999/api/submit_task"
TARGET_PROGRESS_URL = "http://localhost:9999/api/task_progress"

# Danh sách 50 nhiệm vụ chuẩn hóa thuộc 5 Domain cốt lõi của JKAI
TASKS = [
    # ── DOMAIN 1: TOÁN HỌC, LOGIC & TÍNH TOÁN TÀI CHÍNH (10 Tasks) ──
    {"id": "TASK-001", "domain": "MATH_LOGIC", "goal": "Tính kết quả: 15 * 12 + 450 / 9", "keywords": ["230"], "mode": "fast"},
    {"id": "TASK-002", "domain": "MATH_LOGIC", "goal": "Tính 15% thuế VAT của số tiền 2.500.000 đồng là bao nhiêu?", "keywords": ["375.000", "375,000", "375000"], "mode": "fast"},
    {"id": "TASK-003", "domain": "MATH_LOGIC", "goal": "Tính diện tích hình tròn có bán kính r = 7 cm (lấy pi = 3.14)", "keywords": ["153.86", "153,86"], "mode": "fast"},
    {"id": "TASK-004", "domain": "MATH_LOGIC", "goal": "Tính tổng dãy số cấp số cộng từ 1 đến 100", "keywords": ["5050", "5.050"], "mode": "fast"},
    {"id": "TASK-005", "domain": "MATH_LOGIC", "goal": "Lương cơ bản 12 triệu, phụ cấp 1.5 triệu, trừ 10.5% bảo hiểm trên lương cơ bản. Tính lương thực nhận.", "keywords": ["12.240.000", "12,240,000", "12240000", "12.24", "12,24"], "mode": "fast"},
    {"id": "TASK-006", "domain": "MATH_LOGIC", "goal": "Một sản phẩm giảm giá 20% còn 400.000đ. Giá gốc ban đầu là bao nhiêu?", "keywords": ["500.000", "500,000", "500000"], "mode": "fast"},
    {"id": "TASK-007", "domain": "MATH_LOGIC", "goal": "Tính lãi đơn của khoản vay 50 triệu trong 6 tháng với lãi suất 8%/năm", "keywords": ["2.000.000", "2,000,000", "2000000", "2 triệu"], "mode": "fast"},
    {"id": "TASK-008", "domain": "MATH_LOGIC", "goal": "Tìm bội chung nhỏ nhất (BCNN) của 12 và 18", "keywords": ["36"], "mode": "fast"},
    {"id": "TASK-009", "domain": "MATH_LOGIC", "goal": "Đổi 45 dặm một giờ (mph) sang km/h (lấy 1 mile = 1.60934 km)", "keywords": ["72.42", "72,42", "72.4"], "mode": "fast"},
    {"id": "TASK-010", "domain": "MATH_LOGIC", "goal": "Tính giá trị của (2^5 + 3^3) * 2", "keywords": ["118"], "mode": "fast"},

    # ── DOMAIN 2: QUẢN TRỊ MẠNG & DEVOPS (10 Tasks) ──
    {"id": "TASK-011", "domain": "NET_DEVOPS", "goal": "Giải thích subnet mask /27 có bao nhiêu địa chỉ IP khả dụng cho host?", "keywords": ["30", "32"], "mode": "fast"},
    {"id": "TASK-012", "domain": "NET_DEVOPS", "goal": "Cú pháp RouterOS MikroTik tạo firewall filter drop cổng telnet 23 là gì?", "keywords": ["/ip firewall filter", "drop", "23"], "mode": "fast"},
    {"id": "TASK-013", "domain": "NET_DEVOPS", "goal": "Lệnh Cisco IOS để gán cổng GigabitEthernet0/1 vào VLAN 10 dạng access port?", "keywords": ["switchport mode access", "switchport access vlan 10"], "mode": "fast"},
    {"id": "TASK-014", "domain": "NET_DEVOPS", "goal": "Phân biệt sự khác nhau giữa TCP 3-way handshake và UDP", "keywords": ["SYN", "ACK", "kết nối", "tin cậy"], "mode": "fast"},
    {"id": "TASK-015", "domain": "NET_DEVOPS", "goal": "Lệnh Linux kiểm tra cổng mạng đang lắng nghe (listen ports) dùng ss hoặc netstat", "keywords": ["ss -tlpn", "ss -tuln", "netstat -tuln"], "mode": "fast"},
    {"id": "TASK-016", "domain": "NET_DEVOPS", "goal": "Ý nghĩa của mã lỗi HTTP 403 Forbidden và cách khắc phục cơ bản", "keywords": ["quyền", "truy cập", "permission", "cấm"], "mode": "fast"},
    {"id": "TASK-017", "domain": "NET_DEVOPS", "goal": "Cấu hình Docker Compose cơ bản cho dịch vụ Nginx lắng nghe port 80", "keywords": ["version", "services", "nginx", "ports"], "mode": "fast"},
    {"id": "TASK-018", "domain": "NET_DEVOPS", "goal": "Định nghĩa và công dụng của bản ghi DNS CNAME so với bản ghi A", "keywords": ["bí danh", "alias", "địa chỉ IP", "tên miền"], "mode": "fast"},
    {"id": "TASK-019", "domain": "NET_DEVOPS", "goal": "Cú pháp iptables trên Ubuntu cho phép kết nối SSH qua cổng 22", "keywords": ["iptables -A INPUT", "22", "ACCEPT"], "mode": "fast"},
    {"id": "TASK-020", "domain": "NET_DEVOPS", "goal": "Địa chỉ Broadcast của mạng 192.168.1.0/24 là gì?", "keywords": ["192.168.1.255"], "mode": "fast"},

    # ── DOMAIN 3: LẬP TRÌNH PYTHON & XỬ LÝ DỮ LIỆU (10 Tasks) ──
    {"id": "TASK-021", "domain": "CODE_PYTHON", "goal": "Viết hàm Python kiểm tra một chuỗi có phải là Palindrome (chuỗi đối xứng) không", "keywords": ["def", "==", "[::-1]"], "mode": "fast"},
    {"id": "TASK-022", "domain": "CODE_PYTHON", "goal": "Cách dùng list comprehension trong Python để lọc các số chẵn từ list số nguyên", "keywords": ["x for x in", "% 2 == 0"], "mode": "fast"},
    {"id": "TASK-023", "domain": "CODE_PYTHON", "goal": "Cú pháp mở và đọc từng dòng file text an toàn trong Python với context manager", "keywords": ["with open", "as f", "readline"], "mode": "fast"},
    {"id": "TASK-024", "domain": "CODE_PYTHON", "goal": "Sự khác biệt giữa `is` và `==` trong Python là gì?", "keywords": ["danh tính", "giá trị", "identity", "id("], "mode": "fast"},
    {"id": "TASK-025", "domain": "CODE_PYTHON", "goal": "Viết biểu thức Regex trong Python bắt tất cả địa chỉ email hợp lệ", "keywords": ["re.", r"[\w\.-]+@[\w\.-]+", "pattern"], "mode": "fast"},
    {"id": "TASK-026", "domain": "CODE_PYTHON", "goal": "Cách xử lý ngoại lệ JSONDecodeError khi parse chuỗi JSON trong Python", "keywords": ["try", "except", "json.loads", "JSONDecodeError"], "mode": "fast"},
    {"id": "TASK-027", "domain": "CODE_PYTHON", "goal": "Giải thích Generator và từ khóa `yield` trong Python giúp tiết kiệm bộ nhớ thế nào", "keywords": ["yield", "iterator", "bộ nhớ", "lazy"], "mode": "fast"},
    {"id": "TASK-028", "domain": "CODE_PYTHON", "goal": "Hàm tính giai thừa đệ quy của n trong Python", "keywords": ["def", "n *", "return 1"], "mode": "fast"},
    {"id": "TASK-029", "domain": "CODE_PYTHON", "goal": "Cách chuyển đổi đối tượng Python Dict sang chuỗi JSON có định dạng thụt lề 2 spaces", "keywords": ["json.dumps", "indent=2"], "mode": "fast"},
    {"id": "TASK-030", "domain": "CODE_PYTHON", "goal": "Khái niệm Decorator trong Python hoạt động như thế nào? Cho ví dụ hàm đo thời gian chạy", "keywords": ["@", "functools.wraps", "wrapper"], "mode": "fast"},

    # ── DOMAIN 4: VĂN PHÒNG, BÁO CÁO & TỔNG HỢP (10 Tasks) ──
    {"id": "TASK-031", "domain": "OFFICE_DOCS", "goal": "Lập bảng Markdown so sánh ưu nhược điểm của làm việc từ xa (Remote) và tại văn phòng (On-site)", "keywords": ["|", "Remote", "On-site", "Ưu điểm", "Nhược điểm"], "mode": "fast"},
    {"id": "TASK-032", "domain": "OFFICE_DOCS", "goal": "Soạn thảo cấu trúc mẫu biên bản cuộc họp giao ban tuần chuyên nghiệp gồm 4 mục chính", "keywords": ["Thời gian", "Thành phần", "Nội dung", "Kết luận"], "mode": "fast"},
    {"id": "TASK-033", "domain": "OFFICE_DOCS", "goal": "Viết email xin nghỉ phép 2 ngày vì lý do gia đình gửi quản lý trực tiếp", "keywords": ["Kính gửi", "Xin phép", "Lý do", "Bàn giao"], "mode": "fast"},
    {"id": "TASK-034", "domain": "OFFICE_DOCS", "goal": "Tóm tắt 3 nguyên tắc cốt lõi của phương pháp quản lý thời gian Pomodoro", "keywords": ["25", "nghỉ", "tập trung", "chu kỳ"], "mode": "fast"},
    {"id": "TASK-035", "domain": "OFFICE_DOCS", "goal": "Lập bảng kế hoạch công việc theo mô hình Ma trận Eisenhower (4 góc phần tư)", "keywords": ["Khẩn cấp", "Quan trọng", "Ủy quyền", "Loại bỏ"], "mode": "fast"},
    {"id": "TASK-036", "domain": "OFFICE_DOCS", "goal": "Nêu 5 tiêu chí cần có trong bản mô tả công việc (JD) cho vị trí Kỹ sư AI", "keywords": ["Mô tả", "Yêu cầu", "Kỹ năng", "Quyền lợi", "Kinh nghiệm"], "mode": "fast"},
    {"id": "TASK-037", "domain": "OFFICE_DOCS", "goal": "Viết đoạn văn ngắn 100 từ giới thiệu về xu hướng điện toán chủ quyền (Sovereign AI)", "keywords": ["chủ quyền", "dữ liệu", "hạ tầng", "tự chủ"], "mode": "fast"},
    {"id": "TASK-038", "domain": "OFFICE_DOCS", "goal": "Cấu trúc chuẩn của một bản báo cáo sự cố hệ thống (Post-Mortem / RCA)", "keywords": ["Nguyên nhân", "Tác động", "Khắc phục", "Phòng ngừa"], "mode": "fast"},
    {"id": "TASK-039", "domain": "OFFICE_DOCS", "goal": "Viết bảng biểu kê khai các đầu mục chi phí cho một chuyến công tác 3 ngày 2 đêm", "keywords": ["Đi lại", "Lưu trú", "Công tác phí", "Tổng cộng"], "mode": "fast"},
    {"id": "TASK-040", "domain": "OFFICE_DOCS", "goal": "Nêu 4 nguyên tắc cơ bản trong bảo mật thông tin nội bộ doanh nghiệp", "keywords": ["Mật khẩu", "Phân quyền", "Bảo mật", "Dữ liệu"], "mode": "fast"},

    # ── DOMAIN 5: KIẾN THỨC TỔNG HỢP & PHẢN XẠ NHẬN THỨC (10 Tasks) ──
    {"id": "TASK-041", "domain": "KNOWLEDGE_CORE", "goal": "Bạn có năng lực gì và danh mục công cụ hỗ trợ nào?", "keywords": ["tính năng", "công cụ", "hỗ trợ", "JKAI"], "mode": "fast"},
    {"id": "TASK-042", "domain": "KNOWLEDGE_CORE", "goal": "Giải thích khái niệm Zero-Egress trong kiến trúc bảo mật của AI chủ quyền", "keywords": ["không gửi", "nội bộ", "cách ly", "dữ liệu"], "mode": "fast"},
    {"id": "TASK-043", "domain": "KNOWLEDGE_CORE", "goal": "Việt Nam có bao nhiêu tỉnh thành phố trực thuộc trung ương?", "keywords": ["63"], "mode": "fast"},
    {"id": "TASK-044", "domain": "KNOWLEDGE_CORE", "goal": "Thủ đô của nước Úc (Australia) là thành phố nào?", "keywords": ["Canberra"], "mode": "fast"},
    {"id": "TASK-045", "domain": "KNOWLEDGE_CORE", "goal": "Nguyên tố hóa học nào có ký hiệu là Fe và số nguyên tử là 26?", "keywords": ["Sắt", "Iron"], "mode": "fast"},
    {"id": "TASK-046", "domain": "KNOWLEDGE_CORE", "goal": "Năm 2026 là năm con gì theo âm lịch Việt Nam?", "keywords": ["Ngọ", "Bính Ngọ", "Ngựa"], "mode": "fast"},
    {"id": "TASK-047", "domain": "KNOWLEDGE_CORE", "goal": "Tàu vũ trụ thương mại có bán vé công khai lên Sao Hỏa năm 2026 không?", "keywords": ["chưa", "không", "thực tế"], "mode": "fast"},
    {"id": "TASK-048", "domain": "KNOWLEDGE_CORE", "goal": "Công thức tính chỉ số khối cơ thể (BMI) của con người là gì?", "keywords": ["cân nặng", "chiều cao", "bình phương"], "mode": "fast"},
    {"id": "TASK-049", "domain": "KNOWLEDGE_CORE", "goal": "Đơn vị đo lường điện trở trong hệ SI là gì?", "keywords": ["Ohm", "Ôm", "Ω"], "mode": "fast"},
    {"id": "TASK-050", "domain": "KNOWLEDGE_CORE", "goal": "Khoảng cách trung bình từ Trái Đất tới Mặt Trăng là khoảng bao nhiêu km?", "keywords": ["384.400", "384,400", "384000", "384"], "mode": "fast"},
]


def run_campaign():
    print("=" * 80)
    print("🚀 BẮT ĐẦU CHIẾN DỊCH 50 LƯỢT KIỂM THỬ VÒNG LẶP KHÉP KÍN 3 BÊN (SSoT v1.2)")
    print(f"Khởi động: {datetime.now(timezone.utc).isoformat()}")
    print("Target UI Endpoint: http://localhost:9999/api/submit_task")
    print("=" * 80)

    results = []
    t_start = time.perf_counter()

    for idx, t in enumerate(TASKS, 1):
        task_id = t["id"]
        domain = t["domain"]
        goal = t["goal"]
        expected_keywords = t["keywords"]
        mode = t["mode"]

        print(f"\n[{idx}/50] 🎯 Đang thực thi {task_id} [{domain}]: '{goal}'")
        t0 = time.perf_counter()

        # Bước 1: Gửi request tới http://localhost:9999/api/submit_task
        payload = json.dumps({"goal": goal, "mode": mode, "mission_id": f"{task_id}_closed_loop"}).encode("utf-8")
        req = urllib.request.Request(
            TARGET_SUBMIT_URL,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "JKAI-3Party-ClosedLoop/1.2"}
        )

        submit_status = None
        runtime_task_id = None
        trace_id = None
        answer = ""
        is_correct = False
        error_msg = None

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                submit_status = resp.status
                sub_data = json.loads(resp.read().decode("utf-8"))
                runtime_task_id = sub_data.get("task_id")
                trace_id = sub_data.get("trace_id")
        except Exception as e:
            error_msg = f"SUBMIT_ERROR: {e}"
            print(f"       ❌ Lỗi gửi nhiệm vụ: {e}")

        # Bước 2: Polling nhận kết quả từ task_progress
        if runtime_task_id:
            poll_start = time.perf_counter()
            max_wait = 25.0
            while time.perf_counter() - poll_start < max_wait:
                time.sleep(0.4)
                try:
                    prog_url = f"{TARGET_PROGRESS_URL}/{runtime_task_id}"
                    with urllib.request.urlopen(prog_url, timeout=5) as p_resp:
                        p_data = json.loads(p_resp.read().decode("utf-8"))
                        logs = p_data.get("logs", [])
                        for l in logs:
                            if l.get("tag") == "JKAI" and l.get("msg"):
                                answer = l.get("msg")
                                break
                    if answer:
                        break
                except Exception:
                    pass

        latency_s = round(time.perf_counter() - t0, 2)

        # Bước 3: Đánh giá rubric ANSWER_CORRECTNESS & PROCESS_COMPLIANCE
        keyword_hits = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        is_correct = bool(answer and len(answer) > 10 and len(keyword_hits) >= 1)
        compliance_pass = bool(submit_status == 200 and runtime_task_id and trace_id)
        task_passed = is_correct and compliance_pass

        status_str = "✅ PASS" if task_passed else "❌ FAIL"
        print(f"       -> Kết quả: {status_str} | Latency: {latency_s}s | Hits: {len(keyword_hits)}/{len(expected_keywords)}")
        preview = (answer[:120] + "...").replace("\n", " ") if answer else "(Không nhận được câu trả lời)"
        print(f"       -> Preview: {preview}")

        results.append({
            "task_id": task_id,
            "domain": domain,
            "goal": goal,
            "expected_keywords": expected_keywords,
            "keyword_hits": keyword_hits,
            "runtime_task_id": runtime_task_id,
            "trace_id": trace_id,
            "latency_s": latency_s,
            "answer": answer,
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else "",
            "answer_correctness": "PASS" if is_correct else "FAIL",
            "process_compliance": "PASS" if compliance_pass else "FAIL",
            "task_verdict": "PASS" if task_passed else "FAIL",
            "error": error_msg,
        })

    total_wall_s = round(time.perf_counter() - t_start, 2)
    passed_count = sum(1 for r in results if r["task_verdict"] == "PASS")
    pass_rate = round((passed_count / len(TASKS)) * 100, 2)

    # Bước 4: Tạo Evidence Pack và niêm phong SHA-256
    evidence_pack = {
        "campaign_id": "CAMPAIGN_50_CLOSED_LOOP_001",
        "protocol_ssot_version": "v1.2",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(TASKS),
        "passed_tasks": passed_count,
        "failed_tasks": len(TASKS) - passed_count,
        "pass_rate_percent": pass_rate,
        "total_duration_seconds": total_wall_s,
        "average_latency_seconds": round(total_wall_s / len(TASKS), 2),
        "target_endpoint": TARGET_SUBMIT_URL,
        "domains_covered": list(set(t["domain"] for t in TASKS)),
        "tasks": results,
    }

    evidence_json = json.dumps(evidence_pack, ensure_ascii=False, indent=2)
    pack_path = "data/niem_phong/CAMPAIGN_50_CLOSED_LOOP_EVIDENCE.json"
    with open(pack_path, "w", encoding="utf-8") as f:
        f.write(evidence_json)

    pack_sha256 = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
    with open(pack_path + ".sha256", "w", encoding="utf-8") as f:
        f.write(pack_sha256)

    # Bước 5: Cập nhật Dashboard
    dashboard_path = "data/niem_phong/dashboard.json"
    dashboard_data = {
        "protocol_ssot_version": "v1.2",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_tasks": len(TASKS),
        "passed_tasks": passed_count,
        "pass_rate": pass_rate,
        "avg_attempts_to_pass": 1.0,
        "total_inconclusive_runs": 0,
        "escalation_count": 0,
        "median_wall_s": round(total_wall_s / len(TASKS), 2),
        "active_attempts": [],
        "resolved_incidents": [],
        "campaign_evidence_sha256": pack_sha256,
    }
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print(f"🏁 TỔNG KẾT CHIẾN DỊCH 50 LƯỢT:")
    print(f"   -> Hoàn thành: {len(TASKS)}/50 tasks")
    print(f"   -> Passed: {passed_count}/{len(TASKS)} ({pass_rate}%)")
    print(f"   -> Tổng thời gian: {total_wall_s}s")
    print(f"   -> Evidence Pack SHA-256: {pack_sha256}")
    print("=" * 80)


if __name__ == "__main__":
    run_campaign()
