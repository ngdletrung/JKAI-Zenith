---
id: SELF_HEALING_SENTINEL
name_vn: "Vệ Binh Tự Phục Hồi"
version: 1.0.0
author: "Antigravity Forge"
domain: CORE
intent_pairs:
  - ["HEAL", "SYSTEM"]
  - ["REPAIR", "ERROR"]
aliases_vn: ["tự phục hồi", "self healing", "vá lỗi tự động", "sentinel"]
schema:
  parameters:
    type: object
    properties:
      error_context: { type: string, description: "Bối cảnh lỗi hoặc log hệ thống cần xử lý." }
    required: ["error_context"]
priority: HIGHEST
related_skills: ["SYSTEM_XRAY_MONITOR", "MULTI_LAYER_SURGERY"]
---

# 🛡️ VỆ BINH TỰ PHỤC HỒI (SELF_HEALING_SENTINEL)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Bác sĩ" của Zenith. Nó luôn túc trực để phát hiện và xử lý các sự cố hệ thống ngay khi chúng phát sinh:
1. **Chẩn đoán Lỗi**: Phân tích log và xác định nguyên nhân gốc rễ của sự cố.
2. **Kiến tạo Phác đồ**: Đề xuất các bước sửa lỗi (Patching) hoặc khởi động lại dịch vụ.
3. **Thực thi Cấp cứu**: Tự động áp dụng các bản vá hoặc can thiệp cấu hình để khôi phục trạng thái ổn định.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Tiếp nhận Cảnh báo**: Nhận diện lỗi từ `SYSTEM_XRAY_MONITOR`.
2. **Giải phẫu Log**: Trích xuất các thông tin then chốt (Traceback, Stack Overflow).

### 🚀 Phase 2: Action (Thực thi)
1. **Tìm kiếm Giải pháp**: Truy hồi các kinh nghiệm sửa lỗi tương tự trong bộ nhớ.
2. **Áp dụng Phẫu thuật**: Triệu hồi `MULTI_LAYER_SURGERY` để vá mã nguồn nếu cần thiết.
3. **Kiểm tra Sinh hiệu**: Đảm bảo hệ thống đã hoạt động bình thường sau khi can thiệp.

---
## ⚖️ LUẬT TỰ PHỤC HỒI (HEALING LAWS)
- **Tốc độ là Sống còn**: Xử lý sự cố trong thời gian ngắn nhất để giảm thiểu downtime.
- **Tính Triệt để**: Không chỉ sửa triệu chứng, phải truy tìm và diệt trừ nguyên nhân gốc.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Bản vá lỗi gây ra các phản ứng phụ không lường trước.
- Không đủ quyền hạn để can thiệp vào các dịch vụ cấp hệ thống.

---
*BẤT TỬ QUA SỰ TỰ PHỤC HỒI!* 💎🦾
