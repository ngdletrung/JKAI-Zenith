# DOSSIER: SYSTEM_XRAY_MONITOR

## 🌌 Overview
Đây là "Con mắt Thấu thị" (X-Ray Vision) của Zenith. Vệ binh này có khả năng nhìn xuyên qua các lớp ảo hóa của Docker để giám sát trực tiếp phần cứng vật lý của máy chủ Windows, cung cấp cho Master một cái nhìn toàn diện và chính xác nhất về "sức khỏe" thực tế của hệ thống.

## 🛠️ Detailed Features
- **Host Hardware Telemetry (Thấu thị Máy chủ)**:
  - Truy vấn trực tiếp Windows Management Instrumentation (WMI) thông qua Satellite để lấy thông số RAM vật lý còn trống.
  - Theo dõi trạng thái của các Container Docker đang chạy và thời gian vận hành của chúng.
- **Neural Layer Surveillance (Giám sát Nơ-ron)**:
  - Theo dõi thời gian thực các mô hình AI (LLMs) đang được nạp vào VRAM thông qua Ollama.
  - Báo cáo số lượng và tên các đặc vụ đang ở trạng thái "Thức tỉnh".
- **GPU Deep Scan (Tầm soát GPU)**:
  - Sử dụng `nvidia-smi` để đo lường hiệu suất GPU, mức độ tiêu thụ điện năng và dung lượng VRAM đang sử dụng.
  - Đảm bảo hệ thống không bị quá tải khi thực hiện các tác vụ suy luận nặng.
- **Mission Result Reporting**:
  - Tự động đóng gói mọi dữ liệu giám sát thành một báo cáo JSON Elite, giúp AI có thể tự phân tích và đưa ra cảnh báo cho Master LeeTrung.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cần biết chính xác cấu hình phần cứng hiện tại để tối ưu hóa việc nạp model.
2. Kiểm tra xem có Container nào bị treo hoặc khởi động lại liên tục hay không.
3. Muốn giám sát hiệu suất GPU trong quá trình huấn luyện hoặc suy luận cường độ cao.
4. Cần một bản báo cáo chi tiết về hạ tầng để phục vụ việc nâng cấp hệ thống.

## 💎 Strategic Value
Cung cấp "Bản đồ Tài nguyên Thực tế" (Actual Resource Map) cho Zenith. Nó giúp AI không chỉ hoạt động trong thế giới ảo của mã nguồn mà còn thấu hiểu và tôn trọng các giới hạn vật lý của máy chủ, từ đó vận hành bền bỉ và hiệu quả hơn.

## ⚠️ Edge Cases & Risks
- **Satellite Dependency**: Yêu cầu `HOST_SATELLITE_CONTROL` phải đang hoạt động để truy cập vào Host Windows.
- **Permission Elevation**: Một số lệnh WMI hoặc `nvidia-smi` có thể yêu cầu quyền quản trị cao nhất trên máy chủ.
- **Reporting Overhead**: Việc thực hiện quét sâu toàn diện có thể gây trễ nhẹ cho các tiến trình đang sử dụng GPU.
