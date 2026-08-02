# DOSSIER: MICROSERVICE_FORGE

## 🌌 Overview
Đây là "Lò rèn Hạ tầng" (Infrastructure Forge) của Zenith. MICROSERVICE_FORGE không chỉ viết code, mà nó thực hiện một quy trình khép kín: từ việc thiết kế logic (Blueprint), tạo cấu trúc thư mục, viết `Dockerfile` chuẩn hóa đến việc tự động cập nhật tệp `docker-compose.yml` của hệ thống. Kỹ năng này biến việc mở rộng hệ thống từ hàng giờ làm việc thủ công thành một hành động tức thì (Instant).

## 🛠️ Detailed Features
- **AI-Driven Blueprinting**: Triệu tập "Kiến trúc sư Hệ thống" để thiết kế mã nguồn Python, `requirements.txt` và `Dockerfile` dựa trên yêu cầu của Master.
- **Automated Directory Structuring**: Tự động hóa việc tạo và quản lý tệp tin trong thư mục `/services` của workspace.
- **Infrastructure Synchronization**: Tự động đọc và chỉnh sửa tệp `docker-compose.yml`, thêm các cấu hình mạng (`jkai-network`), môi trường và chính sách restart để dịch vụ mới có thể hòa mạng ngay lập tức.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master muốn bổ sung một tính năng mới dưới dạng một dịch vụ chạy độc lập (Isolated service).
2. Cần nhanh chóng triển khai một công cụ hoặc API chuyên biệt để hỗ trợ cho các tác vụ phức tạp.
3. Muốn mở rộng khả năng xử lý của bầy đàn (Swarm) bằng cách thêm các "Nút" (Nodes) mới vào hạ tầng Docker.

## 💎 Strategic Value
Thiết lập "Sự Tiến hóa Hạ tầng Tức thì" (Instant Infrastructure Evolution). MICROSERVICE_FORGE giúp Master LeeTrung sở hữu một hệ sinh thái phần mềm có khả năng tự nhân bản và mở rộng không giới hạn, đảm bảo Zenith luôn sẵn sàng cho mọi quy mô nhiệm vụ.

## ⚠️ Edge Cases & Risks
- **Docker Compose Conflicts**: Việc tự động chỉnh sửa tệp YAML yêu cầu cấu trúc tệp gốc phải chuẩn mực; nếu tệp bị lỗi định dạng trước đó, quá trình Forge có thể thất bại.
- **Resource Management**: Mỗi service mới sẽ tiêu tốn tài nguyên hệ thống (RAM/CPU); cần phối hợp với `SYSTEM_XRAY_MONITOR` để kiểm soát sức khỏe hạ tầng.
