# DOSSIER: SKILL_GIAM_SAT_HE_THONG

## 🌌 Overview
Đây là "Nhãn quan Hạ tầng" (Infrastructure Vision) của Zenith. Giám sát Hệ thống chịu trách nhiệm thu thập các chỉ số Telemetry từ phần cứng (CPU, RAM, Disk) và các bản ghi nhật ký (Logs) để đảm bảo hệ thống luôn vận hành ở trạng thái "Elite Operational". Kỹ năng này cung cấp các báo cáo vĩ mô giúp Master LeeTrung nắm bắt được tải trọng của các "Phòng ban AI" và phát hiện sớm các dấu hiệu bất thường.

## 🛠️ Detailed Features
- **Real-time Telemetry Analysis**: Sử dụng `psutil` để đo lường chính xác hiệu năng hệ thống tại thời điểm thực thi.
- **System Health Scoring**: Tự động phân loại trạng thái vận hành (ví dụ: `ELITE OPERATIONAL` hoặc `HIGH LOAD`) dựa trên các ngưỡng thông số cấu hình sẵn.
- **Autonomous Log Auditing**: Rà soát nhật ký hệ thống để tìm kiếm các dấu hiệu xâm nhập trái phép hoặc các lỗi logic tiềm ẩn trong quá trình vận hành của Swarm.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Master muốn kiểm tra xem máy tính/server có đang bị quá tải bởi các đặc vụ AI hay không.
2. Cần điều tra nguyên nhân gây chậm trễ trong việc phản hồi của hệ thống.
3. Thực hiện quy trình bảo trì định kỳ để đảm bảo không có lỗi log nào bị bỏ sót.

## 💎 Strategic Value
Thiết lập "Sự Minh bạch và Tin cậy" (Transparency & Reliability). Giám sát Hệ thống giúp Master LeeTrung luôn nắm thế chủ động trong việc quản lý tài nguyên, ngăn chặn tình trạng treo máy hoặc hỏng hóc hạ tầng do quá tải.

## ⚠️ Edge Cases & Risks
- **Overhead**: Quá trình giám sát (đặc biệt là quét log liên tục) có thể tiêu tốn một lượng nhỏ tài nguyên CPU.
- **Permissions**: Yêu cầu quyền truy cập vào các chỉ số hệ thống của OS để có thể thu thập dữ liệu chính xác.
