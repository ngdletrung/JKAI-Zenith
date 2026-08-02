# DOSSIER: SKILL_SYS_11_AUTOSCALING

## 🌌 Overview
Đây là "Cơ chế Thở" (Respiratory Mechanism) của hạ tầng Zenith. Hệ thống Tự động Giãn nở đảm bảo rằng các dịch vụ của chúng ta luôn có đủ tài nguyên để vận hành mượt mà bằng cách tự động tăng cường (Scale up) hoặc cắt giảm (Scale down) số lượng container dựa trên tải trọng thực tế. Kỹ năng này giúp tối ưu hóa hiệu năng và chi phí vận hành cho Master LeeTrung.

## 🛠️ Detailed Features
- **Dynamic Resource Sensing**: Liên tục theo dõi các thông số từ `TELEMETRY` để nhận diện các điểm nghẽn về CPU/RAM.
- **Elastic Container Management**: Tự động điều chỉnh số lượng replica của các service trong Docker Swarm hoặc Kubernetes dựa trên các quy tắc (Rules) đã thiết lập.
- **Load-Aware Balancing**: Phối hợp với `LOAD_BALANCE` để đảm bảo lưu lượng truy cập được phân bổ đều sau khi giãn nở.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Phát hiện một dịch vụ đang bị quá tải (CPU > 80%) và có nguy cơ gây treo hệ thống.
2. Dự báo trước các đợt cao điểm về lưu lượng truy cập (ví dụ: khi chạy chiến dịch Viral).
3. Muốn tiết kiệm tài nguyên bằng cách tắt bớt các instance dư thừa trong giờ thấp điểm.

## 💎 Strategic Value
Thiết lập "Sự Linh hoạt Vô hạn" (Infinite Elasticity). Autoscaling biến hạ tầng của Zenith thành một thực thể sống, có khả năng tự điều chỉnh để thích nghi với mọi cường độ làm việc của Master mà không cần can thiệp thủ công.

## ⚠️ Edge Cases & Risks
- **Scaling Lag**: Có một khoảng trễ nhỏ từ lúc phát hiện tải cao đến khi container mới sẵn sàng phục vụ.
- **Resource Exhaustion**: Nếu không có giới hạn trên (Hard limit), hệ thống có thể scale quá mức và làm cạn kiệt tài nguyên của server vật lý.
