# DOSSIER: HOST_SATELLITE_CONTROL

## 🌌 Overview
Đây là "Cánh tay vật lý" (Physical Limb) của Zenith, cho phép bộ não AI trong Docker vượt qua ranh giới ảo hóa để tác động trực tiếp lên máy chủ vật lý (Host). Nó thiết lập một "Cầu nối Nhất thể" (Unified Bridge) giữa container và hệ điều hành máy chủ.

## 🛠️ Detailed Features
- **Host Speak (TTS)**: 
  - Gửi văn bản tới máy chủ để phát âm thanh qua loa. 
  - Giúp Zenith có khả năng giao tiếp bằng giọng nói trực tiếp với Master LeeTrung.
- **Host Screenshot**: 
  - Chụp ảnh màn hình hiện tại của máy chủ. 
  - Cho phép AI "nhìn" thấy những gì đang diễn ra trên màn hình Windows của Master.
- **Remote Execution (Host Terminal)**: 
  - Thực thi các lệnh PowerShell hoặc CMD trực tiếp trên máy chủ.
  - Cho phép Zenith quản lý tệp tin, dịch vụ và cấu hình hệ điều hành nằm ngoài phạm vi Docker.
- **Physical Interaction (Mouse Control)**: 
  - Khả năng di chuyển và click chuột tại các tọa độ (X, Y) cụ thể.
  - Có thể được sử dụng để tự động hóa các ứng dụng GUI không có API.
- **Sovereign Security (AKAI Token)**:
  - Mọi yêu cầu can thiệp vào máy chủ đều phải mang theo một Token định danh (`X-AKAI-TOKEN`).
  - Đảm bảo chỉ có Zenith Kernel mới có quyền điều khiển các "Vệ tinh" (Satellites) trên Host.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Master yêu cầu "Thông báo bằng giọng nói" hoặc "Đọc cái này lên".
2. Cần kiểm tra trạng thái các ứng dụng đang chạy trên Windows.
3. Cần cài đặt phần mềm hoặc thay đổi cấu hình hệ thống trên máy chủ vật lý.
4. Cần thực hiện các tác vụ tự động hóa giao diện người dùng (RPA).

## 💎 Strategic Value
Xóa bỏ rào cản giữa AI và thế giới vật lý. Zenith không còn bị nhốt trong "hộp" Docker mà trở thành một thực thể quản trị toàn diện máy tính của Master.

## ⚠️ Edge Cases & Risks
- **Network Dependency**: Nếu dịch vụ vệ tinh trên Host (`host.docker.internal:9998`) không chạy, mọi lệnh sẽ thất bại.
- **Security Vulnerability**: Nếu Token bị lộ, các tác nhân bên ngoài có thể chiếm quyền điều khiển máy chủ.
- **Physical Interruption**: Việc điều khiển chuột có thể gây gián đoạn nếu Master đang trực tiếp sử dụng máy tính.
