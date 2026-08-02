# WORKFLOW PLAYBOOK: Spec-Driven Development

Quy trình phát triển sản phẩm hướng đặc tả tối thượng (Sovereign SDLC Playbook). 
Khi nhận diện Sứ mệnh mới cần thiết lập đặc tả kỹ thuật, Planner BẮT BUỘC phải tuân thủ và ánh xạ lộ trình thực thi theo trình tự các bước dưới đây.

---

## 🧬 SKILL SEQUENCING (Chuỗi liên kết Kỹ năng)

Quy trình thực thi gồm chuỗi 7 bước tuần tự có tính kế thừa thông tin thông qua `MissionState`:

```
[1. INTERVIEW] ──→ [2. SPECIFY] ──→ [3. PLAN/BREAKDOWN] ──→ [4. IMPLEMENT] ──→ [5. TEST (TDD)] ──→ [6. AUDIT/REVIEW] ──→ [7. SHIP]
```

### 1. Phỏng vấn Đặc vụ (Interviewing Master)
- **Kỹ năng sử dụng**: `interview-me` (ID: #1083)
- **Mục tiêu**: Làm rõ các yêu cầu mơ hồ, phác thảo phạm vi tính năng ban đầu, đặt câu hỏi cho Master để loại bỏ mọi giả định ngầm định.
- **Tiêu chí hoàn thành (Exit Criteria)**: Master trả lời các câu hỏi làm rõ quan trọng.

### 2. Thiết lập Đặc tả kỹ thuật (Technical Specification)
- **Kỹ năng sử dụng**: `spec-driven-development` (ID: #4010)
- **Mục tiêu**: Soạn thảo file đặc tả kỹ thuật `spec.md` chi tiết chứa: Objective, Commands, Project Structure, Code Style, Testing Strategy, Boundaries (Always/Ask First/Never).
- **Tiêu chí hoàn thành (Exit Criteria)**: File `spec.md` được tạo và Master duyệt thông qua.

### 3. Phân rã Kế hoạch & Tác vụ (Planning & Task Breakdown)
- **Kỹ năng sử dụng**: `planning-and-task-breakdown` (ID: #4020)
- **Mục tiêu**: Chuyển đổi spec thành sơ đồ DAG và danh sách checklist công việc trong file `task.md` với tiêu chí nghiệm thu cho từng tác vụ nhỏ.
- **Tiêu chí hoàn thành (Exit Criteria)**: File `task.md` được sinh ra với các task độc lập có kích thước nhỏ.

### 4. Triển khai Mã nguồn (Incremental Implementation)
- **Kỹ năng sử dụng**: `incremental-implementation` (ID: #3010)
- **Mục tiêu**: Viết code tuần tự theo từng task, không sửa đổi các vùng không liên quan, tuân thủ đúng phạm vi file đã hoạch định.
- **Tiêu chí hoàn thành (Exit Criteria)**: Code được viết hoàn chỉnh không có lỗi cú pháp.

### 5. Viết & Chạy Kiểm thử (Test-Driven Development)
- **Kỹ năng sử dụng**: `test-driven-development` (ID: #3503)
- **Mục tiêu**: Thực thi chu kỳ Red-Green-Refactor. Viết test case lỗi trước khi viết code xử lý.
- **Tiêu chí hoàn thành (Exit Criteria)**: Toàn bộ Unit/Integration tests chạy thông qua thành công (`exit 0`).

### 6. Rà soát Chất lượng & An ninh (Code Review & Quality Gate)
- **Kỹ năng sử dụng**: `code-review-and-quality` (ID: #6015)
- **Mục tiêu**: Kiểm toán mã nguồn theo 5 trục (Correctness, Readability, Architecture, Security, Performance).
- **Tiêu chí hoàn thành (Exit Criteria)**: Bảng báo cáo Code Audit được Critic duyệt thông qua.

### 7. Nghiệm thu & Chuyển giao (Shipping & Launch)
- **Kỹ năng sử dụng**: `shipping-and-launch` (ID: #3510)
- **Mục tiêu**: Đồng bộ mã nguồn, dọn dẹp môi trường sandbox, đóng gói và báo cáo kết quả nghiệm thu cuối cùng cho Master.
- **Tiêu chí hoàn thành (Exit Criteria)**: Hệ thống được deploy thành công, sandbox sạch sẽ.

---

## 🛡️ DECISION TREE & PATHWAY BRANCHING (Nhánh rẽ quy trình)

- **Nếu tính năng cực kỳ đơn giản (< 10 dòng code và không có rủi ro logic):**
  - Cho phép rút ngắn: Skip bước 1 (`interview-me`) và bước 3 (`planning-and-task-breakdown`).
  - *Bắt buộc giữ lại*: Viết test (`test-driven-development`) và Kiểm toán (`code-review-and-quality`).
- **Nếu phát hiện xung đột thư viện hoặc thay đổi DB Schema trong quá trình làm:**
  - *Quay lại bước 2*: Cập nhật `spec.md` -> Yêu cầu Master xác nhận -> Cập nhật `task.md`.

---

## 🏁 GLOBAL EXIT CRITERIA (Tiêu chí nghiệm thu toàn cục)

- [ ] Tài liệu đặc tả `spec.md` khớp 100% với code thực tế.
- [ ] Checklist `task.md` đạt trạng thái hoàn thành hoàn toàn `[x]`.
- [ ] Bằng chứng kiểm thử (`evidence/` hoặc terminal output) được lưu vào `MissionState.artifacts`.
- [ ] Critic Agent ký duyệt báo cáo chất lượng không có lỗi Security.
