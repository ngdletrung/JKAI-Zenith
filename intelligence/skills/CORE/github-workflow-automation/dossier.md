# DOSSIER: GITHUB_WORKFLOW_AUTOMATION

## 🌌 Overview
Đây là "Kiến trúc sư CI/CD" (CI/CD Architect) của Zenith. Kỹ năng này tập trung sâu vào việc thiết kế và vận hành các luồng tự động hóa phức tạp thông qua GitHub Actions. Nó giúp biến các quy trình phát triển thủ công thành một chuỗi các sự kiện tự kích hoạt, đảm bảo tính liên tục và ổn định cho mã nguồn.

## 🛠️ Detailed Features
- **Workflow Synthesis & Design**: Tự động viết các tệp cấu hình YAML cho GitHub Actions, tối ưu hóa cho từng loại dự án cụ thể (Python, Node.js, Docker).
- **CI/CD Pipeline Monitoring**: Giám sát trạng thái thực thi của các Workflow và tự động báo cáo lỗi hoặc các điểm nghẽn cho Master.
- **Secret & Runner Governance**: Hỗ trợ quản lý các biến môi trường bảo mật (Secrets) và cấu hình các máy chủ thực thi (Runners) để đạt hiệu suất tối đa.
- **Event-Driven Automation**: Thiết lập các quy trình tự động dựa trên các sự kiện đặc thù của GitHub (như Push, Release, Issue Open).

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Cần thiết lập một quy trình tự động kiểm tra code (Linting/Testing) cho dự án.
2. Muốn tự động hóa việc đóng gói (Build) và đẩy ảnh Docker (Push) lên Registry.
3. Cần tối ưu hóa thời gian triển khai thông qua các kỹ thuật caching và parallel execution trong GitHub Actions.

## 💎 Strategic Value
Nâng cao "Năng lực Vận hành" (Operational Capability) của Zenith. Tự động hóa Workflow giúp giải phóng sức sáng tạo của Master LeeTrung bằng cách để máy móc tự xử lý các công đoạn kiểm tra và triển khai nhàm chán nhưng quan trọng.

## ⚠️ Edge Cases & Risks
- **YAML Syntax Errors**: Một sai sót nhỏ trong cú pháp YAML có thể làm hỏng toàn bộ luồng tự động hóa.
- **Resource Limits**: Các Workflow chạy quá lâu hoặc quá thường xuyên có thể làm cạn kiệt số phút miễn phí (Free Minutes) trên GitHub.
- **Security Leaks**: Cần đặc biệt cẩn thận khi truyền các biến bảo mật vào Workflow để tránh bị lộ trong nhật ký (Logs).
