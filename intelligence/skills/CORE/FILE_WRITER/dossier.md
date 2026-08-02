# 🏛️ HỒ SƠ CHIẾN LƯỢC: FILE_WRITER

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi cần tạo mới một tệp mã nguồn, tệp cấu hình JSON/YAML hoặc ghi đè hoàn toàn nội dung cũ của một tệp khi đã có đầy đủ mã nguồn mới.

## 🛠️ Hướng dẫn thực thi
1. Chỉ ghi đè khi chắc chắn không làm mất các đoạn code quan trọng của tệp cũ (đặc biệt là đối với các tệp lớn). Đối với việc chỉnh sửa cục bộ hoặc vá code, ưu tiên dùng `REPO_SURGEON`.
2. Hệ thống sẽ tự động tạo các thư mục cha nếu chưa tồn tại.
