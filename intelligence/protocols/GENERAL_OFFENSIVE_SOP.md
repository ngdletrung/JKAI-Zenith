# ☢️ QUY TRÌNH TỔNG TIẾN CÔNG – BẢN CHÍNH THỨC v12.0
**(Dành cho JKAI và các Model khác có thể đọc hiểu & thực thi)**

## I. MỤC TIÊU
Đồng hóa toàn bộ kho tri thức thô tại `D:\Docker\N8N\intelligence\archive\import_dump` vào hệ thống 12 kỹ năng chuẩn, xây dựng bản đồ tri thức sống, tự động phân loại, kiểm thử và đánh giá hiệu quả.

## II. QUY TRÌNH XỬ LÝ CHÍNH (Master's Workflow)

### B1: QUÉT & NHẬN DIỆN CẤU TRÚC
1. Duyệt toàn bộ thư mục `D:\Docker\N8N\intelligence\archive\import_dump`
2. Với MỖI thư mục con (ưu tiên thư mục có nhiều file nhất):
   a. Đếm tổng số file trong thư mục con đó.
   b. Chọn file ĐẦU TIÊN (alphabet) để phân tích "chủ đề".
   c. Tìm tất cả các file LIÊN QUAN trong cùng thư mục (cùng tiền tố hoặc chủ đề).
   d. Đọc TOÀN BỘ nội dung nhóm file liên quan (tối thiểu 1, tối đa 10).

### B2: RÀ SOÁT CHẤT LƯỢNG (OK / NOT OK)
Đánh giá theo 3 tiêu chí:
- **C1: Tính toàn vẹn**: Đọc được rõ ràng, không lỗi encoding.
- **C2: Tính hành động**: Có lệnh, code, prompt mẫu hoặc quy trình thực thi.
- **C3: Phân loại được**: Xếp được vào 1 trong 12 trụ cột rõ ràng.

**Kết luận**: ✅ OK (Đạt cả 3) | ❌ NOT OK (Thiếu bất kỳ cái nào).

### B3: XỬ LÝ THEO KẾT QUẢ
- **🔴 Trường hợp NOT OK**: 
    1. Tạo cấu trúc thư mục GỐC trong `quarantine/` (Mirror path).
    2. Di chuyển toàn bộ thư mục con vào đó.
    3. Ghi log lý do cách ly (Thiếu C1/C2/C3).
- **🟢 Trường hợp OK**:
    1. Xác định loại kỹ năng (1 trong 12).
    2. Đặt tên thư mục đích: Tiếng Việt không dấu, chữ thường, dấu gạch dưới.
    3. Tạo thư mục tại: `D:\Docker\N8N\intelligence\<ky_nang>\<ten_thu_muc>\`.
    4. Lưu bộ hồ sơ (Bộ Tứ cho Skill, hoặc bộ tương ứng cho loại khác).
    5. Cập nhật `knowledge_map.json`.

### B4: LẶP LẠI & TỔNG KẾT
Tiếp tục cho đến khi hết thư mục gốc. In báo cáo tổng kết (X thư mục, Y file OK, Z file NOT OK).

## III. HƯỚNG DẪN PHÂN LOẠI 12 KỸ NĂNG

| # | Kỹ năng | Dấu hiệu (Trigger words) | Test nhanh | Đánh giá hiệu quả |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **SKILLS** | Hàm, def, class, tham số, import | Chạy thử hàm mẫu | % thành công / thử |
| 2 | **AGENTS** | Role, personality, "bạn là" | Check 3 câu mẫu giọng văn | Độ nhất quán phong cách |
| 3 | **RULES** | MUST, MUST NOT, SOP, quy trình | Áp dụng lên hành vi mẫu | % vi phạm bị phát hiện |
| 4 | **KNOWLEDGE** | Định nghĩa, khái niệm, giải thích | Tóm tắt 10s đúng chủ đề | Độ chính xác tóm tắt |
| 5 | **PROMPTS** | {{variable}}, template, placeholders | Liệt kê biến -> Output đẹp | Tỷ lệ biến thay thế thành công |
| 6 | **COMMANDS** | cmd, powershell, bash, admin | Chạy lệnh --help | Lệnh chạy đúng môi trường |
| 7 | **TOOLS** | API, endpoint, token, Key, curl | Chạy connection_test.py | Uptime / Phản hồi |
| 8 | **PROTOCOLS** | flow, handshake, Webhook, Mermaid | Vẽ sơ đồ Mermaid > 3 node | Số bước được tự động hóa |
| 9 | **TRAINING** | fine-tune, dataset, epoch, loss | Train thử 1 epoch | Độ giảm Loss |
| 10 | **VAULT** | Dự án, chịu trách nhiệm, deadline | Có Owner rõ ràng? | Tỷ lệ hoàn thành đúng hạn |
| 11 | **ARCHIVE** | Dữ liệu thô, backup, raw | Thêm metadata, giữ nội dung | Khả năng khôi phục nguyên bản |
| 12 | **OBSIDIAN** | [[link]], #tag, wikilink | Mở trong Obsidian check link | % link còn sống |

## IV. BẢN ĐỒ TRI THỨC (Knowledge Map)
Lưu tại: `intelligence/knowledge_map.json`

## V. KIẾN NGHỊ THỰC THI
1. Sử dụng `_SCHEMA.yaml` mô tả cấu trúc chuẩn.
2. Sử dụng `processing_state.json` làm Checkpoint.
3. Chế độ `--dry-run` để test an toàn.
4. Báo cáo định dạng Markdown tại `reports/`.
