# 🏛️ HỒ SƠ CHIẾN LƯỢC: CODE_GREP

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi cần tìm kiếm nơi định nghĩa của một biến, một hàm, một class, hoặc khi cần truy quét các vị trí xuất hiện của một từ khóa lỗi trong toàn bộ mã nguồn dự án.

## 🛠️ Hướng dẫn thực thi
1. Truy vấn `query` nên là từ khóa hoặc chuỗi ký tự chính xác cần tìm (ví dụ: `class ToolRouter`).
2. Mặc định công cụ sẽ quét qua các tệp nguồn phổ biến như `.py`, `.json`, `.yaml`, `.yml`, `.md` và bỏ qua các thư mục thư viện bên ngoài (như `.git`, `node_modules`, `venv`) để tối ưu hiệu năng.
