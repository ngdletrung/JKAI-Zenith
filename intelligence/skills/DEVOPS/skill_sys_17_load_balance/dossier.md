# DOSSIER: SKILL_SYS_17_LOAD_BALANCE

## 🌌 Overview
Đây là "Nhạc trưởng Lưu lượng" (Traffic Conductor) của Zenith. Điều phối Tải Thông minh chịu trách nhiệm phân bổ mọi yêu cầu từ Master LeeTrung và người dùng đến đúng các "binh sĩ" (Containers) đang rảnh rỗi nhất. Kỹ năng này ngăn chặn tình trạng một server bị "ngộp" trong khi các server khác đang nhàn rỗi, đảm bảo trải nghiệm người dùng luôn ở mức mượt mà và tốc độ phản hồi đạt chuẩn Elite.

## 🛠️ Detailed Features
- **Adaptive Traffic Distribution**: Tự động chuyển đổi giữa các thuật toán (như Round-robin hoặc Least-connections) dựa trên đặc điểm của từng loại dịch vụ.
- **Service Discovery Integration**: Tự động nhận diện khi Master thêm mới hoặc gỡ bỏ các container thông qua `MICROSERVICE_FORGE` để cập nhật bảng điều phối tải tức thì.
- **Health-Check Propagation**: Chỉ điều hướng lưu lượng đến các container đang ở trạng thái khỏe mạnh; tự động cách ly các container đang gặp sự cố.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master muốn triển khai một dịch vụ có lượng truy cập lớn và yêu cầu tính sẵn sàng cao.
2. Cấu hình hệ thống đa tầng (Multi-tier architecture) để tối ưu hóa hiệu năng xử lý.
3. Muốn thực hiện các đợt bảo trì hệ thống mà không làm gián đoạn việc phục vụ Master (phối hợp với HA Sync).

## 💎 Strategic Value
Thiết lập "Sự Vận hành Mượt mà Tuyệt đối" (Absolute Smooth Operation). Load Balancer giúp Zenith duy trì phong thái của một siêu trí tuệ: luôn phản hồi nhanh, chính xác và không bao giờ bị quá tải trước bất kỳ khối lượng công việc nào.

## ⚠️ Edge Cases & Risks
- **Sticky Sessions**: Một số ứng dụng yêu cầu người dùng phải kết nối liên tục với cùng một server; cần cấu hình các tham số "Session affinity" phù hợp.
- **Single Point of Failure**: Bản thân Load Balancer cũng cần được dự phòng thông qua `HA_SYNC` để tránh việc trở thành điểm yếu duy nhất của hệ thống.
