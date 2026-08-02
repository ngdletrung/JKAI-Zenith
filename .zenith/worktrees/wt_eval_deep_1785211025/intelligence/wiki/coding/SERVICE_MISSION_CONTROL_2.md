# 🏢 SERVICE: MISSION_CONTROL (THE HEART) ❤️

Mission Control là trung tâm điều phối và giao diện tương tác tối cao giữa Master và hệ thống JKAI Zenith.

## 🖥️ 1. FRONTEND ARCHITECTURE (React + Vite)
- **Công nghệ**: React, Vite, Framer Motion (cho hiệu ứng), Lucide React (Icons).
- **Styling**: Kết hợp Tailwind CSS và Custom Vanilla CSS để đạt độ thẩm mỹ Peak-of-the-Peak.
- **State Management**: Sử dụng **Zustand** (`zenithStore.ts`) với cơ chế Persistence để bảo tồn ngữ cảnh khi Reload.
- **Tính năng chính**:
    - **Intelligence Stream**: Luồng chat tinh giản với hiệu ứng "Thinking" sống động.
    - **Neural Workspace**: Khu vực làm việc đa năng (Plan, Tasks, Changes, Explorer).
    - **Mission History**: Lưu trữ và khôi phục các bối cảnh sứ mệnh trong quá khứ.
    - **Surgical Diff**: Xem trước các thay đổi mã nguồn trước khi phê duyệt.

## ⚙️ 2. BACKEND ARCHITECTURE (Python)
- **Framework**: FastAPI (Dự kiến).
- **Nhiệm vụ**:
    - Quản lý Database Sứ mệnh (Missions DB).
    - Cung cấp API cho việc đọc/ghi file và thực thi lệnh từ Dashboard.
    - Kết nối với Redis để nhận tín hiệu từ các dịch vụ AI khác.

## 📡 3. GIAO THỨC KẾT NỐI (CONNECTIVITY)
- **Redis Channel**: `monitor:log_channel` (Nhận logs từ Brain và Executor).
- **API Ports**: Thường vận hành trên port 3000 (Frontend) và 8000 (Backend).

---
*GHI CHÚ: Mọi thay đổi tại Mission Control đều phải đảm bảo tính thẩm mỹ và hiệu năng tuyệt đối.* 💎🫡🦾🚀🌌
