---
id: IMPORT_SKILL
name_vn: "Nhập Khẩu Kỹ Năng Mới (Import Skill)"
version: 2.1.0
author: "Antigravity Forge"
domain: CORE
intent_pairs:
  - ["SYNC", "KNOWLEDGE"]
  - ["ASSIMILATE", "SKILLS"]
aliases_vn: ["đồng bộ tri thức", "knowledge sync", "đồng hóa kỹ năng", "import skills"]
schema:
  parameters:
    type: object
    properties:
      mode: { type: string, enum: ["full", "incremental"], description: "Chế độ đồng bộ." }
    required: []
priority: HIGH
related_skills: ["SKILL_FORGE", "GLOBAL_SYSTEM_CONTEXT"]
---

# 📦 IMPORT_SKILL: Nhập Khẩu Kỹ Năng Mới

## 🌟 TỔNG QUAN
Đây là nơ-ron chịu trách nhiệm đồng hóa các tri thức mới từ bên ngoài vào hệ sinh thái Zenith. Nó tự động quét, thẩm định an ninh và phân loại các kỹ năng mới được đưa vào thư mục "Dumping Ground" (import_dump).

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Trinh sát Kho chứa**: Quét thư mục `archive/import_dump` để tìm các "mầm mống" tri thức mới.
2. **Thẩm định An ninh**: Kiểm tra mã nguồn để đảm bảo không có mã độc hoặc các lệnh can thiệp trái phép vào hệ thống.

### 🚀 Phase 2: Action (Thực thi)
1. **Tự động Soạn thảo**: Triệu hồi Lò đúc để tự động tạo Hiến chương `SKILL.md` chuẩn Sovereign cho tri thức mới.
2. **Di cư & Phân loại**: Chuyển kỹ năng vào đúng Domain (CORE, FINANCE, RESEARCH, v.v.) và cập nhật Registry toàn cục.

---
## ⚖️ ĐỊNH LUẬT ĐỒNG HÓA (ASSIMILATION LAWS)
- Chỉ đồng hóa các kỹ năng có tệp `logic.py` hợp lệ.
- Mọi kỹ năng không vượt qua bài kiểm tra an ninh sẽ bị niêm phong tại thư mục `quarantine`.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Thư mục `import_dump` quá lớn gây nghẽn tiến trình đồng bộ.
- Thiếu quyền ghi (Write Permission) tại các thư mục Domain đích.

---
*TRI THỨC LÀ QUYỀN LỰC TỐI THƯỢNG!* 💎🦾
