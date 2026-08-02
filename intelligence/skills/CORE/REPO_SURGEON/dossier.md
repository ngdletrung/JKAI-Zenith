# 🏛️ HỒ SƠ CHIẾN LƯỢC: REPO_SURGEON

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi cần chỉnh sửa, sửa lỗi (bug fix), cải tiến mã nguồn cho các tệp tin trong hệ thống. Đây là phương pháp chỉnh sửa mã nguồn chính thống và an toàn nhất.

## 🛠️ Hướng dẫn thực thi
1. Bản vá `patches` chứa danh sách các tệp tin cần thay đổi kèm nội dung mới đầy đủ của chúng.
2. Công cụ tự động chạy kiểm tra cú pháp AST cho Python. Nếu code bị lỗi cú pháp, bản vá sẽ tự động bị từ chối trước khi ghi đè tệp tin gốc.
3. Sau khi áp dụng bản vá thành công, hệ thống tự động kiểm thử để xác định tính ổn định.
