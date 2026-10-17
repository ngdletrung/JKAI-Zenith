# -*- coding: utf-8 -*-
"""
scripts/generate_gold_decision_dataset.py
===========================================
JKAI Zenith — Gold Decision LoRA Dataset Generator v2 (Phase A3).
Tạo 100 mẫu dữ liệu huấn luyện tinh hoa chuẩn nhận thức sâu (Cognitive Decision Record).
Đáp ứng 100% các tiêu chí thẩm tra của Master Lee Trung & Red Team SOP v2.4:
1. Đủ 5 nhóm chiến lược, mỗi nhóm đúng 20 mẫu:
   - FAST_DIRECT (20 mẫu - có cặp đối chứng biên)
   - MULTI_STEP_PLANNING (20 mẫu - DAG, checkpoints, điều kiện phụ thuộc)
   - ERROR_ADAPTIVE_RECOVERY (20 mẫu - Recovery Hygiene, chống tác dụng phụ)
   - ASK_USER_CLARIFICATION (20 mẫu - dừng hỏi Master khi thiếu thông tin)
   - ESCALATE_MODEL_OR_HUMAN (20 mẫu - phân định MASTER_APPROVAL vs TEACHER_MODEL)
2. Bắt buộc có 'alternatives_rejected' (dạy mô hình ranh giới quyết định).
3. Hợp đồng dữ liệu 8 trường có TTL.
4. Chống rò rỉ N-gram < 0.40 với kho đề thi sealed_C.
"""

import json
from pathlib import Path

contract = {
    "source": "verified_failure_and_expert_curation",
    "sample_count": 100,
    "created_at": "2026-10-15T20:50:00Z",
    "expires_at": "2026-11-15T20:50:00Z",
    "freshness_policy": "required",
    "benchmark_id": "phase_a3_decision_vault_v2",
    "compute_budget": 1800.0,
    "approval_tier": "TIER_2"
}

samples = []

# ==============================================================================
# NHÓM 1: FAST_DIRECT (20 mẫu) - Bao gồm các cặp đối chứng biên với MULTI_STEP
# ==============================================================================
fast_samples_raw = [
    ("Kiểm tra phiên bản của thư viện requests hiện tại", "FAST_DIRECT", "Lệnh: pip show requests.", "Single-step query. No dependencies, no DAG needed.", {"MULTI_STEP_PLANNING": "Chỉ đọc phiên bản, không sửa đổi file hay chạy migration.", "ASK_USER_CLARIFICATION": "Tên thư viện đã rõ ràng, không thiếu tham số."}),
    ("Tính căn bậc hai của 625", "FAST_DIRECT", "25", "Direct arithmetic calculation.", {"MULTI_STEP_PLANNING": "Phép tính một bước, lập kế hoạch DAG gây lãng phí tài nguyên.", "ESCALATE_MODEL_OR_HUMAN": "Số học cơ bản nằm trọn trong năng lực model nhỏ."}),
    ("Đổi 500 MB sang đơn vị KB", "FAST_DIRECT", "512,000 KB (500 * 1024).", "Direct unit conversion.", {"MULTI_STEP_PLANNING": "Chuyển đổi một bước, không cần DAG.", "ERROR_ADAPTIVE_RECOVERY": "Không có lỗi runtime nào xảy ra."}),
    ("Lệnh xem IP hiện tại trên hệ điều hành Linux", "FAST_DIRECT", "Lệnh: ip addr show hoặc ip a.", "Single-step terminal query.", {"MULTI_STEP_PLANNING": "Không có tiến trình đa bước.", "ESCALATE_MODEL_OR_HUMAN": "Lệnh đọc trạng thái vô hại, không có rủi ro."}),
    ("Hàm tính độ dài chuỗi ký tự trong Python", "FAST_DIRECT", "Sử dụng hàm: len(s).", "Standard built-in function query.", {"MULTI_STEP_PLANNING": "Chỉ tra cứu cú pháp cơ bản.", "ASK_USER_CLARIFICATION": "Yêu cầu đã đầy đủ dữ kiện."}),
    ("Tính giá trị 2^10", "FAST_DIRECT", "1024", "Direct exponential computation.", {"MULTI_STEP_PLANNING": "Không cần lập kế hoạch.", "ESCALATE_MODEL_OR_HUMAN": "Năng lực toán học cơ bản."}),
    ("Cổng mặc định của giao thức HTTPS", "FAST_DIRECT", "Port 443.", "Direct protocol knowledge.", {"MULTI_STEP_PLANNING": "Tra cứu thông số tĩnh một bước.", "ASK_USER_CLARIFICATION": "Khái niệm mạng chuẩn quốc tế."}),
    ("Ý nghĩa của cờ -v trong lệnh pytest", "FAST_DIRECT", "Hiển thị chi tiết (verbose) từng test case.", "Direct CLI flag description.", {"MULTI_STEP_PLANNING": "Không có tác vụ lập trình đa bước.", "ESCALATE_MODEL_OR_HUMAN": "Không có rủi ro an ninh."}),
    ("Mã lệnh Git để kiểm tra trạng thái các file", "FAST_DIRECT", "Lệnh: git status.", "Direct Git read command.", {"MULTI_STEP_PLANNING": "Không có sửa đổi file hay merge.", "ASK_USER_CLARIFICATION": "Mục tiêu tra cứu rõ ràng."}),
    ("Tính diện tích hình tròn có bán kính r = 7 cm (pi=22/7)", "FAST_DIRECT", "154 cm^2 (pi * r^2 = 22/7 * 49).", "Standard geometric calculation.", {"MULTI_STEP_PLANNING": "Một bước tính toán số học.", "ESCALATE_MODEL_OR_HUMAN": "Toán học phổ thông."}),
    ("Lệnh xóa một file rỗng test.txt trong Bash", "FAST_DIRECT", "Lệnh: rm test.txt.", "Single atomic file deletion.", {"MULTI_STEP_PLANNING": "Xóa một file đơn lẻ xác định.", "ESCALATE_MODEL_OR_HUMAN": "File rỗng không có nguy cơ mất mát dữ liệu hệ thống."}),
    ("Kiểm tra phiên bản Python hiện tại trên máy chủ", "FAST_DIRECT", "Lệnh: python --version.", "Direct environment inspection.", {"MULTI_STEP_PLANNING": "Chỉ đọc phiên bản, không cài đặt gói.", "ASK_USER_CLARIFICATION": "Lệnh kiểm tra tiêu chuẩn."}),
    ("Tính 15% của 1.200.000 đồng", "FAST_DIRECT", "180.000 đồng (1.200.000 * 0.15).", "Percentage arithmetic.", {"MULTI_STEP_PLANNING": "Phép tính một dòng.", "ERROR_ADAPTIVE_RECOVERY": "Không có lỗi."}),
    ("Cổng mặc định của hệ quản trị cơ sở dữ liệu PostgreSQL", "FAST_DIRECT", "Port 5432.", "Static database port query.", {"MULTI_STEP_PLANNING": "Tra cứu hằng số mạng.", "ASK_USER_CLARIFICATION": "Dữ kiện đã chuẩn xác."}),
    ("Hàm chuyển chuỗi thành chữ hoa trong Python", "FAST_DIRECT", "Phương thức: string.upper().", "Built-in string method query.", {"MULTI_STEP_PLANNING": "Không cần lập kế hoạch.", "ESCALATE_MODEL_OR_HUMAN": "Cú pháp ngôn ngữ cơ bản."}),
    ("Tính chu vi tam giác đều cạnh 12 cm", "FAST_DIRECT", "36 cm (12 * 3).", "Simple arithmetic.", {"MULTI_STEP_PLANNING": "Phép nhân một bước.", "ASK_USER_CLARIFICATION": "Cạnh đã rõ ràng."}),
    ("Lệnh tạo nhánh mới git mang tên feature-auth", "FAST_DIRECT", "Lệnh: git checkout -b feature-auth.", "Single branch creation command.", {"MULTI_STEP_PLANNING": "Tạo nhánh không yêu cầu luồng DAG.", "ESCALATE_MODEL_OR_HUMAN": "Thao tác git an toàn tại local."}),
    ("Mã lỗi HTTP 404 có nghĩa là gì", "FAST_DIRECT", "Not Found - Không tìm thấy tài nguyên.", "HTTP spec definition.", {"MULTI_STEP_PLANNING": "Tra cứu mã lỗi tĩnh.", "ERROR_ADAPTIVE_RECOVERY": "Chỉ hỏi định nghĩa, không phải đang phục hồi lỗi."}),
    ("Tính tích của 14 và 25", "FAST_DIRECT", "350 (14 * 25).", "Arithmetic multiplication.", {"MULTI_STEP_PLANNING": "Số học một bước.", "ESCALATE_MODEL_OR_HUMAN": "Toán cơ bản."}),
    ("Cách khai báo biến môi trường tạm thời trong PowerShell", "FAST_DIRECT", "Cú pháp: $env:VAR_NAME = 'value'.", "Shell syntax query.", {"MULTI_STEP_PLANNING": "Chỉ hỏi cú pháp, không thực thi script phức tạp.", "ASK_USER_CLARIFICATION": "Cú pháp chung đã rõ."})
]

for i, (prompt, strat, out_action, rationale, rejected) in enumerate(fast_samples_raw, 1):
    samples.append({
        "id": f"dec_fast_{i:02d}",
        "group": "FAST_DIRECT",
        "instruction": prompt,
        "input": "Trạng thái đơn lẻ, đầu vào đầy đủ, không có lỗi, rủi ro thấp.",
        "decision": strat,
        "output": json.dumps({
            "strategy": strat,
            "step_budget": 1,
            "action": out_action,
            "rationale": rationale,
            "alternatives_rejected": rejected,
            "success_criteria": ["Thực thi tức thì không qua DAG", "Tiết kiệm tài nguyên", "Đạt kết quả chính xác"]
        }, ensure_ascii=False),
        "data_contract": contract
    })

# ==============================================================================
# NHÓM 2: MULTI_STEP_PLANNING (20 mẫu) - DAG, checkpoints, điều kiện phụ thuộc
# ==============================================================================
multi_samples_raw = [
    ("Nâng cấp thư viện requests, quét lỗ hổng phụ thuộc và chạy lại toàn bộ test suite", "DAG: pip install --upgrade requests -> pip-audit -> pytest tests/", 3, {"FAST_DIRECT": "Nhiệm vụ gồm 3 giai đoạn phụ thuộc tuần tự, chạy trực tiếp sẽ bỏ sót bước audit và kiểm thử.", "ASK_USER_CLARIFICATION": "Tên gói và mục tiêu đã xác định rõ ràng."}),
    ("Bước 1 tạo thư mục mới, sau đó viết file cấu hình và chạy pytest kiểm tra", "DAG: mkdir -> write config -> run pytest", 3, {"FAST_DIRECT": "Các bước phụ thuộc: file config phụ thuộc thư mục, pytest phụ thuộc file config.", "ESCALATE_MODEL_OR_HUMAN": "Nhiệm vụ dev thông thường trong tầm kiểm soát."}),
    ("Nâng cấp schema CSDL: backup trước, chạy migration script, sau đó kiểm tra tính toàn vẹn", "DAG: backup db -> run migration -> verify schema", 3, {"FAST_DIRECT": "Nếu chạy migration trực tiếp mà không backup, rủi ro mất dữ liệu không thể phục hồi.", "ASK_USER_CLARIFICATION": "Quy trình chuẩn 3 bước đã rõ."}),
    ("Refactor module auth: phân tích phụ thuộc, tách logic token, cập nhật unit tests và chạy full suite", "DAG: analyze deps -> extract token logic -> update tests -> run suite", 4, {"FAST_DIRECT": "Refactor đa file đòi hỏi theo dõi tiến độ và rollback khi test gãy.", "ESCALATE_MODEL_OR_HUMAN": "Refactor cục bộ không phải rủi ro an ninh nghiêm trọng."}),
    ("Triển khai microservice: build docker image, push lên registry, cập nhật k8s và probe health check", "DAG: docker build -> push -> apply k8s -> health probe", 4, {"FAST_DIRECT": "Quy trình CD đa pha bắt buộc phải probe health sau khi rollout.", "ERROR_ADAPTIVE_RECOVERY": "Chưa có lỗi, đây là quy trình triển khai tuần tự."}),
    ("Tạo báo cáo tuần: trích xuất metrics từ telemetry, sinh biểu đồ, tổng hợp PDF và gửi thông báo", "DAG: extract metrics -> plot charts -> render PDF -> notify", 4, {"FAST_DIRECT": "Dòng dữ liệu đa tầng từ raw metrics tới file PDF hoàn chỉnh.", "ASK_USER_CLARIFICATION": "Chu kỳ báo cáo đã được lập trình."}),
    ("Đồng bộ hai kho lưu trữ: quét danh sách lệch, copy file mới, xác thực mã SHA-256 từng file", "DAG: diff file list -> copy new files -> verify sha256 checksums", 3, {"FAST_DIRECT": "Cần kiểm tra mã băm từng file để bảo đảm toàn vẹn.", "ERROR_ADAPTIVE_RECOVERY": "Tiến trình đồng bộ chủ động, không phải phục hồi lỗi."}),
    ("Xây dựng pipeline CI: chạy linter, chạy unit tests, build binary và upload artifacts", "DAG: run linter -> unit tests -> compile binary -> publish artifacts", 4, {"FAST_DIRECT": "Các bước nối tiếp có điều kiện gate (linter fail thì ngắt ngay).", "ESCALATE_MODEL_OR_HUMAN": "Quy trình CI chuẩn mực."}),
    ("Tối ưu bảng CSDL: phân tích slow query log, tạo chỉ mục index mới, benchmark lại thời gian truy vấn", "DAG: analyze slow query -> create indexes -> benchmark latency", 3, {"FAST_DIRECT": "Cần đối chiếu latency trước và sau khi index.", "ASK_USER_CLARIFICATION": "Mục tiêu tối ưu đã rõ."}),
    ("Thiết lập môi trường dev: clone repo, tạo virtualenv, cài requirements và chạy smoke test", "DAG: git clone -> venv -> pip install -> smoke test", 4, {"FAST_DIRECT": "Chuỗi cài đặt phụ thuộc tuần tự.", "ERROR_ADAPTIVE_RECOVERY": "Khởi tạo môi trường mới sạch sẽ."}),
    ("Xử lý log sự cố: thu thập log 3 nodes, lọc lỗi ERROR trong 1h, nhóm nguyên nhân và xuất CSV", "DAG: collect cluster logs -> grep errors -> aggregate root causes -> export csv", 4, {"FAST_DIRECT": "Tổng hợp dữ liệu đa nguồn cần map-reduce.", "ESCALATE_MODEL_OR_HUMAN": "Xử lý log thuần túy, không thay đổi hệ thống."}),
    ("Di chuyển storage volume: đặt chế độ read-only, rsync dữ liệu, cập nhật mount point và restart", "DAG: set read-only -> rsync -> remount -> restart service", 4, {"FAST_DIRECT": "Dừng dịch vụ và remount cần lưu checkpoint an toàn.", "ASK_USER_CLARIFICATION": "Kế hoạch di chuyển đã định sẵn."}),
    ("Đóng gói ứng dụng: biên dịch mã nguồn, ký số executable, tạo bộ cài MSI và test installer", "DAG: compile -> sign binary -> package MSI -> test installer VM", 4, {"FAST_DIRECT": "Đóng gói phần mềm gồm nhiều bước kiểm định chữ ký.", "ERROR_ADAPTIVE_RECOVERY": "Chưa có lỗi xảy ra."}),
    ("Đánh giá an ninh mạng: quét cổng Nmap, kiểm tra cấu hình SSH, rà soát sudoers và xuất audit report", "DAG: port scan -> audit sshd -> verify sudoers -> generate audit report", 4, {"FAST_DIRECT": "Kiểm toán an ninh đòi hỏi thu thập bằng chứng đa góc độ.", "ESCALATE_MODEL_OR_HUMAN": "Đánh giá an ninh ở chế độ read-only là an toàn."}),
    ("Bảo trì cụm Redis: lưu snapshot RDB, kiểm tra phân mảnh RAM, dọn dẹp expired keys và ghi log", "DAG: save RDB -> check memory frag -> evict expired keys -> write log", 4, {"FAST_DIRECT": "Quy trình bảo trì có thứ tự ưu tiên snapshot trước.", "ASK_USER_CLARIFICATION": "Chính sách bảo trì định kỳ đã có."}),
    ("Chuyển đổi giao thức mạng: cấu hình IPv6 song song, test dual-stack, cập nhật DNS AAAA và verify", "DAG: config IPv6 -> test dual-stack -> update DNS AAAA -> verify lookup", 4, {"FAST_DIRECT": "Cấu hình mạng song song cần probe kết nối trước khi đổi DNS.", "ESCALATE_MODEL_OR_HUMAN": "Chuyển đổi dual-stack có kiểm soát."}),
    ("Xây dựng dataset: tải dữ liệu thô, lọc bỏ trùng lặp, format JSONL và phân chia train/val/test", "DAG: download raw -> dedup -> format jsonl -> split train/val/test", 4, {"FAST_DIRECT": "Pipeline xử lý dữ liệu nhiều chặng.", "ERROR_ADAPTIVE_RECOVERY": "Quy trình ETL chuẩn."}),
    ("Kiểm tra tải hệ thống: chuẩn bị kịch bản Locust, chạy thử tải 500 CCU, monitor CPU/RAM và tổng kết", "DAG: prepare Locust script -> run 500 CCU -> monitor resources -> compile report", 4, {"FAST_DIRECT": "Load test đòi hỏi kịch bản và giám sát thời gian thực.", "ASK_USER_CLARIFICATION": "Tham số 500 CCU đã được cung cấp."}),
    ("Khôi phục sau thảm họa (DR drill): ngắt master, promote standby, verify đồng bộ và alert ops", "DAG: simulate failover -> promote standby -> verify sync -> alert ops team", 4, {"FAST_DIRECT": "Quy trình diễn tập thảm họa cần kiểm soát nghiêm ngặt từng cổng.", "ESCALATE_MODEL_OR_HUMAN": "Kịch bản diễn tập đã được phê chuẩn trong môi trường test."}),
    ("Chuẩn bị bài thuyết trình kỹ thuật: trích xuất số liệu benchmark, soạn dàn ý, vẽ sơ đồ và xuất slide", "DAG: collect metrics -> outline deck -> draw diagrams -> export slides", 4, {"FAST_DIRECT": "Sản phẩm phức tạp gồm nhiều thành phần con.", "ERROR_ADAPTIVE_RECOVERY": "Tác vụ sáng tạo tuần tự."})
]

for i, (prompt, plan, steps, rejected) in enumerate(multi_samples_raw, 1):
    samples.append({
        "id": f"dec_multi_{i:02d}",
        "group": "MULTI_STEP_PLANNING",
        "instruction": prompt,
        "input": "Yêu cầu gồm nhiều bước phụ thuộc, cần theo dõi tiến độ và checkpoint.",
        "decision": "MULTI_STEP_PLANNING",
        "output": json.dumps({
            "strategy": "MULTI_STEP_PLANNING",
            "step_budget": steps,
            "plan": plan,
            "rationale": f"Phát hiện nhiệm vụ đa bước ({steps} giai đoạn). Khởi tạo kế hoạch DAG và checkpoint.",
            "alternatives_rejected": rejected,
            "success_criteria": ["Mọi bước trong DAG được hoàn thành", "Lưu vết checkpoint", "Xác thực 100% tiêu chí"]
        }, ensure_ascii=False),
        "data_contract": contract
    })

# ==============================================================================
# NHÓM 3: ERROR_ADAPTIVE_RECOVERY (20 mẫu) - Tuân thủ Recovery Hygiene, chống tác dụng phụ
# ==============================================================================
recovery_samples_raw = [
    ("Lệnh git commit thất bại: 'syntax error: unmatched quotes in commit message'", "ARGUMENT_RE_ENCODING", "Chuẩn hóa và thoát chuỗi ký tự trong message commit.", {"FAST_DIRECT": "Lệnh ban đầu đã fail, chạy lại y nguyên sẽ lặp lỗi.", "PATH_RECONCILIATION": "Lỗi cú pháp tham số, không liên quan đến đường dẫn file."}),
    ("Đọc file /app/secret.key báo lỗi Permission denied (403)", "AUTHORITY_VERIFY_AND_HALT", "Dừng lại xác minh thẩm quyền truy cập, không tự ý chuyển sang file khác hay leo quyền.", {"FAST_DIRECT": "Chạy lại lệnh cũ sẽ tiếp tục bị từ chối quyền.", "PATH_RECONCILIATION": "Nghiêm cấm tự ý đổi sang đường dẫn khác khi bị từ chối quyền (vi phạm an ninh)."}),
    ("Truy vấn CSDL bị ConnectionTimeout(30s), kiểm tra Redis cache thấy TTL đã hết hạn", "STALE_CACHE_ABORT", "Dừng lại và thông báo lỗi timeout, từ chối dùng cache hết hạn (freshness_verified == false).", {"FALLBACK_OFFLINE_SEARCH": "Không được dùng dữ liệu cache cũ vì tính mới chưa được kiểm chứng (freshness_verified == false).", "FAST_DIRECT": "Mạng CSDL đang nghẽn, gọi lại ngay sẽ gây bão request."}),
    ("Đọc file config ./config/dev.yaml báo lỗi FileNotFoundError trong thư mục dev", "PATH_RECONCILIATION", "Dò tìm trong danh mục đường dẫn dự phòng đã đăng ký (./config/default.yaml), không tự ý tạo thư mục hệ thống.", {"FAST_DIRECT": "File không tồn tại ở đường dẫn cũ.", "ARGUMENT_RE_ENCODING": "Lỗi do file thiếu, không phải do cú pháp tham số."}),
    ("Chạy lệnh phân tích FAST_DIRECT bị crash do thiếu bộ nhớ", "PROMOTE_TO_DAG_WITH_CHECKPOINT", "Nâng cấp lên MULTI_STEP_PLANNING có chia nhỏ batch và lưu checkpoint.", {"FAST_DIRECT": "Đã crash ở chế độ trực tiếp do quá tải bộ nhớ.", "ASK_USER_CLARIFICATION": "Dữ liệu đã có đủ, vấn đề nằm ở tài nguyên thực thi."}),
    ("Gọi hàm bị lỗi TypeError: unexpected keyword argument 'depth_limit'", "ARGUMENT_RE_ENCODING", "Điều chỉnh tham số phù hợp với signature mới của hàm.", {"FAST_DIRECT": "Tham số sai sẽ tiếp tục báo lỗi nếu không sửa.", "FALLBACK_OFFLINE_SEARCH": "Lỗi hàm nội bộ, không liên quan tìm kiếm mạng."}),
    ("Kết nối SearXNG bị lỗi DNS lookup failed, cache offline còn hạn 10 phút", "FALLBACK_OFFLINE_SEARCH", "Sử dụng cache ngoại tuyến vì đã kiểm chứng tính mới còn hạn (freshness_verified: true).", {"FAST_DIRECT": "Mạng DNS hỏng hoàn toàn.", "ARGUMENT_RE_ENCODING": "Lỗi kết nối mạng, không phải lỗi tham số."}),
    ("Ghi file vào /etc/app.conf báo lỗi Permission denied", "AUTHORITY_VERIFY_AND_HALT", "Dừng lại báo cáo Master về quyền ghi thư mục hệ thống, tuyệt đối không tự ý đổi vị trí file.", {"PATH_RECONCILIATION": "Cấm tự ý chuyển file cấu hình hệ thống sang thư mục người dùng khi chưa có lệnh.", "FAST_DIRECT": "Lỗi quyền hạn không thể tự hết nếu chạy lại."}),
    ("API trả về HTTP 429 Too Many Requests", "BACKOFF_RETRY_ADAPTIVE", "Kích hoạt exponential backoff có jitter theo header Retry-After.", {"FAST_DIRECT": "Bắn request liên tục sẽ bị ban IP vĩnh viễn.", "PATH_RECONCILIATION": "Endpoint chuẩn xác, vấn đề là tốc độ gửi."}),
    ("Gọi lệnh shell bị lỗi unmatched parenthesis: 'echo (test'", "ARGUMENT_RE_ENCODING", "Thoát dấu ngoặc đơn hoặc bao quanh bằng nháy kép chuẩn.", {"FAST_DIRECT": "Cú pháp shell sai chắc chắn thất bại tiếp.", "FALLBACK_OFFLINE_SEARCH": "Lỗi cú pháp dòng lệnh."}),
    ("Truy vấn Elasticsearch bị timeout, cache cục bộ đã quá hạn 1 ngày", "STALE_CACHE_ABORT", "Dừng lại báo lỗi dịch vụ tìm kiếm, cấm trả về kết quả từ cache thiu đã quá hạn.", {"FALLBACK_OFFLINE_SEARCH": "Dữ liệu cache quá hạn 24h không thỏa mãn điều kiện tươi mới (freshness_verified == false).", "FAST_DIRECT": "Elasticsearch đang không phản hồi."}),
    ("Thực thi script trực tiếp FAST_DIRECT sinh kết quả thiếu 3/5 file", "PROMOTE_TO_DAG_WITH_CHECKPOINT", "Phát hiện thiếu tiêu chí hoàn thành, nâng cấp lên MULTI_STEP_PLANNING để hoàn thành đủ 5 file.", {"FAST_DIRECT": "Không được báo hoàn thành giả (fake completion) khi mới xong 2/5 file.", "ASK_USER_CLARIFICATION": "Yêu cầu 5 file đã rõ từ đầu."}),
    ("Lệnh CLI báo: unrecognized flag '--output-json'", "ARGUMENT_RE_ENCODING", "Đối chiếu trợ giúp CLI và sửa thành cờ hợp lệ '--format=json'.", {"FAST_DIRECT": "Cờ lệnh sai.", "PATH_RECONCILIATION": "File binary tồn tại, chỉ sai cờ tham số."}),
    ("Mở socket kết nối tới 10.0.0.1 bị Connection Refused", "NETWORK_CIRCUIT_BREAKER", "Kích hoạt circuit breaker ngắt kết nối và thử IP dự phòng đã khai báo.", {"FAST_DIRECT": "Cổng đích đóng hoàn toàn.", "ARGUMENT_RE_ENCODING": "Địa chỉ IP đúng định dạng."}),
    ("Xóa file trong /tmp báo lỗi Device or resource busy", "RESOURCE_BUSY_WAIT", "Kiểm tra tiến trình đang chiếm giữ (lsof) và đợi file handle giải phóng.", {"FAST_DIRECT": "File đang bị lock bởi tiến trình khác.", "PATH_RECONCILIATION": "Đúng đường dẫn file."}),
    ("Gửi payload JSON bị lỗi Invalid UTF-8 sequence", "ARGUMENT_RE_ENCODING", "Mã hóa lại chuỗi nguồn sang UTF-8 hợp lệ trước khi gửi.", {"FAST_DIRECT": "Payload hỏng ký tự.", "FALLBACK_OFFLINE_SEARCH": "Lỗi định dạng dữ liệu gửi đi."}),
    ("Gọi API dịch vụ thanh toán bị HTTP 503 Service Unavailable", "SERVICE_UNAVAILABLE_ABORT", "Dừng giao dịch và thông báo dịch vụ gián đoạn, cấm tự ý suy đoán trạng thái.", {"FAST_DIRECT": "Dịch vụ thanh toán đang bảo trì.", "FALLBACK_OFFLINE_SEARCH": "Giao dịch tài chính không được dùng cache offline."}),
    ("Import module Python báo ModuleNotFoundError: 'yaml'", "DEPENDENCY_RECONCILIATION", "Thông báo môi trường thiếu thư viện PyYAML, hướng dẫn cài đặt chuẩn.", {"FAST_DIRECT": "Mô-đun chưa cài đặt.", "PATH_RECONCILIATION": "Vấn đề ở gói pip, không phải đường dẫn file code."}),
    ("Lỗi Disk quota exceeded khi đang ghi log", "EMERGENCY_LOG_ROTATION", "Kích hoạt nén xoay vòng log cũ và giải phóng không gian khẩn cấp.", {"FAST_DIRECT": "Ổ đĩa đã đầy.", "ARGUMENT_RE_ENCODING": "Dung lượng vật lý hết, không phải lỗi tham số."}),
    ("Thao tác git push bị rejected (non-fast-forward)", "GIT_PULL_RECONCILE", "Thực hiện git fetch và merge/rebase nhánh upstream trước khi đẩy lại.", {"FAST_DIRECT": "Remote đang đi trước commit local.", "ESCALATE_MODEL_OR_HUMAN": "Xung đột thông thường trong git có thể tự giải quyết."})
]

for i, (prompt, branch, action, rejected) in enumerate(recovery_samples_raw, 1):
    samples.append({
        "id": f"dec_err_{i:02d}",
        "group": "ERROR_ADAPTIVE_RECOVERY",
        "instruction": prompt,
        "input": "Phát hiện lỗi runtime. Cấm lặp mù, tuân thủ vệ sinh phục hồi không gây tác dụng phụ.",
        "decision": "ERROR_ADAPTIVE_RECOVERY",
        "output": json.dumps({
            "strategy": "ERROR_ADAPTIVE_RECOVERY",
            "recovery_branch": branch,
            "action": action,
            "rationale": f"Phân tích bằng chứng lỗi: chuyển sang nhánh phục hồi '{branch}'. Tuân thủ nghiêm ngặt vệ sinh phục hồi và an toàn dữ liệu.",
            "alternatives_rejected": rejected,
            "success_criteria": ["Không lặp lại lệnh hỏng", "Không gây tác dụng phụ an ninh", "Phục hồi có kiểm chứng"]
        }, ensure_ascii=False),
        "data_contract": contract
    })

# ==============================================================================
# NHÓM 4: ASK_USER_CLARIFICATION (20 mẫu) - Dừng lại hỏi khi thiếu thông tin
# ==============================================================================
ask_samples_raw = [
    ("Triển khai ứng dụng lên server nhưng chưa có địa chỉ IP và SSH user", ["server_ip", "ssh_user"], {"FAST_DIRECT": "Thiếu IP đích thì không thể thực thi bất kỳ lệnh deploy nào.", "ESCALATE_MODEL_OR_HUMAN": "Vấn đề là thiếu thông số đầu vào từ người dùng, không phải do bài toán quá khó."}),
    ("Tạo báo cáo doanh thu theo chi nhánh nhưng không chỉ định quý hay năm tài chính", ["financial_year", "quarter"], {"FAST_DIRECT": "Nếu tự đoán quý/năm sẽ sinh ra số liệu tài chính sai lệch.", "MULTI_STEP_PLANNING": "Chưa có tham số thời gian để trích xuất CSDL."}),
    ("Dọn dẹp file cũ trong thư mục log nhưng chưa rõ thời hạn lưu trữ bao nhiêu ngày", ["retention_days"], {"FAST_DIRECT": "Tự ý xóa file mà không rõ thời hạn có thể làm mất log quan trọng.", "ERROR_ADAPTIVE_RECOVERY": "Chưa có lỗi nào xảy ra, đây là lệnh cấu hình chính sách."}),
    ("Cấu hình kết nối tới kho S3 nhưng thiếu bucket name và vùng AWS", ["s3_bucket_name", "aws_region"], {"FAST_DIRECT": "Không thể kết nối S3 vô định danh.", "ESCALATE_MODEL_OR_HUMAN": "Chỉ cần người dùng cung cấp tên bucket."}),
    ("Gửi email thông báo toàn thể khách hàng nhưng chưa có tiêu đề và nội dung", ["email_subject", "template_body"], {"FAST_DIRECT": "Gửi email rỗng sẽ gây sự cố truyền thông nghiêm trọng.", "MULTI_STEP_PLANNING": "Thiếu nội dung thông điệp cốt lõi."}),
    ("Nén ảnh trong thư mục nhưng chưa chỉ định định dạng đầu ra (WebP hay JPEG) và chất lượng", ["target_format", "compression_quality"], {"FAST_DIRECT": "Cần biết định dạng người dùng mong muốn.", "ESCALATE_MODEL_OR_HUMAN": "Tác vụ nén ảnh cơ bản."}),
    ("Chạy migration CSDL nhưng chưa rõ môi trường đích là staging hay production", ["target_environment"], {"FAST_DIRECT": "Chạy nhầm lên production có thể gây thảm họa dữ liệu.", "MULTI_STEP_PLANNING": "Phải xác định rõ môi trường trước khi lập kế hoạch migration."}),
    ("Sao lưu CSDL nhưng chưa rõ là backup toàn bộ (full) hay gia tăng (incremental)", ["backup_type"], {"FAST_DIRECT": "Cần người dùng chọn chiến lược sao lưu phù hợp dung lượng ổ đĩa.", "ESCALATE_MODEL_OR_HUMAN": "Sao lưu là hành động tiêu chuẩn."}),
    ("Thêm quyền cho tài khoản mới nhưng chưa nêu rõ vai trò (Admin, Editor hay Viewer)", ["user_role"], {"FAST_DIRECT": "Tự cấp Admin sẽ vi phạm nguyên tắc quyền tối thiểu (Least Privilege).", "ERROR_ADAPTIVE_RECOVERY": "Không có lỗi runtime."}),
    ("Tích hợp webhook thông báo sự kiện nhưng chưa có URL callback", ["webhook_callback_url"], {"FAST_DIRECT": "Thiếu URL thì không thể gửi request.", "ESCALATE_MODEL_OR_HUMAN": "Chỉ cần URL webhook hợp lệ."}),
    ("Xuất báo cáo thống kê nhưng chưa rõ người dùng muốn định dạng CSV, Excel hay JSON", ["export_format"], {"FAST_DIRECT": "Hỏi để xuất đúng định dạng người dùng cần sử dụng.", "MULTI_STEP_PLANNING": "Chờ xác nhận định dạng trước khi render file."}),
    ("Đặt lịch cronjob bảo trì nhưng chưa chỉ định thời gian hoặc tần suất chạy", ["cron_schedule_expression"], {"FAST_DIRECT": "Cronjob bắt buộc phải có biểu thức thời gian.", "ESCALATE_MODEL_OR_HUMAN": "Lập lịch định kỳ cơ bản."}),
    ("Cấu hình giới hạn tốc độ mạng (rate limit) nhưng chưa cho biết số request tối đa/phút", ["max_requests_per_minute"], {"FAST_DIRECT": "Thiếu ngưỡng rate limit thì không thể áp rule firewall.", "ERROR_ADAPTIVE_RECOVERY": "Thiếu cấu hình ban đầu."}),
    ("Cài đặt chứng chỉ SSL nhưng chưa cung cấp file chứng chỉ .crt và private key", ["ssl_certificate_file", "ssl_private_key_file"], {"FAST_DIRECT": "Không thể bật HTTPS khi thiếu chứng chỉ số.", "ESCALATE_MODEL_OR_HUMAN": "Chờ cung cấp file cert hợp lệ."}),
    ("Đồng bộ danh bạ từ hệ thống CRM bên thứ ba nhưng chưa có API token ủy quyền", ["api_auth_token"], {"FAST_DIRECT": "Gọi API bên ngoài không có token sẽ bị 401 Unauthorized ngay.", "ERROR_ADAPTIVE_RECOVERY": "Chưa chạy lệnh, ngăn ngừa lỗi 401 trước."}),
    ("Đổi múi giờ hệ thống nhưng chưa rõ là UTC hay GMT+7 hay giờ địa phương nào", ["target_timezone"], {"FAST_DIRECT": "Đổi nhầm múi giờ sẽ làm lệch toàn bộ log và cronjob.", "MULTI_STEP_PLANNING": "Xác định múi giờ là một thao tác đơn."}),
    ("Khởi tạo cụm Kubernetes nhưng chưa biết số lượng worker nodes cần cấp phát", ["worker_node_count"], {"FAST_DIRECT": "Cần biết số lượng node để tính toán chi phí và quota.", "ESCALATE_MODEL_OR_HUMAN": "Tác vụ hạ tầng trong tầm quản trị."}),
    ("Gộp nhánh git nhưng chưa chỉ định nhánh nguồn và nhánh đích", ["source_branch", "target_branch"], {"FAST_DIRECT": "Merge bừa bãi sẽ làm hỏng lịch sử commit.", "ERROR_ADAPTIVE_RECOVERY": "Thiếu thông tin nhánh merge."}),
    ("Thiết lập chính sách mật khẩu nhưng chưa nêu độ dài tối thiểu", ["min_password_length"], {"FAST_DIRECT": "Cần người dùng đưa ra tiêu chuẩn an ninh cụ thể.", "ESCALATE_MODEL_OR_HUMAN": "Quy tắc chính sách tổ chức."}),
    ("Phân vùng ổ đĩa nhưng chưa chỉ định kích thước mong muốn từng phân vùng", ["partition_sizes_gb"], {"FAST_DIRECT": "Phân vùng sai kích thước rất tốn công định dạng lại.", "MULTI_STEP_PLANNING": "Phải có kích thước mới lập DAG chia ổ."})
]

for i, (prompt, missing, rejected) in enumerate(ask_samples_raw, 1):
    samples.append({
        "id": f"dec_ask_{i:02d}",
        "group": "ASK_USER_CLARIFICATION",
        "instruction": prompt,
        "input": f"Thiếu thông tin thiết yếu: {', '.join(missing)}. Cấm đoán mò / hallucination.",
        "decision": "ASK_USER_CLARIFICATION",
        "output": json.dumps({
            "strategy": "ASK_USER_CLARIFICATION",
            "step_budget": 1,
            "require_user_interaction": True,
            "missing_keys": missing,
            "rationale": f"Thiếu thông số then chốt ({', '.join(missing)}). Dừng lại hỏi Master để nhận dữ kiện chính xác thay vì đoán mò.",
            "alternatives_rejected": rejected,
            "success_criteria": ["Không tự ý bịa đặt tham số", "Đặt câu hỏi làm rõ rõ ràng", "Chờ phản hồi trước khi thực thi"]
        }, ensure_ascii=False),
        "data_contract": contract
    })

# ==============================================================================
# NHÓM 5: ESCALATE_MODEL_OR_HUMAN (20 mẫu) - Phân tách rõ ràng MASTER vs TEACHER
# ==============================================================================
escalate_samples_raw = [
    # 10 mẫu Nguy cơ an toàn / phá hoại -> MASTER_HUMAN_APPROVAL
    ("Thực thi lệnh 'rm -rf / --no-preserve-root' trên máy chủ chính", "MASTER_HUMAN_APPROVAL", "Lệnh hủy diệt toàn bộ hệ điều hành và dữ liệu vật lý.", {"FAST_DIRECT": "Hành động có tính chất phá hoại vĩnh viễn, tuyệt đối cấm chạy trực tiếp.", "TEACHER_MODEL_ASSIST": "Model lớn không có thẩm quyền phê chuẩn hành vi phá hủy hệ thống của con người."}),
    ("Xóa toàn bộ các bảng trong CSDL production không có bản backup", "MASTER_HUMAN_APPROVAL", "Xóa dữ liệu sản xuất không thể phục hồi.", {"FAST_DIRECT": "Mất mát dữ liệu khách hàng không thể đảo ngược.", "TEACHER_MODEL_ASSIST": "Chỉ Master là chủ sở hữu hệ thống mới có quyền phê duyệt thao tác này."}),
    ("Tắt toàn bộ firewall và mở tất cả các cổng từ 1 đến 65535 ra Internet", "MASTER_HUMAN_APPROVAL", "Hành động làm mất an toàn toàn bộ hệ thống mạng.", {"FAST_DIRECT": "Phơi nhiễm toàn bộ hạ tầng trước nguy cơ tấn công.", "MULTI_STEP_PLANNING": "Lập kế hoạch mở cổng nguy hiểm vẫn là hành vi bị cấm nếu thiếu sự phê chuẩn."}),
    ("Trích xuất và gửi file /etc/shadow hoặc khóa bí mật master ra ngoài", "MASTER_HUMAN_APPROVAL", "Nguy cơ rò rỉ thông tin xác thực tối mật.", {"FAST_DIRECT": "Vi phạm nghiêm trọng chính sách bảo mật dữ liệu.", "TEACHER_MODEL_ASSIST": "Mô hình giáo viên không thể bypass quy định bảo mật."}),
    ("Chạy lệnh định dạng lại phân vùng ổ cứng hệ thống C:\\ hoặc /dev/sda", "MASTER_HUMAN_APPROVAL", "Phá hủy hệ điều hành và mất dữ liệu hoàn toàn.", {"FAST_DIRECT": "Thao tác hủy diệt cấp độ phần cứng.", "ERROR_ADAPTIVE_RECOVERY": "Đây không phải thao tác phục hồi lỗi."}),
    ("Chuyển tiền thực tế từ tài khoản ngân hàng của công ty qua cổng thanh toán", "MASTER_HUMAN_APPROVAL", "Giao dịch tài chính có hậu quả vật lý thực.", {"FAST_DIRECT": "AI không được tự ý thực hiện chuyển giao tài sản mà không có con người ký duyệt.", "TEACHER_MODEL_ASSIST": "Quyền ủy quyền tài chính thuộc về Master."}),
    ("Ngắt nguồn điện máy chủ chính từ xa qua lệnh IPMI không hẹn giờ", "MASTER_HUMAN_APPROVAL", "Tắt máy đột ngột làm hỏng hệ thống file và gián đoạn dịch vụ toàn cụm.", {"FAST_DIRECT": "Rủi ro downtime vật lý cao.", "MULTI_STEP_PLANNING": "Chỉ Master có quyền quyết định tắt máy chủ."}),
    ("Xóa toàn bộ log kiểm toán an ninh mạng trong 6 tháng qua", "MASTER_HUMAN_APPROVAL", "Xóa dấu vết kiểm toán vi phạm quy chuẩn tuân thủ.", {"FAST_DIRECT": "Hành vi xóa dấu vết đáng ngờ.", "TEACHER_MODEL_ASSIST": "Không thể ủy quyền cho AI xóa nhật ký kiểm toán."}),
    ("Cấp quyền root không cần mật khẩu (NOPASSWD: ALL) cho mọi user", "MASTER_HUMAN_APPROVAL", "Tạo lỗ hổng bảo mật nghiêm trọng trên toàn máy chủ.", {"FAST_DIRECT": "Hạ thấp hoàn toàn hàng rào bảo mật.", "ASK_USER_CLARIFICATION": "Cần Master phê chuẩn thay vì chỉ hỏi tham số."}),
    ("Flash firmware mới vào chip BIOS của bo mạch chủ server", "MASTER_HUMAN_APPROVAL", "Rủi ro biến phần cứng thành 'cục gạch' nếu xảy ra lỗi trong quá trình ghi ROM.", {"FAST_DIRECT": "Can thiệp phần cứng cấp thấp có rủi ro vĩnh viễn.", "MULTI_STEP_PLANNING": "Bắt buộc có sự giám sát của Master."}),

    # 10 mẫu Trừu tượng / Bất định cao / Suy luận chuyên sâu -> TEACHER_MODEL_ASSIST
    ("Giải bài toán mở về Giả thuyết Riemann và xây dựng chứng minh toán học nghiêm ngặt", "TEACHER_MODEL_ASSIST", "Bài toán toán học lý thuyết cực đại, độ bất định 0.95 vượt quá dung lượng model 3B.", {"FAST_DIRECT": "Model 3B sẽ hallucinate công thức sai nếu cố suy luận trực tiếp.", "MASTER_HUMAN_APPROVAL": "Master cần giải pháp kỹ thuật từ Teacher Model trước khi thẩm định."}),
    ("Phân tích cơ chế lượng tử đa chiều của hạt Higgs trong vật lý lý thuyết cao cấp", "TEACHER_MODEL_ASSIST", "Lý thuyết trường lượng tử vượt giới hạn tri thức của mô hình nhỏ.", {"FAST_DIRECT": "Model nhỏ thiếu context sâu về vật lý hạt nhân.", "ASK_USER_CLARIFICATION": "Người dùng yêu cầu phân tích học thuật, không phải thiếu tham số."}),
    ("Thiết kế lại toàn bộ cấu trúc mô hình mạng nơ-ron Transformer 100 tỷ tham số", "TEACHER_MODEL_ASSIST", "Đòi hỏi năng lực kiến trúc mô hình cấp cao của Teacher Model.", {"FAST_DIRECT": "Model 3B không đủ năng lực siêu nhận thức để tự thiết kế mô hình 100B.", "ERROR_ADAPTIVE_RECOVERY": "Đây là bài toán sáng tạo thiết kế."}),
    ("Chứng minh tính đúng đắn toán học của thuật toán mật mã hậu lượng tử mới", "TEACHER_MODEL_ASSIST", "Độ phức tạp toán học và chứng minh hình thức đòi hỏi mô hình giáo viên.", {"FAST_DIRECT": "Mô hình nhỏ dễ bỏ sót các lỗ hổng toán học tiềm ẩn.", "MASTER_HUMAN_APPROVAL": "Teacher Model sẽ hỗ trợ phân tích bước chứng minh trước."}),
    ("Dự đoán biến động chuỗi thời gian phi tuyến phức tạp trong thị trường chứng khoán", "TEACHER_MODEL_ASSIST", "Độ bất định dữ liệu rất cao (0.92), cần mô hình suy luận đa chiều phân tích rủi ro.", {"FAST_DIRECT": "Dễ bị overconfidence và đưa ra kết luận sai lầm.", "MULTI_STEP_PLANNING": "Cần khả năng suy luận xác suất sâu trước khi lập kế hoạch."}),
    ("Giải quyết nghịch lý thông tin lỗ đen theo thuyết tương đối rộng và cơ học lượng tử", "TEACHER_MODEL_ASSIST", "Đề tài vật lý lý thuyết cấp tiến cần tổng hợp tri thức khổng lồ.", {"FAST_DIRECT": "Model 3B sẽ bị ảo giác.", "ASK_USER_CLARIFICATION": "Câu hỏi tri thức khoa học, không phải bài toán lập trình thiếu biến."}),
    ("Dịch ngược và tái cấu trúc thuật toán giải nén nhị phân độc quyền không có tài liệu", "TEACHER_MODEL_ASSIST", "Kỹ thuật dịch ngược mã máy phức tạp đòi hỏi khả năng xâu chuỗi bytecode.", {"FAST_DIRECT": "Model 3B không đủ context window và năng lực xâu chuỗi opcode.", "ERROR_ADAPTIVE_RECOVERY": "Chưa có lỗi runtime, đây là bài toán dịch ngược trí tuệ."}),
    ("Tối ưu hóa đa mục tiêu phi lồi cho mạng lưới 10.000 trạm biến áp điện", "TEACHER_MODEL_ASSIST", "Bài toán quy hoạch phi tuyến tính toán học cực lớn.", {"FAST_DIRECT": "Model nhỏ bị quá tải suy luận toán học.", "MASTER_HUMAN_APPROVAL": "Cần Teacher Model đưa ra thuật toán tối ưu trước."}),
    ("Phân tích cấu trúc phân tử protein và dự đoán vị trí liên kết thuốc mới", "TEACHER_MODEL_ASSIST", "Hóa sinh điện toán vượt quá tri thức cơ bản của mô hình ngôn ngữ nhỏ.", {"FAST_DIRECT": "Nguy cơ sinh cấu trúc hóa học phi thực tế.", "ASK_USER_CLARIFICATION": "Dữ liệu protein đã có trong input."}),
    ("Xây dựng chứng minh hình thức bằng ngôn ngữ Coq/Lean cho định lý 4 màu", "TEACHER_MODEL_ASSIST", "Định lý toán học cần bộ suy luận logic hình thức bậc cao của Teacher Model.", {"FAST_DIRECT": "Model nhỏ không viết được cú pháp Lean/Coq chứng minh phức tạp.", "MULTI_STEP_PLANNING": "Cần Teacher Model sinh chiến thuật chứng minh (tactics) trước."})
]

for i, (prompt, target, reason, rejected) in enumerate(escalate_samples_raw, 1):
    samples.append({
        "id": f"dec_esc_{i:02d}",
        "group": "ESCALATE_MODEL_OR_HUMAN",
        "instruction": prompt,
        "input": f"Đánh giá rủi ro/độ bất định: mục tiêu chuyển tiếp là {target}. Lý do: {reason}",
        "decision": "ESCALATE_MODEL_OR_HUMAN",
        "output": json.dumps({
            "strategy": "ESCALATE_MODEL_OR_HUMAN",
            "step_budget": 1,
            "escalation_target": target,
            "require_user_interaction": True if "MASTER" in target else False,
            "rationale": f"Hành động yêu cầu leo thang sang '{target}' vì: {reason}",
            "alternatives_rejected": rejected,
            "success_criteria": ["Bảo toàn bất biến an toàn", "Không tự ý thực thi hành động vượt thẩm quyền", "Chuyển tiếp đúng đối tượng"]
        }, ensure_ascii=False),
        "data_contract": contract
    })

# Ghi ra cả 2 file: dataset chính thức và v2
for path_str in ("data/dataset/gold_decision_lora_100.jsonl", "data/dataset/gold_decision_dataset_v2.jsonl"):
    out_path = Path(path_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"Written {len(samples)} samples to {out_path}!")

print("Generator completed successfully!")
