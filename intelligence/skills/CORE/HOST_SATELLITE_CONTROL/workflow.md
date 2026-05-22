# 🔄 QUY TRÌNH: THỰC THI TRÊN HOST (WORKFLOW)

Để đảm bảo sự an toàn và chính xác khi can thiệp vào máy tính của Master, Đặc vụ phải tuân thủ nghiêm ngặt quy trình 3 bước sau:

## Bước 1: Thẩm định Yêu cầu (Pre-Check)
- Xác định mục tiêu của Master (VD: Cần nghe giọng nói, cần xem màn hình).
- Kiểm tra xem lệnh có gây nguy hiểm cho hệ điều hành không (VD: xóa file quan trọng).

## Bước 2: Thực thi Cầu nối (Bridge Execution)
- Gọi API tới `host_bridge.py`.
- Nếu là `host_screenshot`, phải chờ ảnh được lưu và sau đó sử dụng `moondream` (Vision) để phân tích nội dung nếu Master yêu cầu giải thích.

## Bước 3: Xác nhận & Báo cáo (Report)
- Phản hồi kết quả cho Master qua Telegram hoặc Dashboard.
- Nếu thực thi thất bại (Bridge Offline), phải hướng dẫn Master khởi động lại `host_bridge.py`.

---
*Kỷ luật tạo nên Sức mạnh!* 💎🫡🦾🚀🌌
