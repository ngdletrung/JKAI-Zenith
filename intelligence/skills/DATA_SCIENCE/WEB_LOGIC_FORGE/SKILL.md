---
id: WEB_LOGIC_FORGE
name_vn: "Lò Đúc Logic Web Elite"
version: 1.0.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["FORGE", "WEB_LOGIC"]
  - ["CREATE", "WEB_SKILL"]
aliases_vn: ["đúc logic web", "web forge", "tạo kỹ năng web", "neural eye forge"]
schema:
  parameters:
    type: object
    properties:
      domain: { type: string, description: "Phân vùng ứng dụng." }
      skill_name: { type: string, description: "Tên kỹ năng cần đúc." }
      capability: { type: string, description: "Mô tả năng lực của kỹ năng." }
      code: { type: string, description: "Mã nguồn Python cần đúc." }
    required: ["domain", "skill_name", "capability", "code"]
priority: MEDIUM
related_skills: ["SKILL_FORGE", "NEURAL_LINK_AGGREGATOR"]
---

# 🏗️ LÒ ĐÚC LOGIC WEB ELITE (WEB_LOGIC_FORGE)

## 🌟 TỔNG QUAN
Đây là nơ-ron chuyên biệt, dùng để tự động kiến tạo và đăng ký các tập lệnh logic dành cho các tác vụ web. Nó giúp hệ thống mở rộng năng lực tương tác với các nền tảng trực tuyến một cách nhanh chóng bằng cách tự động đúc mã nguồn và cập nhật Registry nội bộ.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Rà soát Phân vùng**: Xác định thư mục Domain đích để lưu trữ tệp tin.
2. **Kiểm tra Mã nguồn**: Đảm bảo đoạn mã Python được cung cấp tuân thủ chuẩn thực thi của Zenith.

### 🚀 Phase 2: Action (Thực thi)
1. **Đúc Logic (Write)**: Ghi tệp Python vào đúng tọa độ trong hệ thống.
2. **Niêm phong Registry**: Cập nhật tệp `registry.json` nội bộ của cụm Web Forge để ghi nhận kỹ năng mới.
3. **Báo cáo Kết quả**: Xác nhận với Master rằng nơ-ron mới đã sẵn sàng phục vụ.

---
## ⚖️ LUẬT KIẾN TẠO (FORGING LAWS)
- **Tính Chính xác Tọa độ**: Phải ghi tệp vào đúng thư mục Domain đã định.
- **Tính Minh bạch**: Phải cập nhật Registry ngay sau khi ghi tệp.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Thiếu quyền ghi tại thư mục đích khiến tiến trình bị chặn.
- Đặt tên kỹ năng trùng lặp gây ghi đè mã nguồn cũ.

---
*KIẾN TẠO ĐỂ VƯƠN XA!* 💎🦾
