# DOSSIER: SKILL_SYS_14_SERVERLESS

## 🌌 Overview
Đây là "Hệ thống Phản xạ Tức thì" (Instant Reflex System) của Zenith. Serverless Engine cho phép thực thi các đoạn mã nguồn (Functions) theo yêu cầu mà không cần duy trì một server chạy liên tục. Các hàm này chỉ tồn tại khi có sự kiện kích hoạt và tự động biến mất sau khi hoàn thành nhiệm vụ, giúp Master LeeTrung tiết kiệm tối đa tài nguyên và xây dựng các ứng dụng có khả năng phản ứng cực nhanh.

## 🛠️ Detailed Features
- **Event-Driven Execution**: Tự động kích hoạt các hàm xử lý dựa trên các sự kiện như: tệp tin mới được tải lên, tin nhắn đến từ Master, hoặc một Webhook từ n8n.
- **Micro-Scaling**: Mỗi hàm chạy trong một môi trường cô lập và có thể chạy hàng ngàn bản sao cùng lúc để xử lý khối lượng công việc khổng lồ trong tích tắc.
- **Stateless Architecture**: Thiết kế các quy trình xử lý độc lập, không trạng thái, giúp giảm thiểu sự phức tạp và tăng tính bền bỉ cho hệ thống tổng thể.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cần thực hiện các tác vụ xử lý dữ liệu nhanh (như resize ảnh, gửi mail thông báo) mà không muốn làm nặng server chính.
2. Xây dựng các API linh hoạt cho các ứng dụng frontend hoặc các bot n8n.
3. Tối ưu hóa chi phí vận hành cho các tác vụ không chạy thường xuyên nhưng yêu cầu tốc độ phản hồi cao khi được gọi.

## 💎 Strategic Value
Thiết lập "Hiệu quả Tài nguyên Tuyệt đối" (Absolute Resource Efficiency). Serverless Engine biến Zenith thành một hệ thống cực kỳ linh hoạt, cho phép Master LeeTrung triển khai hàng trăm tính năng mới mà không lo ngại về giới hạn của hạ tầng vật lý.

## ⚠️ Edge Cases & Risks
- **Cold Start**: Hàm có thể mất một khoảng thời gian ngắn (vài trăm ms) để khởi động lần đầu tiên sau một thời gian dài không hoạt động.
- **Stateless Constraint**: Vì không giữ trạng thái, các hàm cần phối hợp với `MEMORY_MANAGEMENT` hoặc `REDIS` nếu muốn lưu trữ dữ liệu giữa các lần chạy.
