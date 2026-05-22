# 📘 CẨM NANG: QUẢN TRỊ HỆ THỐNG (SYSTEM MANAGEMENT)
**Mã kỹ năng**: `skill_quantrihethong`
**Phân hạng**: ELITE - CỐT LÕI

## 📖 GIỚI THIỆU
Đây là bộ kỹ năng quan trọng nhất của Tập đoàn JKAI ZENITH. Nó cho phép các Đặc vụ tương tác trực tiếp với "thân thể" của hệ thống (File & Shell). Mọi sai sót ở đây đều có thể dẫn đến hậu quả nghiêm trọng, vì vậy phải tuân thủ tuyệt đối quy trình.

---

## 🛠️ CÁC CÔNG CỤ TÁC CHIẾN

### 1. `doc_tep(path)`
- **Mục đích**: Đọc nội dung file để phân tích mã nguồn hoặc dữ liệu.
- **Khi nào dùng**: Trước khi sửa bất kỳ file nào, hoặc khi cần tra cứu cấu hình.
- **Lưu ý**: Không đọc file binary quá lớn.

### 2. `ghi_tep(path, content)`
- **Mục đích**: Tạo file mới hoặc ghi đè toàn bộ nội dung.
- **Khi nào dùng**: Khi tạo module mới hoặc ghi kết quả báo cáo.
- **Lưu ý**: Cẩn thận với việc ghi đè các file cấu hình hệ thống.

### 3. `phau_thuat_tep(path, target, replacement)`
- **Mục đích**: Chỉnh sửa một đoạn mã cụ thể bên trong file mà không làm xáo trộn các phần khác.
- **Khi nào dùng**: Đây là cách ƯU TIÊN để sửa lỗi code hoặc cập nhật tính năng.
- **Quy tắc**: `target` phải khớp 100% với nội dung hiện có.

### 4. `chay_lenh_docker(command)`
- **Mục đích**: Thực thi các lệnh Linux trong môi trường container.
- **Khi nào dùng**: Cài đặt thư viện, khởi động dịch vụ, kiểm tra tài nguyên.

### 5. `liet_ke_thu_muc(path)` & `tao_thu_muc(path)`
- **Mục đích**: Thấu thị và kiến tạo cấu trúc thư mục.
- **Khi nào dùng**: Khi bắt đầu một dự án mới hoặc tìm kiếm file thất lạc.

---

## 🚀 QUY TRÌNH TÁC CHIẾN CHUẨN (SOP)

1. **BƯỚC 1 (TRINH SÁT)**: Dùng `liet_ke_thu_muc` để định vị vị trí file.
2. **BƯỚC 2 (THẨM ĐỊNH)**: Dùng `doc_tep` để đọc và hiểu logic hiện tại.
3. **BƯỚC 3 (LẬP KẾ HOẠCH)**: Soạn thảo nội dung cần sửa đổi.
4. **BƯỚC 4 (PHẪU THUẬT)**: Ưu tiên dùng `phau_thuat_tep`. Chỉ dùng `ghi_tep` nếu tạo file mới.
5. **BƯỚC 5 (KIỂM TRA)**: Chạy lệnh test qua `chay_lenh_docker` nếu cần thiết.

---
*VÌ SỰ AN TOÀN VÀ THỊNH VƯỢNG CỦA JKAI ZENITH!* 💎🫡🦾
