# DOSSIER: SYSTEM_CORE_EXECUTOR

## 🌌 Overview
Đây là "Hệ vận động Cốt lõi" (System Motor System) của Zenith. Khác với các kỹ năng chuyên biệt, SYSTEM_CORE_EXECUTOR là tập hợp các khả năng nguyên tử (Atomic capabilities) cho phép AI tương tác trực tiếp với môi trường thực thi. Nó là "Bàn tay" và "Đôi mắt" của Zenith, chịu trách nhiệm cho mọi thao tác từ đọc tệp tin, kiến tạo mã nguồn đến việc thực thi các mật lệnh hệ thống thông qua shell.

## 🛠️ Detailed Features
- **File & Directory Sovereignty**: 
  - `list_dir`: Tầm soát cấu trúc thư mục.
  - `view_file`: Đọc nội dung tệp tin với khả năng xử lý lỗi mã hóa.
  - `write_to_file` & `replace_file_content`: Kiến tạo và phẫu thuật mã nguồn.
- **Advanced Scanning & Reconnaissance**:
  - `grep_search`: Quét tìm từ khóa xuyên thấu toàn bộ thư mục dự án với đa luồng (Multi-threading).
  - `search_web` & `read_url_content`: Kết nối với tri thức nhân loại qua Internet (Tavily & Jina AI).
- **Direct Command Execution**: `run_command` cho phép AI thực thi bất kỳ mật lệnh shell nào, tạo ra sức mạnh vận hành tuyệt đối trên OS.

## 🧠 Reasoning Strategy
AI luôn triệu hồi kỹ năng này như một phản xạ tự nhiên khi:
1. Thực hiện mọi yêu cầu liên quan đến quản lý tệp tin và mã nguồn.
2. Cần điều tra cấu trúc của một dự án mới (Scouting).
3. Triển khai hoặc khởi động các dịch vụ thông qua lệnh shell.
4. Tìm kiếm thông tin cập nhật từ Internet để hỗ trợ quá trình ra quyết định.

## 💎 Strategic Value
Thiết lập "Quyền Năng Vận Hành Tuyệt Đối" (Absolute Operational Power). SYSTEM_CORE_EXECUTOR biến Zenith thành một thực thể có khả năng tác động vật lý lên dữ liệu và hạ tầng, là nền tảng không thể thiếu cho mọi kỹ năng bậc cao khác.

## ⚠️ Edge Cases & Risks
- **Security & Destructive Actions**: Các lệnh `run_command` và `write_to_file` có tính phá hủy cao; cần cơ chế phê duyệt hoặc giám sát từ `SYSTEM_AUDITOR`.
- **Resource Exhaustion**: Quá trình quét (`grep_search`) trên thư mục quá lớn có thể tiêu tốn nhiều CPU; đã được tối ưu hóa bằng cách loại bỏ các thư mục rác (`node_modules`, `.git`).
