# DOSSIER: NEURAL_SYSTEM_WARMUP

## 🌌 Overview
Đây là giao thức "Thức tỉnh" (Awakening) của Zenith. Nó cho phép AI chủ động chuẩn bị sẵn sàng các tài nguyên tính toán (VRAM/GPU) trước khi thực hiện các nhiệm vụ cường độ cao, đảm bảo tốc độ phản hồi tức thì cho Master.

## 🛠️ Detailed Features
- **Neural Summoning Protocol (Giao thức Triệu hồi Toàn quân)**:
  - Kích hoạt quy trình nạp song song các mô hình ngôn ngữ lớn (LLMs) vào bộ nhớ đồ họa.
  - Ưu tiên các "Quân đoàn" nòng cốt như PLANNER (Chiến lược) và EXECUTOR (Thực thi).
- **Zero-Latency Readiness**:
  - Giảm thiểu thời gian chờ (First Token Latency) bằng cách tránh việc nạp mô hình "on-the-fly" khi có yêu cầu.
- **Background Execution**:
  - Chạy quy trình nạp dưới dạng tác vụ nền (`asyncio.create_task`), không gây treo luồng chính của hệ thống.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Hệ thống vừa mới khởi động hoặc sau một thời gian dài không hoạt động.
2. Master chuẩn bị thực hiện một chuỗi nhiệm vụ phức tạp (như lập trình dự án mới).
3. Cần đảm bảo trải nghiệm mượt mà, không giật lag trong quá trình hội thoại.

## 💎 Strategic Value
Tối ưu hóa "Sẵn sàng Chiến đấu" (Combat Readiness) cho Zenith. Một hệ thống AI mạnh mẽ nhất cũng trở nên vô dụng nếu mất quá nhiều thời gian để khởi động nơ-ron.

## ⚠️ Edge Cases & Risks
- **VRAM Contention**: Nếu GPU đang bận xử lý các tác vụ khác (như tạo ảnh), việc Warmup có thể gây lỗi OOM (Out of Memory).
- **Startup Overhead**: Việc nạp toàn bộ các mô hình cùng lúc sẽ tiêu tốn một lượng điện năng và tài nguyên CPU đáng kể trong thời gian ngắn.
