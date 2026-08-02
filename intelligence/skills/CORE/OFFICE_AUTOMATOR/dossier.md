# 🏛️ HỒ SƠ CHIẾN LƯỢC: OFFICE_AUTOMATOR

## 🎯 Bối cảnh sử dụng (Trigger Conditions)
Sử dụng khi Master yêu cầu đọc/phân tích tài liệu Word/Excel, tạo mới báo cáo, bảng tính hoặc tự động điền thông tin vào tệp biểu mẫu (template) Word, Excel, PowerPoint.

## 🛠️ Hướng dẫn thực thi
1. **Đọc dữ liệu (`action=dump`)**: Trích xuất nội dung của file sang JSON để mô hình AI đọc hiểu.
2. **Điền biểu mẫu (`action=merge`)**: Điền thông tin động từ JSON vào tệp template chứa placeholder `{{key}}`.
3. Hệ thống sẽ tự động tải file chạy Linux của `OfficeCLI` và cấu hình môi trường trong lần đầu tiên chạy.
