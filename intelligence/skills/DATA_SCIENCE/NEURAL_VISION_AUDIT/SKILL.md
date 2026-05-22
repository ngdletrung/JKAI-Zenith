---
id: NEURAL_VISION_AUDIT
name_vn: "Mắt Thần Thấu Thị Giao Diện"
version: 1.2.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["CAPTURE", "VISION"]
  - ["AUDIT", "INTERFACE"]
aliases_vn: ["chụp ảnh màn hình", "screenshot", "audit giao diện", "neural eye", "thị giác máy tính web"]
schema:
  parameters:
    type: object
    properties:
      url: { type: string, description: "Địa chỉ web cần thấu thị." }
    required: ["url"]
priority: HIGH
related_skills: ["SUPER_DATA_SCIENCE", "WEB_PATHFINDER"]
---

# 👁️ MẮT THẦN THẤU THỊ GIAO DIỆN (NEURAL_VISION_AUDIT)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Thị giác" vĩ mô. Nó sử dụng hệ thống Vệ tinh (AI-Browser) để chụp lại hình ảnh thực tế của bất kỳ trang web nào và tiến hành phân tích sâu bằng AI Vision để phát hiện các lỗi hiển thị, sự cố giao diện hoặc các thành phần UI bị hỏng.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Liên kết Vệ tinh**: Kiểm tra kết nối với dịch vụ `ai-browser`.
2. **Tiếp cận Mục tiêu**: Truy cập URL và chờ giao diện nạp hoàn tất.

### 🚀 Phase 2: Action (Thực thi)
1. **Thấu Thị (Capture)**: Chụp ảnh màn hình độ phân giải cao.
2. **Audit Thị Giác**: Gửi hình ảnh qua bộ não AI Vision để rà soát lỗi giao diện (Overlap, Broken UI, Error Messages).
3. **Báo Cáo Sự Cố**: Trình bày kết quả phân tích hình ảnh và cảnh báo các điểm bất thường cho Master.

---
## ⚖️ LUẬT THỊ GIÁC (VISION LAWS)
- **Tính Thực Tế**: Chỉ báo cáo những gì thực sự nhìn thấy trên hình ảnh.
- **Tính Cảnh Giác**: Luôn ưu tiên phát hiện các thông báo lỗi và thành phần UI bị lỗi.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Vệ tinh `ai-browser` bị ngoại tuyến khiến không thể chụp ảnh.
- Trang web yêu cầu đăng nhập hoặc có tường lửa chặn truy cập.

---
*NHÌN THẤU MỌI SỰ THẬT!* 💎🦾
