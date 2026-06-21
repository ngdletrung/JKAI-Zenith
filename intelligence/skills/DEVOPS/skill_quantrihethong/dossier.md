# DOSSIER: SKILL_QUANTRIHETHONG

## 🌌 Overview
Đây là "Người bảo an Dữ liệu" (Data Custodian) của Zenith. Quản trị Hệ thống không chỉ thực hiện các thao tác CRUD cơ bản, mà nó thiết lập một lớp bảo vệ an toàn cao cấp cho toàn bộ tài sản số của Master LeeTrung. Mọi hành động ghi đè hay xóa tệp đều được xử lý thông qua các giao thức an toàn như Sao lưu tức thì (Instant Backup) và Thùng rác nơ-ron (Soft-delete), đảm bảo khả năng phục hồi dữ liệu trong mọi tình huống sai sót.

## 🛠️ Detailed Features
- **Safe Write with Instant Backup**: Trước khi ghi đè lên bất kỳ tệp tin nào, hệ thống tự động tạo một bản sao lưu trong thư mục `archive/backups` kèm theo mốc thời gian (Timestamp).
- **Soft-Delete Mechanism (Thùng rác Nơ-ron)**: Di chuyển các tệp tin bị xóa vào thư mục `archive/trash` thay vì xóa vĩnh viễn, cho phép phục hồi nhanh chóng khi cần thiết.
- **Storage Telemetry**: Cung cấp các số liệu thống kê chi tiết về dung lượng đĩa cứng, tỷ lệ sử dụng và không gian trống còn lại trong Workspace.
- **Elite Directory Listing**: Hiển thị danh sách tệp tin với định dạng chuyên nghiệp, bao gồm loại tệp, kích thước và thời gian sửa đổi cuối cùng.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master yêu cầu xóa các tệp tin hoặc thư mục quan trọng (đảm bảo có đường lùi).
2. Cần ghi đè các tệp cấu hình hệ thống mà không muốn rủi ro làm mất dữ liệu cũ.
3. Cần kiểm tra tình trạng lưu trữ để lên kế hoạch dọn dẹp hoặc mở rộng tài nguyên.
4. Thực hiện các nhiệm vụ khôi phục dữ liệu từ các bản sao lưu trước đó.

## 💎 Strategic Value
Thiết lập "Sự An tâm Tuyệt đối" (Absolute Peace of Mind). Quản trị Hệ thống đảm bảo rằng Master LeeTrung không bao giờ phải lo lắng về việc mất mát dữ liệu do sai sót của AI hoặc con người, biến Zenith thành một môi trường làm việc cực kỳ an toàn và bền bỉ.

## ⚠️ Edge Cases & Risks
- **Backup Bloat**: Việc tạo quá nhiều bản sao lưu có thể làm đầy ổ cứng theo thời gian; cần có quy trình định kỳ để dọn dẹp thư mục `archive/backups`.
- **Path Resolution**: Cần đảm bảo các đường dẫn tệp tin được xử lý chính xác để tránh tác động lên các khu vực nhạy cảm bên ngoài Workspace.
