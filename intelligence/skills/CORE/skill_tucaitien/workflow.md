# [ZENITH FILE DIRECTIVE]
# - File: workflow.md
# - Role: Standard Operating Procedure (Workflow) for skill_tucaitien
# - Status: Optimized | Version: Zenith v6.0

## 1. Lưu Đồ Tiến Trình Nâng Cấp Hệ Thống

Tiến trình nâng cấp kỹ năng tự cải tiến tuân thủ nghiêm ngặt 5 giai đoạn khép kín nhằm bảo đảm tính toàn vẹn hệ thống:

```mermaid
graph TD
    A[Khởi chạy /tucaitien] --> B[Sao chép & Chạy JKAI_MAP_graph.py tại gốc]
    B --> C[Dọn dẹp tệp map_graph tại gốc]
    C --> D[Lấy ngữ cảnh liên kết vĩ mô từ JKAI_MAP_GRAPH.md]
    D --> E[Gọi OmniSearch truy vấn tri thức tối ưu hóa]
    E --> F[Thiết lập phiên giao dịch ACID & Tạo sao lưu .bak]
    F --> G[LLM thiết kế mã nguồn mới bám sát SDS Header]
    G --> H[Thẩm định cú pháp tĩnh AST]
    H --> I[Chạy thử nghiệm cô lập trong Sandbox]
    I -->|Lỗi Runtime / Crash| J[Kích hoạt Rollback khôi phục nguyên bản]
    I -->|Thành công 100%| K{Chế độ Dry Run?}
    K -->|True| L[Rollback & Báo cáo Diff chi tiết]
    K -->|False| M[Commit ghi đè file production & Xóa file .bak]
```

## 2. Quy Tắc An Toàn Trung Ương

*   **Ranh giới Tác chiến**: Mọi hoạt động sửa đổi tệp tin phải được quản lý bởi `cognitive_transaction_manager` để bảo đảm tính hoàn vẹn, không cho phép sửa đổi mồ côi ngoài luồng giao dịch.
*   **Chính sách Zero-Trust**: Hộp cát Sandbox cô lập phải được áp dụng thời hạn chạy tối đa (timeout) không quá 5 giây và bị chặn đứng tuyệt đối mọi câu lệnh gọi tiến trình hệ thống trái phép từ Policy Proof Engine.
*   **Vệ sinh Hệ thống**: Bất kỳ tệp tin phụ trợ hoặc tập lệnh sinh bản đồ tạm thời nào được ghi vào thư mục gốc của dự án đều phải được đăng ký trong cấu trúc `try...finally` để dọn dẹp triệt để ngay lập tức sau khi hoàn thành công việc.
