# 🏛️ ZENITH SOVEREIGN SKILL PROTOCOL (V1.0)
**Giao thức Định danh và Vận hành Kỹ năng Tối thượng**

---

## ⚖️ TRIẾT LÝ CỐT LÕI (CORE PRINCIPLES)
1. **Macro-Consistency**: Không chấp nhận các kỹ năng "vá tạm". Mọi kỹ năng phải tuân thủ cấu trúc định danh chuẩn hóa.
2. **Deterministic Retrieval**: AI không "đoán" kỹ năng. AI khớp kỹ năng dựa trên `Intent Pairs` và `Universal IDs`.
3. **Bilingual Bridge**: Kỹ năng được định danh bằng tiếng Anh (logic) nhưng giao tiếp thâm sâu bằng tiếng Việt (soul).
4. **Autonomous Flow**: Mỗi kỹ năng phải chứa đựng một "Giao thức vận hành" (Protocol) rõ ràng để AI thực thi không sai sót.

---

## 📂 CẤU TRÚC THƯ MỤC (DIRECTORY STRUCTURE)
Mọi kỹ năng phải được đặt trong thư mục riêng biệt theo phân cấp Domain:
`intelligence/skills/[DOMAIN]/[UNIVERSAL_SKILL_ID]/`

**Ví dụ**:
`intelligence/skills/RESEARCH/SEARCH_WEB_GLOBAL/`
├── `SKILL.md` (Manifest & Protocol chính)
├── `examples/` (Các ví dụ thực tế - Tùy chọn)
└── `tools/` (Các công cụ/script bổ trợ riêng - Tùy chọn)

---

## 📝 QUY CHUẨN SKILL.MD (MANIFEST SCHEMA v2.0)
Mọi tệp `SKILL.md` PHẢI bắt đầu bằng khối YAML metadata Nhất thể sau:

```yaml
---
id: UNIVERSAL_SKILL_ID
name_vn: "Tên kỹ năng Elite"
version: 2.0.0
domain: [DOMAIN_NAME]
intent_pairs:
  - ["ACTION", "OBJECT"]
aliases_vn: ["bí danh 1", "bí danh 2"]
schema:                        # 💎 [NEW]: Thay thế hoàn toàn schema.json
  parameters:
    type: object
    properties:
      param1: { type: string, description: "Mô tả tham số" }
    required: ["param1"]
priority: HIGH
related_skills: ["ID_1", "ID_2"]
---
```

### ⚖️ TIÊU CHUẨN "NHẤT THỂ 2 FILE"
- **Luật**: Mỗi kỹ năng chỉ gồm `logic.py` và `SKILL.md`.
- **Cấm**: Tuyệt đối không dùng `schema.json`, `manual.md`, `workflow.md`.

---

## 🛠️ QUY TRÌNH VẬN HÀNH (OPERATIONAL PROTOCOL)
Bên dưới khối YAML, nội dung `SKILL.md` phải chia thành các Phase rõ ràng:

1. **Phase 1: Investigation (Thẩm định)**: AI cần thu thập dữ liệu gì trước khi làm?
2. **Phase 2: Action (Thực thi)**: Các bước thực hiện cụ thể kèm `Tool Call` mẫu.
3. **Phase 3: Validation (Xác minh)**: Làm sao biết đã thành công?
4. **Phase 4: Reporting (Đúc kết)**: Cách trình bày kết quả cho Master.

---

## 🚀 GIAO THỨC ĐỒNG HÓA (ASSIMILATION)
* **RAM Loading**: Hệ thống sẽ quét toàn bộ khối YAML và nạp vào Redis hàng giờ hoặc sau khi có lệnh `/sync`.
* **MapGraph Injection**: Các `related_skills` sẽ được kết nối để tạo thành "Chuỗi nhận thức" (Cognitive Chain) trong bộ não của Zenith.

---
**NGHIÊM CẤM**: Đặt tên file tùy tiện hoặc thiếu khối YAML Manifest. Vi phạm sẽ bị hệ thống loại bỏ khỏi Registry.
