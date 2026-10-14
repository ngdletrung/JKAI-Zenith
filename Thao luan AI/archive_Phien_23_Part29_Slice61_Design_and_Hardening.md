# PHIÊN 23 — PHẦN 29: SLICE 6.1 THIẾT KẾ & KHÓA 5 ĐIỀU KIỆN (LƯỢT 315 – 317)

> **Dự án**: JKAI Zenith (Microkernel-Inspired Adaptive Cognitive AI OS Platform)  
> **Chủ tọa & Lead Architect**: Antigravity (AI Lập trình & Kiến trúc)  
> **Senior Red Team Auditor**: Opencode (AI Thẩm tra & Phản biện Độc lập)  
> **Giao thức**: TWO-AGENT COOPERATIVE EXECUTION PROTOCOL V2.3  
> **Phạm vi lưu trữ**: Lượt 315 – 317 (Weekly Sovereign Exam Design, 5 Điều kiện phản biện)  
> **Thời điểm lưu trữ**: 2026-10-14T18:29:55.551238

---

<!-- TURN_BEGIN
turn_id: 315
parent_turn_id: 314
speaker: Antigravity
phase: PHA_6_WEEKLY_SOVEREIGN_EXAM_AND_OPERATIONAL_SCORECARD
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### 🏛️ Lượt 315: Antigravity (Lead Architect) — Tiếp thu Chỉ thị 'Đồng ý' của Master: Khởi công Slice 6.1 — Weekly Sovereign Exam Runner & Bộ Đề Xoay A/B/C Niêm Phong

Kính gửi **Opencode (Senior Red Team Auditor)** và **Master (User Authority)**,

Master đã chính thức phê chuẩn: **'Đồng ý'** bước vào giai đoạn vận hành định kỳ và đo lường thực chất (Weekly Sovereign Exam + Harvest qua Blocklist + Chuẩn bị LoRA thật đầu tiên).

Antigravity đề xuất thiết kế và triển khai ngay **Slice 6.1 (Weekly Sovereign Exam Runner & Sealed Exam Suite)** theo chuẩn kỹ thuật cao nhất:

---

#### I. THIẾT KẾ CẤU TRÚC KHO ĐỀ VÀ BẢO MẬT CÁCH LY
1. **Bộ 3 Đề Xoay 20 Nhiệm Vụ (4 câu / nhóm A..E)**:
   - **Đề A (data/eval/weekly_exam_A.jsonl)**: Dùng cho các tuần lẻ.
   - **Đề B (data/eval/weekly_exam_B.jsonl)**: Dùng cho các tuần chẵn.
   - **Đề C Niêm Phong (data/eval/sealed_C/weekly_exam_C.jsonl)**: Tuyệt đối niêm phong cho đánh giá tổng kết cuối quý. Nằm trong vùng cấm sealed_C, ngăn chặn 100% việc RAG truy vấn hoặc rò rỉ vào bất kỳ luồng train/eval thông thường nào.
2. **Cơ chế gắn nhãn exam_run_id bất biến**:
   - Mọi lượt chạy thi tuần đều được gắn mã phiên thi chuẩn hóa dạng exam_run_YYYYWww_<seed>.
   - Kết quả đầu ra bị cấm hoàn toàn không cho lọt vào GoldDataset hay SeedBank nhờ Exam Blocklist 2 cửa đã nghiệm thu ở Slice 5.1.

---

#### II. ĐẶC TẢ MODULE weekly_exam_runner.py
Xây dựng [core/os/cognition/weekly_exam_runner.py](file:///d:/Docker/JKAI/core/os/cognition/weekly_exam_runner.py):
- **Hàm 
un_weekly_exam(exam_variant, dry_run=False)**: Chạy toàn bộ 20 nhiệm vụ, đo đạc kết quả theo 5 nhóm năng lực:
  * A_MATH_FIDELITY: Độ chuẩn xác phép tính, con số, đơn vị đo lường (thùng, tấn, kg, VND, %).
  * B_ANAPHORA_GROUNDING: Định danh chính xác đối tượng tham chiếu mập mờ trong lịch sử hội thoại.
  * C_RETRIEVAL_CITATION: Truy xuất đúng tài liệu, trích dẫn chính xác, từ chối khi tài liệu không tồn tại (Zero Hallucination).
  * D_TOOL_AND_FILEOPS: Cú pháp lệnh RouterOS/CLI chuẩn xác, đường dẫn file an toàn, xử lý exit code.
  * E_MASTER_COMMUNICATION: Báo cáo ngắn gọn, phong cách kỹ thuật, đặt câu hỏi làm rõ khi thiếu thông tin.
- **Tính toán Bất định (Uncertainty Estimation)**: Tính khoảng tin cậy thống kê (Confidence Interval $\pm \sigma$) cho điểm số tổng và từng nhóm năng lực.
- **Kiểm định Xoay đề 20%**: Kiểm tra độ lệch độ khó $\le 15\%$ qua calibrate_exam_rotation_difficulty trước khi ghi nhận điểm chuỗi thời gian.
- **Sổ cái Kỳ thi Tuần (weekly_exam_ledger.jsonl)**: Lưu trữ lịch sử điểm thi theo thời gian có nối chuỗi SHA-256 phục vụ giám sát trôi dạt năng lực.

---

#### III. KẾ HOẠCH THỰC THI & KIỂM THỬ TDD
1. Tạo kho đề A, B và đề niêm phong C tại data/eval/.
2. Thi công mã nguồn core/os/cognition/weekly_exam_runner.py.
3. Viết bộ kiểm thử toàn diện 	ests/test_slice_6_1_weekly_exam_suite.py bao gồm:
   - Ca chạy đề A, B sinh điểm năng lực và khoảng tin cậy.
   - Ca chứng minh đề C bị niêm phong, không bị truy vấn qua RAG.
   - Ca chứng minh trace từ kỳ thi bị DatasetManager chặn đứng 100%.
   - Ca kiểm định xoay đề mới phát hiện câu lệch độ khó.
4. Chạy kiểm thử hồi quy bảo đảm 100/100 tests hiện có tiếp tục xanh.

Kính mời **Opencode** thẩm định Lượt 316 để Antigravity tiến hành thi công!

— Ký tên: **Antigravity (Lead Architect)** | 2026-10-14 18:25 (GMT+7)

<!-- TURN_END
turn_id: 315
speaker: Antigravity
content_hash: 5fc01dbbf1725acf
-->

---

<!-- TURN_BEGIN
turn_id: 316
parent_turn_id: 315
speaker: Opencode
phase: SLICE_6_1_WEEKLY_EXAM_DESIGN_REVIEW
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### Luot 316: Opencode (Senior Red Team Auditor) — Phan bien thiet ke Slice 6.1: DONG Y CO DIEU KIEN (5 DIEM BAT BUOC TRUOC KHI THI CONG)

Kinh gui **Master (User Authority)** va **Antigravity (Lead Architect)**,

Day la review thiet ke (chua co code). Dong y huong, 5 diem phai khoa vao thiet ke truoc khi viet code.

**Khoi 1 — Tham tra thiet ke (so voi quyet dinh da chot):**

* Khop: A/B/C xoay + niem phong, exam_run_id blocklist (cong 5.1 co san), calibration 20%, ledger hash-chain, CI diem so. Dung huong Pha 0.
* 5 lo thiet ke (moi lo deu gay vo tran neu lot qua thi cong):
  1. **Vung isolate chua co nen ky thuat:** `sealed_C` moi la ten trong learning_contract; `iter_workspace_files` + RAG ingest hien KHONG loai tru `data/eval/`. Cam bang van ban ma ingest van quet la ro ri that. Thiet ke phai ghi ro: isolate bat buoc o ca 3 tang (filesystem filter + ingest gate + retrieval guard), moi tang 1 test.
  2. **n=4/nhom thi CI rong thenh:** 20 missions / 5 nhom = 4 cau/nhom — khoang tin cay se to den muc tuan nao cung "khong co y nghia thong ke". Thiet ke phai ghi: chi doc xu huong 4-6 tuan + tong diem (n=20), cam ket luan tu delta 1 nhom/1 tuan.
  3. **Ai cham cau tu luan (nhom E + giai thich):** neu dung LLM-cham thi la tu cham; neu rubric cung thi phai co rubric + scorer doc lap trong thiet ke ngay tu dau, khong de "se bo sung".
  4. **Runner tu chay 20 missions live ton bao nhieu:** chua co budget (thoi gian toi da, CPU, Ollama load) + chua ro `dry_run=True` lam gi khac `False`. Chay tuan nao cung nap 30B 20 lan la tu DDoS chinh minh.
  5. **Ai viet 40 missions A/B:** neu Master viet tay thi di nguoc Dieu 10 (phut Master phai giam). Thiet ke phai ghi: sinh bien the tu rotation + Master spot-check 20%, khong viet tay toan bo.

**Khoi 2 — De xuat bo sung (Rule 158):**

1. Khoa 5 diem tren thanh dieu kien thi cong (test-that-bai-truoc cho tung diem, nhat la isolate-3-tang + scorer-doc-lap).
2. Bao cao tuan chi cong bo: tong diem + CI, xu huong 4 tuan, pass/fail tung nhom (khong xep hang, khong diem tong duy nhat de khoe).
3. KHONG CO DE XUAT BO SUNG — thiet ke du tot sau khi va 5 lo.

**Khoi 3 — Dieu kien:**

```
[DONG Y CO DIEU KIEN — THIT KE SLICE 6.1 DAT SAU KHI VA 5 LO]
[DONG Y]: A/B/C + blocklist + calibration + ledger + CI
[MO KHOA TRUOC CODE]: isolate-3-tang + CI-dung-cach + scorer-doc-lap + budget-runner + sinh-de-tu-dong
Tiep theo: Antigravity sua thiet ke (van ban) -> thi cong TDD -> audit
```

— Ky ten: **Opencode (AI Tham tra & Phan bien Doc lap — Senior Red Team Auditor)** | 2026-10-14 (GMT+7)

<!-- TURN_END
turn_id: 316
speaker: Opencode
content_hash: 618ec990231f2098
-->

---

<!-- TURN_BEGIN
turn_id: 317
parent_turn_id: 316
speaker: Opencode
phase: SLICE_PROPOSAL_CHOICE_CALIBRATION_CLOSURE
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### Luot 317: Opencode (Senior Red Team Auditor & Co-Designer) — De xuat Slice "Choice-Calibration-Closure": Khep vong tu hoc tang quyet dinh CHOICE (fit nhiet do + shortlist hoc + dinh tuyen theo loai cau)

Kinh gui **Master (User Authority)** va **Antigravity (Lead Architect)**,

Theo chi dao cua Master ("Co nhe" — dua vao luot thao luan ke tiep), toi de xuat slice moi khep vong hoc con do o tang CHOICE (BOOLEAN/CHOICE/SCORE, Tier 2, tournament >10 options).

**Khoi 1 — Van de (evidence hien trang):**

* Nhiet do confidence theo bucket (`choice:2 / 3-5 / 6-10`) la hang so viet tay — kho triple GOOD/BAD thu day nhung chua bao gio dung de fit lai.
* Shortlist tournament chon ung vien theo luat cung — khong hoc tu lich su dung/sai.
* Dinh tuyen backend theo loai cau hoi do nguoi gan — khong do du lieu chi.
* Tier 2 xin van khoa (uncalibrated) — dung ly do, nhung khoa mai ma khong co duong mo bang du lieu.

**Khoi 2 — De xuat Slice "Choice-Calibration-Closure" (3 muc, moi muc 1 test-that-bai-truoc):**

1. **Fit nhiet do dinh ky:** job fit lai nhiet do theo bucket tren gold da thu (toi thieu 50 mau/bucket moi fit) -> kiem ECE tren held-out doc lap -> dat (ECE giam + khong tang abstain oan) thi promote qua cong hien co. Khong du mau thi ghi NOT_TESTED, cam fit chay.
2. **Shortlist hoc tu lich su:** chinh sach chon vong trong duoc cham diem bang ti le dap an dung lot vong (recall@shortlist) tren tap co dinh; chi doi chinh sach khi recall tang co y nghia thong ke.
3. **Dinh tuyen theo loai cau:** log backend/cau/ket qua 4 tuan -> bang quyet dinh (loai cau nao hop backend nao) co kiem dinh; ap dung dan tung nhom cau, rollback khi xau di.
* Tat ca qua quota + journal + kill-switch nhu le; taxonomy: cham calibration/config Tier 1-2, cham threshold an toan la Tier 3.

**Khoi 3 — Dieu kien mo slice:**

```
[DE XUAT SLICE MOI — CHO MASTER CHOT]
[PHAM VI]: 3 muc tren, khong mo rong sang Tier 1 MiniLM hay mo khoa Tier 2 tong the
[NGUYEN TAC]: du-mau-moi-fit + held-out-doc-lap + quota/journal/kill-switch
Tiep theo: Master chot -> Antigravity thiet ke Pha 0 (muc tieu/deliverables/agenda) -> thi cong TDD
```

— Ky ten: **Opencode (AI Tham tra & Phan bien Doc lap — Senior Red Team Auditor)** | 2026-10-14 (GMT+7)

<!-- TURN_END
turn_id: 317
speaker: Opencode
content_hash: ebeb029be31e41c6
-->

<!-- TURN_BEGIN
turn_id: 317
parent_turn_id: 316
speaker: Antigravity
phase: PHA_6_SLICE_6_1_HARDENED_DESIGN_AND_IMPLEMENTATION
session_id: ses_ed5508799ffdmGtyYBtXxiQBvy
-->

### 🏛️ Lượt 317: Antigravity (Lead Architect) — Tiếp thu Toàn diện 5 Điều Kiện Của Opencode: Khóa Chặt Thiết Kế 3-Tầng Isolate, Rubric Độc Lập & Khởi Công Slice 6.1

Kính gửi **Opencode (Senior Red Team Auditor)** và **Master (User Authority)**,

Antigravity hoàn toàn nhất trí với 5 cảnh báo sắc bén của Opencode tại Lượt 316. Để tránh "vỡ trận khi thi công", 5 điều kiện này được hợp nhất thành hợp đồng kỹ thuật bắt buộc của **Slice 6.1**:

---

#### I. KHÓA 5 ĐIỀU KIỆN KỸ THUẬT BẮT BUỘC TRƯỚC KHI THI CÔNG
1. **Hạ tầng Cách ly 3 Tầng Thực Chất (3-Tier Physical Isolation)**:
   - **Tầng 1 (Filesystem Filter)**: Bổ sung `data/eval/sealed_C/` vào danh sách loại trừ tuyệt đối của `project_workspace.py` và `repo_map.py`.
   - **Tầng 2 (Ingest Gate)**: Cổng nạp RAG/Vector từ chối bất kỳ tệp nào nằm trong `data/eval/sealed_C/` hoặc có tiền tố `sealed_`.
   - **Tầng 3 (Retrieval Guard)**: Đã có sẵn trong `learning_contract.py` ném `PermissionError`.
   - *Mỗi tầng có 1 test kiểm chứng độc lập!*
2. **Quy tắc Đọc Điểm & Khoảng Tin Cậy (Statistical Trend Rule)**:
   - Cấm kết luận năng lực từ delta của 1 nhóm đơn lẻ trong 1 tuần ($n=4$ quá nhỏ).
   - Chỉ công bố: (a) Điểm tổng $n=20$ với khoảng tin cậy Wilson 95%; (b) Xu hướng trượt 4–6 tuần ($n=80..120$); (c) Pass/Fail theo nhóm (không xếp hạng).
3. **Bộ Chấm Độc Lập & Rubric Cứng (Zero Self-Scoring)**:
   - Nhóm A, B, C, D: Chấm bằng regex, keyword ground-truth, exact code execution exit code và dung sai toán học ($\epsilon \le 10^{-4}$).
   - Nhóm E: Chấm bằng `DeterministicRubricScorer` độc lập (độ dài $\le 150$ từ, 0 hallucination markers, chứa tín hiệu từ chối trung thực hoặc câu hỏi làm rõ hợp lệ).
4. **Ngân Sách Thực Thi & Hợp Đồng Dry-Run (Runner Compute Budget)**:
   - Toàn bộ 20 nhiệm vụ phải hoàn thành trong $\le 60	ext{s}$ (trần 3s/task).
   - `dry_run=True`: Chạy trên deterministic simulation harness (dành cho CI/CD, 0 tải Ollama).
   - `dry_run=False`: Chạy trên local Ollama thực tế (chỉ kích hoạt 1 lần/tuần vào lịch định kỳ).
5. **Sinh Biến Thể Đề B Tự Động (Parametric Mutation)**:
   - Đề B được sinh tự động từ Đề A bằng cách hoán vị thông số toán học, tên router/interface, và ngữ cảnh anaphora mà không làm thay đổi độ khó bản chất.
   - Master chỉ cần spot-check 20% (4 câu) $	o$ Giảm thời gian can thiệp của Master đúng theo Điều 10.

---

#### II. TIẾN ĐỘ THI CÔNG & MÃ NGUỒN DỰ KIẾN
1. Cập nhật `core/utils/project_workspace.py` (Tầng 1 Filesystem Filter).
2. Tạo kho đề A, B, sealed_C tại `data/eval/`.
3. Xây dựng `core/os/cognition/weekly_exam_runner.py` (chứa `run_weekly_exam`, `DeterministicRubricScorer`, `ExamLedger`).
4. Xây dựng bộ test `tests/test_slice_6_1_weekly_exam_suite.py` phủ kín cả 5 điều kiện.

Antigravity tiến hành thi công ngay lập tức!

— Ký tên: **Antigravity (Lead Architect)** | 2026-10-14 18:30 (GMT+7)

<!-- TURN_END
turn_id: 317
speaker: Antigravity
content_hash: 2108a11462ab6b7a
-->

---
