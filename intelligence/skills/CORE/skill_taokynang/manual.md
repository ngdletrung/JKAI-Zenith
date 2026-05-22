# 🧬 QUY TRÌNH TAM HỢP: KIẾN TẠO KỸ NĂNG ELITE (v10.0)

Chào Đặc vụ JKAI Zenith. Đây là quy trình bắt buộc khi bạn được Master yêu cầu tạo ra hoặc nâng cấp một Kỹ năng (Skill) mới. Hãy tuân thủ để đảm bảo hệ thống luôn ổn định và chuyên nghiệp.

---

### 🏛️ CẤU TRÚC 3 THÀNH PHẦN (THE TRINITY)

Mọi kỹ năng thực thi (Callable Skill) phải bao gồm đầy đủ 3 thành phần sau:

#### 1. LINH HỒN (Instruction - .md)
- **Vị trí**: `D:/Docker/N8N/intelligence/skills/skill_[tên_kỹ_năng].md`
- **Nội dung**: Hướng dẫn bằng Tiếng Việt về mục đích, cách sử dụng và các tình huống áp dụng. Đây là nơi bạn lưu giữ tư duy của kỹ năng.

#### 2. CHỨNG CHỈ (Schema - .json)
- **Vị trí**: `D:/Docker/N8N/services/tools/definitions/schemas/[tên_kỹ_năng].json`
- **Nội dung**: Định nghĩa kỹ thuật chuẩn JSON Schema. Bao gồm tên (name), mô tả (description) và các tham số (parameters). Đây là file để bộ não Planner lập kế hoạch gọi lệnh.

#### 3. THỰC THI (Logic - .py)
- **Vị trí**: 
    - Nếu là tool điều phối: `D:/Docker/N8N/services/tools/definitions/[tên_kỹ_năng].py`
    - Nếu là tool thực thi hệ thống: `D:/Docker/N8N/services/ai-executor/tool_impls/[tên_kỹ_năng].py`
- **Nội dung**: Mã nguồn Python thực thi hành động. Phải có xử lý lỗi (try-except) và thông báo log rõ ràng.

---

### 📝 QUY TRÌNH 4 BƯỚC THỰC HIỆN:

1. **PHÁC THẢO**: Sử dụng `read_file` để xem các kỹ năng tương tự làm mẫu.
2. **KIẾN TẠO**: Sử dụng `write_file` để tạo lần lượt 3 file (MD -> JSON -> PY).
3. **GHI DANH**: Sử dụng `patch_file` để thêm kỹ năng mới vào `D:/Docker/N8N/intelligence/MAP_SKILLS.md`.
4. **ĐỒNG BỘ**: Nhắc Master chạy lệnh `sync_nuclear` để bộ não RAG cập nhật tri thức mới nhất.

---

### 🛡️ NGUYÊN TẮC AN TOÀN:
- Tuyệt đối không ghi đè các file hệ thống cốt lõi (`engine.py`, `app.py`) khi chưa có lệnh xác nhận từ Master.
- Luôn kiểm tra cú pháp Python trước khi lưu file.
- Ghi chú trong code bằng Tiếng Việt để Master có thể rà soát.

*Bạn là một phần của Zenith OS. Hãy kiến tạo những điều vĩ đại.* 💎🫡
