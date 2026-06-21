# DOSSIER: PROJECT_ANALYZER

## 🌌 Overview
Đây là "Thiên Nhãn" (Architecture Clairvoyance) của Zenith, cho phép AI nhìn thấu cấu trúc, tình trạng và sự phụ thuộc của toàn bộ hệ sinh thái JKAI Zenith. Nó cung cấp cái nhìn vĩ mô về cách các thành phần vận hành và tương tác với nhau.

## 🛠️ Detailed Features
- **Project Mapping (Bản đồ hóa Dự án)**:
  - Tự động quét và nhận diện các service quan trọng trong hạ tầng (`ai-brain`, `ai-executor`, `ai-control-plane`).
  - Phân tích cấu trúc thư mục để xác định đâu là mã nguồn lõi, đâu là tri thức đồng hóa và đâu là các công cụ hỗ trợ.
- **Dependency Analysis (Kiểm tra Phụ thuộc)**:
  - Nhận diện các liên kết giữa các container (Docker), các volume chia sẻ và mạng nội bộ.
  - Giúp AI hiểu được tác động lan tỏa khi một thành phần bị thay đổi.
- **Anomaly Detection (Phát hiện Dị thường)**:
  - Tìm kiếm các file thiếu hụt, cấu trúc không đồng nhất hoặc các file cấu hình bị lỗi.
  - Cảnh báo về các sai lệch so với kiến trúc chuẩn **Sovereign Gateway**.
- **Contextual Awareness**:
  - Tích hợp thông tin về vai trò của các Đặc vụ (Agents) và các Quy tắc (Rules) đang áp dụng cho từng phần của dự án.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master yêu cầu "Giải thích cho tôi kiến trúc của dự án này".
2. Cần lập kế hoạch cho một sự thay đổi lớn ảnh hưởng đến nhiều service.
3. Muốn kiểm tra "sức khỏe" tổng quát của hệ thống sau khi triển khai bản cập nhật mới.
4. Cần định vị một file hoặc tính năng cụ thể trong một codebase khổng lồ.

## 💎 Strategic Value
Đảm bảo AI luôn nắm giữ "Bản đồ Tối cao" (Master Map) của hệ thống. Khi AI hiểu rõ mình đang đứng ở đâu và xung quanh có những gì, nó sẽ hành động với sự tự tin và chính xác tuyệt đối.

## ⚠️ Edge Cases & Risks
- **Large Project Latency**: Với các dự án có hàng chục ngàn file, việc quét sâu (`depth=3` trở lên) có thể mất thời gian.
- **Hidden Dependencies**: Một số liên kết logic ẩn (không qua Docker hay File System) có thể bị bỏ sót nếu không có tài liệu đi kèm.
- **Permission Constraints**: Nếu bị chặn truy cập vào một số thư mục bảo mật, bản đồ sẽ bị khuyết thiếu.
