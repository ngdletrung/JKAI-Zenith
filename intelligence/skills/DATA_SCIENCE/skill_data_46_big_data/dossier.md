# DOSSIER: SKILL_DATA_46_BIG_DATA

## 🌌 Overview
Đây là "Nhà máy Xử lý Hạng nặng" (Heavy-Duty Processing Plant) của Zenith. Big Data Engine giải quyết bài toán "Dữ liệu khổng lồ" mà các công cụ thông thường không thể chạm tới. Sử dụng sức mạnh của Spark và kiến trúc tính toán phân tán, kỹ năng này cho phép Master LeeTrung xử lý, làm sạch và phân tích hàng Petabyte dữ liệu trong thời gian ngắn nhất, biến "Đại dương dữ liệu" thành "Dòng chảy tri thức" mạch lạc cho Tập đoàn.

## 🛠️ Detailed Features
- **Distributed Spark Processing**: Thực thi các tác vụ ETL (Extract, Transform, Load) và phân tích trên cụm máy chủ phân tán, đảm bảo khả năng mở rộng không giới hạn.
- **Real-time Data Streaming**: Xử lý dữ liệu ngay khi chúng vừa phát sinh (như log web, giao dịch tài chính) để cung cấp các báo cáo tức thì cho Master.
- **Massive Storage Connectivity**: Kết nối mạnh mẽ với các hệ thống lưu trữ dữ liệu lớn như HDFS, S3, hoặc các cơ sở dữ liệu NoSQL quy mô lớn.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master yêu cầu xử lý các tệp dữ liệu có dung lượng vượt quá khả năng xử lý của RAM trên một máy đơn lẻ (thường > 10GB).
2. Xây dựng các đường ống dữ liệu (Data pipelines) cho các hệ thống doanh nghiệp lớn.
3. Cần thực hiện các phép tính toán phức tạp trên toàn bộ kho dữ liệu lịch sử của Tập đoàn (phối hợp với `SHARDING`).

## 💎 Strategic Value
Thiết lập "Quyền năng Xử lý Vô hạn" (Infinite Processing Power). Big Data Engine giúp Master LeeTrung không bao giờ bị giới hạn bởi quy mô dữ liệu, biến Zenith thành một "Siêu máy tính" có khả năng thấu hiểu mọi chuyển động dù là nhỏ nhất trong biển thông tin toàn cầu.

## ⚠️ Edge Cases & Risks
- **Cluster Management Complexity**: Yêu cầu hạ tầng cụm máy chủ (Cluster) vận hành ổn định; lỗi tại một node có thể ảnh hưởng đến toàn bộ Job nếu không có cơ chế Fault-tolerance tốt.
- **Data Skew**: Tình trạng dữ liệu phân bổ không đều giữa các node có thể làm chậm tiến độ xử lý chung; cần tối ưu hóa phân vùng dữ liệu (Partitioning).
