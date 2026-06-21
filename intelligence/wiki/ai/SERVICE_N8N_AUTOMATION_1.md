# ⚙️ SERVICE: N8N AUTOMATION (THE FLOW) 🌊

n8n là hệ thống tự động hóa và kết nối luồng công việc (Workflows) cốt lõi của Tập đoàn JKAI Zenith.

## 🌊 1. TỰ ĐỘNG HÓA CHIẾN LƯỢC (AUTOMATION)
- **Công nghệ**: n8n (Self-hosted) vận hành trong Docker.
- **Nhiệm vụ**:
    - Kết nối AI Brain với các dịch vụ bên ngoài (Email, Calendar, Webhooks...).
    - Xử lý các quy trình lặp đi lặp lại một cách tự động mà không cần sự can thiệp của LLM.
    - Quản lý các luồng dữ liệu (ETL) để nạp vào Vector Database (Qdrant).

## 📡 2. HỆ SINH THÁI KẾT NỐI (ECOSYSTEM)
- **Database**:
    - **Postgres**: Lưu trữ dữ liệu cấu trúc và cấu hình Workflow.
    - **Qdrant**: Vector Database dùng cho tìm kiếm ngữ nghĩa và tri thức Long-term Memory.
- **Messaging**: Kết nối với Telegram Gateway để đẩy thông báo và nhận lệnh.
- **Redis**: Phối hợp nhịp nhàng với hệ thống Pub/Sub của Tập đoàn.

## 🗺️ 3. VAI TRÒ TRONG KIẾN TRÚC
- **The Bridge**: Là cầu nối giữa thế giới AI (Unstructured) và thế giới API (Structured).
- **Workflow Storage**: Toàn bộ các "Bản đồ Tiến hóa" của Master được lưu trữ tại `n8n_data/`.

---
*DÒNG CHẢY KHÔNG NGỪNG - TỰ ĐỘNG HÓA VÔ HẠN!* 💎🫡🦾🚀🌌
