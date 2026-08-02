# DOSSIER: SKILL_SYS_12_SHARDING

## 🌌 Overview
Đây là "Kiến trúc Phân mảnh" (Fragmentation Architecture) của Zenith. Data Sharding Engine giải quyết bài toán dữ liệu khổng lồ bằng cách chia nhỏ các bảng cơ sở dữ liệu lớn thành các phần (Shards) nhỏ hơn và phân tán chúng trên nhiều server. Kỹ năng này đảm bảo rằng ngay cả khi dữ liệu của Master LeeTrung tăng lên hàng tỷ bản ghi, tốc độ truy vấn vẫn giữ được sự tức thì (Instant response).

## 🛠️ Detailed Features
- **Horizontal Partitioning Strategy**: Tự động phân tích và lựa chọn `Shard Key` tối ưu để đảm bảo dữ liệu được phân bổ đồng đều giữa các node.
- **Cross-Shard Query Orchestration**: Quản lý việc truy vấn dữ liệu từ nhiều shard khác nhau và hợp nhất kết quả một cách mạch lạc cho AI xử lý.
- **Dynamic Re-sharding**: Hỗ trợ việc di chuyển và phân bổ lại các mảnh dữ liệu khi có thêm node mới gia nhập hạ tầng mà không làm gián đoạn dịch vụ.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cơ sở dữ liệu hiện tại đạt đến ngưỡng giới hạn về hiệu năng (Query latency tăng cao).
2. Master yêu cầu thiết kế một hệ thống có khả năng lưu trữ và xử lý dữ liệu ở quy mô Terabyte hoặc Petabyte.
3. Cần tối ưu hóa chi phí phần cứng bằng cách sử dụng nhiều server tầm trung thay vì một server siêu khủng.

## 💎 Strategic Value
Thiết lập "Khả năng Lưu trữ Vô tận" (Infinite Storage Capability). Sharding Engine giúp Zenith không bao giờ bị "nghẹn" bởi dữ liệu, biến mọi thông tin Master thu thập được thành tài sản có thể truy xuất tức thì và hiệu quả.

## ⚠️ Edge Cases & Risks
- **Complexity in Joins**: Việc thực hiện các phép Join giữa dữ liệu ở các shard khác nhau rất phức tạp và tốn kém tài nguyên.
- **Hotspot Shards**: Nếu `Shard Key` không được chọn tốt, một shard có thể bị quá tải trong khi các shard khác lại nhàn rỗi.
