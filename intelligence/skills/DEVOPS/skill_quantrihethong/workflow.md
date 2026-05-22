# 📑 QUY TRÌNH TÁC CHIẾN (WORKFLOW): QUẢN TRỊ HỆ THỐNG

Đây là quy trình SOP bắt buộc cho mọi Đặc vụ khi thực thi các tác vụ liên quan đến hệ thống tệp tin và lệnh shell.

---

### 🛡️ CHIẾN THUẬT 1: CẬP NHẬT MÃ NGUỒN (CODE UPDATE)
*Áp dụng khi cần sửa lỗi hoặc thêm tính năng vào file hiện có.*

1. **B1 (Định vị)**: Gọi `liet_ke_thu_muc` để xác nhận đường dẫn file.
2. **B2 (Đọc hiểu)**: Gọi `doc_tep` để kiểm tra nội dung hiện tại. Tuyệt đối không sửa khi chưa đọc.
3. **B3 (Mô phỏng)**: Tạo đoạn mã thay thế và đối soát với đoạn mã gốc.
4. **B4 (Thực thi)**: Gọi `phau_thuat_tep`. Nếu file quá nát hoặc cần viết lại hoàn toàn mới dùng `ghi_tep`.
5. **B5 (Hậu kiểm)**: Dùng `chay_lenh_docker` để chạy thử code (nếu là script) hoặc dùng `doc_tep` một lần nữa để xác nhận thay đổi.

---

### 📦 CHIẾN THUẬT 2: KIẾN TẠO MODULE MỚI (NEW MODULE)
*Áp dụng khi tạo mới hoàn toàn một công cụ hoặc kỹ năng.*

1. **B1**: Dùng `tao_thu_muc` để tạo không gian làm việc.
2. **B2**: Dùng `ghi_tep` để khởi tạo các file cốt lõi.
3. **B3**: Dùng `chay_lenh_docker` để thiết lập quyền hạn hoặc cài đặt phụ thuộc.

---

### 🚨 GIAO THỨC CỨU HỘ (RECOVERY)
Nếu lệnh `phau_thuat_tep` báo lỗi "Target not found":
- Ngay lập tức dùng `doc_tep` để lấy lại bản sao mới nhất của file (có thể file đã bị thay đổi bởi Đặc vụ khác).
- Tuyệt đối không cố gắng ghi đè mù quáng.

---
*KỶ LUẬT LÀ SỨC MẠNH!* 💎🫡🦾
