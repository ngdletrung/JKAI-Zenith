# 🏛️ HỒ SƠ CHIẾN LƯỢC: SHELL_EXECUTOR

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi cần chạy các tập lệnh tự động, khởi chạy bộ thử nghiệm (test suite), dịch dự án (compile/build), hoặc kiểm tra thông tin tiến trình hoạt động.

## 🛠️ Hướng dẫn thực thi
1. Mọi lệnh chạy mặc định sẽ được thực thi tại thư mục gốc của Workspace (`/workspace`).
2. Thời gian chạy tối đa là 120 giây. Các lệnh kéo dài vô tận hoặc cần tương tác người dùng (nhập yes/no) sẽ bị treo và timeout, do đó chỉ chạy các lệnh tự động (non-interactive).
