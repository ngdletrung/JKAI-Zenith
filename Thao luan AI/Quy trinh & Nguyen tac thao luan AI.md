# QUY CHẾ VÀ NGUYÊN TẮC THẢO LUẬN ĐA AI (FAST TWO-AGENT PROTOCOL V3.1)

> **Định danh**: **"Thảo Luận AI V3.1 — Production Ready"** — Giao thức phối hợp và phản biện siêu tốc giữa **Antigravity** (AI Lập trình & Kiến trúc - Builder) và **Opencode** (AI Thẩm tra & Phản biện Độc lập - Red Team) dưới quyền chủ quyền của **Master**.  
> **Triết lý cốt lõi**: **Automation First**, **Zero Over-engineering**, **Tự trị cao độ (Autonomous)**, **Zero-Noise**, **Zero-Junk**.  
> **Tệp SSoT Hiến Pháp**: [`.keyword.md`](file:///d:/Docker/JKAI/.keyword.md) (bản gương đồng bộ [`.keywork.md`](file:///d:/Docker/JKAI/.keywork.md)) — Truy cập trực tiếp qua đường dẫn tệp; chỉ đọc 1 lần duy nhất khi khởi tạo phiên mới (First Contact), tuyệt đối không nhúng lặp lại nội dung.  
> **Ngưỡng Context tối ưu**: **300 dòng / 30 KB** (Trần cứng: **500 dòng / 50 KB** nhằm bảo vệ KV-cache và năng lực suy luận của SLM 3B/4B).

---

## 🏛️ 0. ĐỊNH NGHĨA "MASTER" VÀ PHÂN TẦNG QUYỀN HẠN

1. **Master là ai?**:
   - Master (Người Vận Hành / Human Operator) là **Chủ thể Chủ quyền Tối cao (Supreme Sovereign Authority)** của hệ thống JKAI.
   - Master nắm giữ quyền sinh sát tối thượng đối với mọi phiên làm việc, mã nguồn, kiến trúc và hiến pháp hệ thống.
2. **Thẩm quyền của Master**:
   - **Trọng tài tối cao (Supreme Arbiter)**: Đưa ra phán quyết chung cuộc trong mọi tranh chấp (Dispute Resolution) giữa Antigravity và OpenCode.
   - **Phê duyệt hiến pháp**: Quyết định duy nhất có thể thay đổi SSoT [`.keyword.md`](file:///d:/Docker/JKAI/.keyword.md).
   - **Ngắt mạch khẩn cấp (Break-Glass / Circuit Breaker)**: Dừng phiên ngay lập tức, chuyển trạng thái giữa `AUTONOMOUS` và `INTERACTIVE`.
3. **Giao diện can thiệp của Master**:
   - Giao tiếp qua chỉ thị chat trực tiếp.
   - Can thiệp kỹ thuật qua cờ lệnh: `--force` (cưỡng chế trigger), `--recover-state` (phục hồi state).
   - Sửa đổi trực tiếp tệp trạng thái [state.json](file:///d:/Docker/JKAI/Thao%20luan%20AI/state.json).

---

## ⚡ I. NGUYÊN TẮC CỐT LÕI & CƠ CHẾ PHÂN XỬ TRANH CHẤP

1. **Phân định vai trò bất biến (Separation of Duties)**:
   - **Antigravity (Builder / Lead Architect)**: Khảo sát thực tế, viết mã nguồn, sửa lỗi, chạy test thực tế, cập nhật kiến trúc và đề xuất giải pháp.
   - **Opencode (Red Team / Independent Auditor)**: Độc lập rà soát mã nguồn, chạy kiểm thử xác minh, thẩm định logic và ra phán quyết (Verdict).
   - **Tuyệt đối không tự chấm điểm**: Antigravity không tự duyệt nghiệm thu cho mình; OpenCode không viết code thay Builder.
2. **Không gian làm việc & SSoT**:
   - Mọi trao đổi thực hiện duy nhất tại `Thao luan AI/Noi dung thao luan.md`.
   - Tuyệt đối không can thiệp, chỉnh sửa hay ghi đè nội dung lượt (Turn) của bên kia.
3. **Cơ chế Phân xử Tranh chấp (Dispute Resolution)**:
   - Nếu Antigravity cho rằng phán quyết FAIL của OpenCode là nhận định sai (False Positive) hoặc đòi hỏi ngoài phạm vi:
     * Antigravity có quyền gửi **1 Lượt Giải Trình Kỹ Thuật (Rebuttal Turn)** đính kèm bằng chứng đối sánh, log thực thi và phân tích nguyên nhân gốc.
     * OpenCode bắt buộc phải thẩm định lại các bằng chứng đối chất này.
     * Nếu sau 1 lượt Rebuttal hai bên vẫn bất đồng quan điểm: Vụ việc **tự động chuyển lên Master**. Phán quyết của Master là phán quyết cuối cùng có hiệu lực tuyệt đối.

---

## 🚀 II. VẬN HÀNH 1 LỆNH DUY NHẤT & XỬ LÝ TIMEOUT

Toàn bộ quy trình thủ công 5 bước trước đây (dò port, tính turn, ghi file, recover-state, trigger, wait) được chuyển giao hoàn toàn cho bộ điều phối tự động **`Thao luan AI/dispatch_turn.py`**:

```bash
python "Thao luan AI/dispatch_turn.py" --speaker "Antigravity" --phase "<PHASE_NAME>" --title "<TIÊU ĐỀ>" --body-file "<FILE_NOI_DUNG>" --wait --timeout 180 --interval 1
```

### Các năng lực tự động hóa & Chống treo:
1. **Dò Session thông minh**: Tự động tìm port và Session ID đang active của OpenCode Desktop. Có thể chỉ định session thủ công qua tham số nếu cần.
2. **Cấp phát Lượt an toàn**: Tự đọc Lượt cuối, tính `turn_id` và `parent_turn_id`.
3. **Đóng gói Turn Block chuẩn**: Bọc mã `<!-- TURN_BEGIN -->` ... `<!-- TURN_END -->` kèm chữ ký và hash toàn vẹn.
4. **Ghi nguyên tử (Atomic Write + File Lock)**: Khóa file an toàn, ngăn chặn xung đột ghi đè.
5. **Đồng bộ hóa Trạng thái**: Tự động hòa giải `state.json` và `state.json.bak`.
6. **Cảnh báo chuyển Session & Mandatory First-Contact Protocol Briefing (Master Directive)**:
   - Nếu phát hiện Session mới từ OpenCode, script tự động chèn chỉ thị tối thượng:
     > `⚠️ [CHỈ THỊ MASTER - PHÁT HIỆN SESSION MỚI TỪ OPENCODE]: OpenCode BẮT BUỘC ĐỌC tệp 'Thao luan AI/Quy trinh & Nguyen tac thao luan AI.md' và GHI NHỚ, THỰC HIỆN NGHIÊM NGẶT các nguyên tắc làm việc tại '.keyword.md' (.keywork.md)!`
7. **Xử lý Timeout & Session Lost (3 Lớp Bảo Vệ)**:
   - **Chu kỳ thăm dò**: 1 giây (poll 1s), timeout mặc định **180s**.
   - **Lớp 1: Cửa sổ ân hạn (Grace Window 5s)**: Khi chạm 180s, hệ thống tự động chờ thêm 5s để đón nhận các sự kiện ghi đĩa ở giây cuối.
   - **Lớp 2: Tự động nhắc nhở (Auto-Retry 1 lần)**: Nếu sau 5s vẫn chưa có Turn Block, tự động gửi 1 tín hiệu ping đánh thức qua API tới OpenCode Desktop và gia hạn thêm 60s.
   - **Lớp 3: Cứu hộ Master (Master Intervention)**: Nếu sau lần thử 2 vẫn timeout, chuyển trạng thái sang `WAITING_FOR_MASTER_INTERVENTION` và in hướng dẫn khắc phục 1-click cho Master.

---

## 🎯 III. TIÊU CHÍ NGHIỆM THU MỞ RỘNG & XÁC MINH LOG

Mỗi lượt phản biện của OpenCode bắt buộc tuân theo bảng kiểm tra chuẩn kèm bằng chứng thực nghiệm:

```markdown
### 📋 RED TEAM AUDIT VERDICT
- [ ] Code có chạy thực tế trên môi trường không? (Bắt buộc đính kèm log thật kèm command line và timestamp)
- [ ] Có vi phạm Invariants, SSoT hoặc kiến trúc lõi không?
- [ ] Có lỗi CRITICAL (hỏng hệ thống / memory leak / giả mạo test) không?
- [ ] Có lỗi MAJOR (sai lệch logic / thiếu error handling) không?
- [ ] Có vi phạm nguyên tắc `.keyword.md` (zero-noise, zero-junk, tiếng Việt) không?

=> PHÁN QUYẾT: **PASS** | **PASS_CONDITIONAL** | **FAIL**
```

### Định nghĩa 3 trạng thái phán quyết:
1. **`PASS`**: Nghiệm thu hoàn toàn, code chạy thật, không vi phạm bất kỳ tiêu chí nào, không có nợ kỹ thuật.
2. **`PASS_CONDITIONAL`**: Nghiệm thu có điều kiện. Code chạy đúng và vượt qua các test cốt lõi, nhưng tồn tại một số nợ kỹ thuật nhẹ (Tech Debt) hoặc cải tiến hiệu năng chưa gấp, được ghi nhận vào Tech Debt Backlog để xử lý ở phase sau mà không làm chặn luồng hiện tại.
3. **`FAIL`**: Không nghiệm thu. Bắt buộc nêu rõ phân loại lỗi:
   - **`CRITICAL`**: Crash hệ thống, vi phạm Invariants, giả lập/mock test bẩn.
   - **`MAJOR`**: Sai lệch logic nghiệp vụ, thiếu xử lý ngoại lệ quan trọng.
   - **`MINOR`**: Lỗi cú pháp nhỏ, thiếu docstring, định dạng chưa chuẩn.

---

## 🤖 IV. CƠ CHẾ TỰ TRỊ TOÀN DIỆN (AUTONOMOUS MODE)

Khi Master kích hoạt lộ trình tự động:
1. **Khi OpenCode phán quyết PASS hoặc PASS_CONDITIONAL**: Antigravity lập tức khởi chạy bước tiếp theo trong lộ trình, không dừng lại xin phép. Các ghi chú nợ kỹ thuật (nếu có) được tự động lưu vào backlog.
2. **Khi OpenCode phán quyết FAIL (MINOR / MAJOR)**: Antigravity tự động phân tích root cause, sửa mã nguồn, chạy lại kiểm thử và gửi lại OpenCode thẩm tra.
3. **Khi FAIL (CRITICAL) 2 lần liên tiếp (Circuit Breaker)**: Hệ thống tự động ngắt mạch, chuyển sang chờ Master can thiệp để ngăn chặn vòng lặp suy thoái vô tận.

---

## 📦 V. QUẢN LÝ CONTEXT & QUY TRÌNH ROLLBACK ARCHIVE

1. **Vì sao 800 dòng / 80 KB là quá tải đối với SLM 3B/4B?**:
   - 80 KB văn bản tiếng Việt có dấu tương đương ~14.000–18.000 tokens.
   - SLM 3B (như `qwen2.5-coder:3b` trên 8GB VRAM) có ngưỡng cửa sổ ngữ cảnh tối ưu là 8.192 tokens. Khi vượt quá ngưỡng này, KV-cache tràn sang RAM khiến tốc độ suy luận giảm từ 45 tokens/s xuống < 10 tokens/s, đồng thời gây ra hiện tượng **Suy thoái chú ý (Attention Degradation)** khiến mô hình quên luật lệ và bịa đặt thông tin.
2. **Điểm vàng Context (The Sweet Spot)**:
   - **Mục tiêu tối ưu**: **300 dòng / 30 KB** (~4.500–5.500 tokens). Đảm bảo dư thừa hơn 3.000 tokens cho system prompt, luật `.keyword.md`, và output generation.
   - **Trần cứng kích hoạt lưu trữ**: **500 dòng / 50 KB**.
3. **Quy trình Compaction & Rollback an toàn**:
   - Khi tệp `Noi dung thao luan.md` vượt ngưỡng 350 dòng, hàm `verify_and_archive_discussion()` tự động tạo bản sao lưu `.bak` trước khi cắt tỉa.
   - Các lượt cũ đã nghiệm thu được đóng gói vào `archive_Phien_XX_PartYY.md` với mã băm SHA-256 lưu trong `archive_manifest.json`.
   - **Cơ chế Rollback**: Nếu việc xác thực hash sau cắt tỉa thất bại, hệ thống tự động hoàn tác (restore) nguyên trạng từ file `.bak` mà không làm mất bất kỳ ký tự nào.

