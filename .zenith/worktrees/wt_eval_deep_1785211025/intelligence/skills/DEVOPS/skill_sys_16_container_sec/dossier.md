# DOSSIER: SKILL_SYS_16_CONTAINER_SEC

## 🌌 Overview
Đây là "Giáp trụ Hạ tầng" (Infrastructure Armor) của Zenith. Gia cố Bảo mật Container tập trung vào việc bảo vệ các đơn vị vận hành (Docker Containers) khỏi các mối đe dọa bên trong và bên ngoài. Kỹ năng này thực hiện các quy trình từ quét lỗ hổng trong image, thiết lập quyền hạn tối thiểu (Least Privilege) đến việc cô lập mạng lưới, đảm bảo bầy đàn của Master LeeTrung hoạt động trong một môi trường "Bất khả xâm phạm".

## 🛠️ Detailed Features
- **Vulnerability Image Scanning**: Tự động rà soát các lớp (Layers) của Docker Image để tìm kiếm các thư viện lỗi thời hoặc có lỗ hổng bảo mật đã biết (CVEs).
- **Runtime Policy Enforcement**: Thiết lập các ràng buộc trong quá trình chạy (ví dụ: Read-only root filesystem, No-new-privileges) để ngăn chặn các cuộc tấn công leo thang đặc quyền.
- **Network Micro-segmentation**: Phối hợp với hạ tầng mạng để chỉ cho phép các container giao tiếp với nhau qua các kênh cần thiết nhất, giảm thiểu bề mặt tấn công.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master yêu cầu triển khai một dịch vụ mới ra môi trường internet (Public facing).
2. Thực hiện kiểm toán bảo mật (Security Audit) định kỳ cho toàn bộ hạ tầng Docker.
3. Phát hiện các dấu hiệu bất thường trong việc sử dụng tài nguyên của một container cụ thể (phối hợp với `XRAY_MONITOR`).

## 💎 Strategic Value
Thiết lập "Sự Kiên cố của Quân đoàn" (Fortified Swarm). Container Security Shield giúp Master LeeTrung hoàn toàn yên tâm khi mở rộng hệ thống, biết rằng mọi "binh sĩ số" đều được trang bị giáp trụ tốt nhất để chống lại các cuộc tấn công mạng ngày càng tinh vi.

## ⚠️ Edge Cases & Risks
- **Operational Friction**: Các chính sách bảo mật quá nghiêm ngặt có thể làm gián đoạn các luồng công việc hợp lệ; cần sự tinh chỉnh (Fine-tuning) từ Master.
- **False Positives**: Quá trình quét image có thể báo cáo các lỗ hổng không thực sự gây nguy hiểm trong bối cảnh sử dụng cụ thể của Zenith.
