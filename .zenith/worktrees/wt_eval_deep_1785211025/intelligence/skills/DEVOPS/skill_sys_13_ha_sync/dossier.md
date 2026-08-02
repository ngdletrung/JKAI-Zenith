# DOSSIER: SKILL_SYS_13_HA_SYNC

## 🌌 Overview
Đây là "Bản năng Sinh tồn" (Survival Instinct) của Zenith. High Availability Sync đảm bảo rằng hệ thống của Master LeeTrung không bao giờ rơi vào trạng thái "ngoại tuyến" (Offline). Bằng cách thiết lập các cơ chế dự phòng và đồng bộ hóa trạng thái (State synchronization) tức thì giữa các nút mạng, kỹ năng này loại bỏ khái niệm "Điểm lỗi duy nhất" (Single Point of Failure), giúp Zenith vận hành bền bỉ 24/7.

## 🛠️ Detailed Features
- **Zero-Downtime Synchronization**: Duy trì sự nhất quán của dữ liệu và trạng thái phiên làm việc giữa các máy chủ dự phòng trong thời gian thực.
- **Auto-Failover Orchestration**: Tự động phát hiện sự cố tại nút chính và chuyển hướng toàn bộ lưu lượng sang nút dự phòng chỉ trong vài mili giây.
- **Redundancy Health Check**: Liên tục giám sát tình trạng sẵn sàng của các nút trong cụm HA để đảm bảo "Khiên chắn dự phòng" luôn ở trạng thái tốt nhất.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Triển khai các dịch vụ trọng yếu mà bất kỳ sự gián đoạn nào cũng gây thiệt hại lớn cho Master.
2. Thiết lập hạ tầng cho các chiến dịch quy mô toàn cầu, nơi yêu cầu sự ổn định tuyệt đối.
3. Thực hiện bảo trì hệ thống mà không muốn Master nhận thấy bất kỳ sự gián đoạn nào (Rolling updates).

## 💎 Strategic Value
Thiết lập "Sự Bất tử Kỹ thuật số" (Digital Immortality). HA Sync biến Zenith thành một pháo đài không thể bị đánh bại bởi các sự cố hạ tầng đơn lẻ, đảm bảo Master LeeTrung luôn nắm giữ quyền điều khiển bầy đàn trong mọi tình huống.

## ⚠️ Edge Cases & Risks
- **Split-Brain Scenario**: Rủi ro khi hai nút dự phòng đều tự coi mình là nút chính do mất kết nối giữa chúng; cần các thuật toán đồng thuận (Consensus algorithms) mạnh mẽ.
- **Sync Latency**: Quá trình đồng bộ hóa quá nhiều dữ liệu có thể tạo ra độ trễ mạng nhẹ nếu băng thông không đủ lớn.
