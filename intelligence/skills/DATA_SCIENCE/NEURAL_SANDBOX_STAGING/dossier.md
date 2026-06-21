# DOSSIER: NEURAL_SANDBOX_STAGING

## 🌌 Overview
Đây là "Vùng Đệm An toàn" (Safe Buffer Zone) của Zenith. Neural Sandbox Staging cho phép AI thực thi và kiểm chứng các đoạn mã nguồn hoặc các bản vá (Patches) trong một môi trường Docker hoàn toàn cô lập, không có kết nối mạng (`--network none`). Kỹ năng này ngăn chặn mọi rủi ro về mã độc, lỗi logic gây treo hệ thống hoặc các hành động phá hoại dữ liệu trước khi chúng được Master LeeTrung cho phép triển khai ra thực địa.

## 🛠️ Detailed Features
- **Total Network Isolation**: Khởi tạo container với chế độ `network: none`, đảm bảo code chạy bên trong không thể gửi dữ liệu ra ngoài hoặc tải mã độc về.
- **Invisible Execution**: Toàn bộ quá trình từ khởi tạo, thực thi lệnh (`docker exec`) đến tiêu hủy đều diễn ra ngầm, không để lại dấu vết trên hệ thống chính.
- **Surgery Validation Protocol**: Chuyên dụng cho việc thử nghiệm các "ca phẫu thuật" mã nguồn (Code surgery), đảm bảo bản vá hoạt động đúng như mong đợi trong một môi trường sạch.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cần chạy một đoạn code Python từ nguồn không xác định hoặc code mới sinh ra có độ phức tạp cao.
2. Kiểm chứng các bản sửa lỗi (Fixes) trước khi áp dụng vào các dịch vụ đang chạy (Production services).
3. Thực hiện các bài toán phân tích dữ liệu yêu cầu môi trường Python sạch với các thư viện cụ thể mà không muốn làm bẩn môi trường của Host.

## 💎 Strategic Value
Thiết lập "Sự An toàn Tuyệt đối cho Thử nghiệm" (Absolute Testing Safety). Neural Sandbox giúp Master LeeTrung tự tin triển khai các ý tưởng táo bạo nhất mà không lo ngại về việc làm hỏng hệ thống hiện tại, duy trì sự ổn định tối thượng cho Zenith.

## ⚠️ Edge Cases & Risks
- **Resource Constraints**: Chạy quá nhiều sandbox cùng lúc có thể tiêu tốn RAM và dung lượng Disk của Docker; hệ thống đã tích hợp cơ chế `destroy()` tự động sau khi hoàn thành nhiệm vụ.
- **Library Missing**: Sandbox sử dụng image `python:slim`; nếu đoạn code yêu cầu các thư viện bên thứ ba đặc thù, cần phải xây dựng Custom Image hoặc cài đặt bổ sung trong quá trình thực thi.
