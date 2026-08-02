# [ZENITH FILE DIRECTIVE]
# - File: manual.md
# - Role: Operator Manual for skill_tucaitien
# - Status: Optimized | Version: Zenith v6.0

## 1. Tổng Quan Hệ Thống

Kỹ năng tự cải tiến (`skill_tucaitien`) là thành phần cốt lõi trong phân vùng nhận thức của Zenith v6.0. Kỹ năng này cung cấp các cơ chế phân tích cấu trúc, tối ưu thuật toán và nâng cấp tự trị mã nguồn của các kỹ năng thành phần thông qua giao dịch ACID nhận thức và kiểm thử an toàn trong hộp cát Sandbox.

## 2. Giao Thức Vận Hành

Kỹ năng tự cải tiến hoạt động thông qua một điểm nhập duy nhất:

### Giao Diện Lệnh: `phau_thuat_logic`

*   **Tham số đầu vào**:
    *   `skill_id` (str): Định danh duy nhất của kỹ năng mục tiêu cần nâng cấp (ví dụ: `skill_tucaitien`, `skill_tusualoi`).
    *   `optimization_goal` (str): Mục tiêu tối ưu hóa chi tiết (ví dụ: cải tiến hiệu năng, dọn dẹp các từ ngữ cường điệu, sửa lỗi xử lý luồng).
    *   `dry_run` (bool, mặc định `False`): Chế độ chạy thử không ghi đè trực tiếp lên đĩa, trả về báo cáo so sánh Diff và kết quả thử nghiệm trong hộp cát.

## 3. Kiến Trúc Vận Hành Toàn Cục

1.  **Đồng bộ hóa Bản đồ Thực địa**: Kỹ năng tự động sao chép tệp tạo đồ thị `JKAI_MAP_graph.py` ra thư mục gốc dự án, thực thi để tái lập `JKAI_MAP_GRAPH.md`, sau đó xóa sạch tệp tạm thời tại gốc dự án để bảo đảm tính ngăn nắp và an toàn thông tin.
2.  **Đọc Ngữ Cảnh Đồ Thị**: Hệ thống trích xuất dòng liên kết vĩ mô liên quan đến kỹ năng mục tiêu để làm đầu vào cho mô hình LLM, ngăn ngừa đứt gãy liên kết vĩ mô.
3.  **Khởi Tạo Giao Dịch**: Gọi `cognitive_transaction_manager` để thiết lập phiên giao dịch an toàn và sao lưu tệp `logic.py` mục tiêu thành tệp `.bak` dự phòng.
4.  **Kiểm Thử Hộp Cát Sandbox**: Mã nguồn cải tiến đề xuất được đưa vào hộp cát cô lập `scratch/sandbox` và chạy thử để thẩm định lỗi runtime hoặc cú pháp.
5.  **Cam Kết Hoặc Hoàn Tác**: Nếu kiểm thử thành công và không ở chế độ `dry_run`, hệ thống sẽ ghi đè lên tệp production và commit giao dịch. Ngược lại, hệ thống sẽ khôi phục tệp nguyên gốc từ `.bak` và giải phóng giao dịch.
