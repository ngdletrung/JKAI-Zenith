---
id: SKILL_FORGE
name_vn: "Lò Đúc Kỹ Năng Sovereign"
version: 32.0.0
author: "Antigravity Forge"
domain: CORE
intent_pairs:
  - ["FORGE", "SKILL"]
  - ["CREATE", "CAPABILITY"]
aliases_vn: ["lò đúc", "tạo kỹ năng", "skill forge", "kiến tạo năng lực"]
schema:
  parameters:
    type: object
    properties:
      skill_description: { type: string, description: "Mô tả chi tiết năng lực của kỹ năng cần kiến tạo." }
    required: ["skill_description"]
priority: HIGHEST
related_skills: ["SYNC_KNOWLEDGE", "SKILL_SYSTEM_CORE"]
---

# 🛠️ LÒ ĐÚC KỸ NĂNG SOVEREIGN (SKILL_FORGE)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Sinh sản" của hệ thống Zenith. Nó cho phép hệ thống tự động kiến tạo, cấu hình và đăng ký các kỹ năng mới dựa trên yêu cầu ngôn ngữ tự nhiên của Master. Mọi kỹ năng được đúc ra đều tuân thủ chuẩn **Nhất Thể 2-File**.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Phân tích Nghiệp vụ**: Thấu hiểu mục tiêu kỹ năng từ `skill_description`.
2. **Thiết kế Nơ-ron**: Triệu hồi Ban Kế hoạch (PLANNER) để thiết kế cấu trúc `logic.py` và `SKILL.md` bao gồm cả Schema YAML.

### 🚀 Phase 2: Action (Thực thi)
1. **Đúc & Niêm phong**: Ghi mã nguồn và hiến chương vào thư mục Domain tương ứng.
2. **Đăng ký Chủ quyền**: Tự động cập nhật `registry.json` và `MAP_SKILLS.md` để Đặc vụ Dispatcher có thể nhận diện ngay lập tức.

---
## ⚖️ LUẬT ĐÚC (FORGING LAWS)
- **Cấm 4-Tệp**: Tuyệt đối không tạo ra các tệp `manual.md`, `workflow.md`, `schema.json`.
- **Nhất Thể Hóa**: Mọi thông tin phải nằm trong 2 tệp `logic.py` và `SKILL.md`.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Mô tả kỹ năng quá mơ hồ khiến AI đúc ra logic không chính xác.
- Đặt tên kỹ năng trùng lặp với các ID hiện có trong Registry.

---
*KIẾN TẠO ĐỂ TRƯỜNG TỒN!* 💎🦾
