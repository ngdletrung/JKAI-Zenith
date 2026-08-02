<!-- 
[ZENITH FILE DIRECTIVE]
- File: SKILL_PROTOCOL.md
- Role: Zenith Intelligence Documentation.
- Ownership: Mr LeeTrung
- Status: Active | Version: SDS v19.9
[WORKING PRINCIPLES]:
1. [HEADER-FIRST]: Antigravity BAT BUOC phai doc khoi header nay truoc khi thao tac.
2. [ID-GOVERNANCE]: Tuyệt đối tuân thủ dải ID phân khu (10xx: Core, 2xxx: Data, 3xxx: Dev...).
3. [DIRECTORY-MAPPING]: Kỹ năng phải nằm đúng thư mục domain tương ứng.
4. [SSoT-SYNC]: Mọi thay đổi vật lý phải được đồng bộ vào Registry trung tâm.
-->
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

### 🆔 QUẢN TRỊ ID (ID GOVERNANCE)
Hệ thống sử dụng dải ID 4 chữ số để phân loại nơ-ron:
- **10xx**: CORE & INFRASTRUCTURE (Hạ tầng & Hệ thống).
- **20xx**: DATA & AI SCIENCE (Trí tuệ nhân tạo & Dữ liệu).
- **30xx**: DEV & ENGINEERING (Kỹ thuật phần mềm).
- **35xx**: DEVOPS & AUTOMATION (Vận hành & Tự động hóa).
- **40xx**: RESEARCH (Nghiên cứu & Khám phá).
- **50xx**: BUSINESS & STRATEGY (Kinh doanh & Chiến lược).
- **60xx**: SECURITY & VAULT (An ninh & Bảo mật).
- **70xx**: HUEIC PROCESS (Quy trình hành chính HUEIC).
- **80xx**: TOOLS & UTILITIES (Công cụ hỗ trợ).

### 📁 PHÂN BỔ THƯ MỤC (DIRECTORY ALLOCATION)
Mọi kỹ năng PHẢI được lưu trữ theo cấu trúc:
`intelligence/skills/[DOMAIN]/[SKILL_ID]/`
- **[DOMAIN]**: Trùng khớp với dải ID (ví dụ: `CORE`, `DATA_SCIENCE`, `SECURITY`).
- **[SKILL_ID]**: Viết hoa, phân cách bằng dấu gạch dưới (Snake Case).
├── `logic.py` (Logic thực thi Python)
├── `SKILL.md` (Manifest & Schema YAML)
├── `dossier.md` (Hồ sơ năng lực & Tính năng chi tiết)
├── `manifest.json` (Cầu nối tương thích hệ thống)
├── `__init__.py` (Chứng chỉ Package)
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
assigned_agent: Zenith_Executor      # 🤖 [NEW]: Agent ưu tiên thực hiện kỹ năng này
priority: HIGH
related_skills: ["ID_1", "ID_2"]
---
```

### ⚖️ TIÊU CHUẨN "NHẤT THỂ 5 FILE" (ELITE STANDARD)
- **Luật**: Mỗi kỹ năng PHẢI gồm đủ 5 file để đảm bảo tính Thấu thị và Chiến lược:
    1. `logic.py`: Logic thực thi Python.
    2. `SKILL.md`: Manifest & Schema (YAML).
    3. `dossier.md`: Hồ sơ năng lực & Tính năng chi tiết (Soul).
    4. `manifest.json`: Cầu nối tương thích hệ thống.
    5. `__init__.py`: Chứng chỉ Package Python.
- **Cấm**: Tuyệt đối không đặt tên file tùy tiện hoặc thiếu một trong 5 file trên.

---

## 🛠️ QUY TRÌNH VẬN HÀNH & KỶ LUẬT (OPERATIONAL WORKFLOW & DISCIPLINE)
Bên dưới khối YAML, nội dung `SKILL.md` đóng vai trò là prompt vận hành chính (Operational Prompt) và PHẢI chứa các cấu phần sau để đảm bảo kỷ luật kỹ nghệ:

1. **OPERATIONAL WORKFLOW (Quy trình thực thi chi tiết)**: Chia thành các bước rõ ràng:
   - *Phase 1: Investigation (Khảo sát/Thẩm định)*: Xác định thông tin cần thu thập (lệnh đọc file, grep cụ thể) trước khi thực hiện bất kỳ chỉnh sửa nào.
   - *Phase 2: Action (Thực thi)*: Các bước triển khai cụ thể kèm Tool Call mẫu.
   - *Phase 3: Validation (Xác minh)*: Các bước chạy thử nghiệm, biên dịch (lệnh cụ thể).
   - *Phase 4: Reporting (Đúc kết)*: Cách trình bày bằng chứng và kết quả cho Master.

2. **ANTI-RATIONALIZATION (Chống ngụy biện - Excuse vs Counter Argument)**:
   Bảng quy tắc phản biện chống việc Executor tự hợp lý hóa để bỏ qua các bước quan trọng (ví dụ: "code nhỏ khỏi chạy test").

3. **EXIT CRITERIA & EVIDENCE (Tiêu chí hoàn thành & Bằng chứng)**:
   Checklist bắt buộc và các bằng chứng thực tế (test reports, linter outputs, runtime validation log) cần bàn giao.


---

## 🧬 GIAO THỨC PHỐI HỢP SWARM (SWARM SYNERGY PROTOCOL)
Để tối ưu hóa Trí tuệ bầy đàn, các kỹ năng phải tuân thủ cơ chế chuyển giao:
1. **Lập trận (Planner)**: Nhận diện Skill cần thiết dựa trên `intent_pairs` và thiết lập tham số đầu vào.
2. **Triển khai (Executor)**: Được chỉ định qua `assigned_agent`, thực hiện các bước trong Phase 2.
3. **Thẩm định (Critic)**: Đối soát kết quả đầu ra của Skill với tiêu chuẩn trong Phase 3.
4. **Ghi nhớ (Memory)**: Lưu trữ các "Edge cases" gặp phải trong quá trình dùng Skill vào Ký ức Swarm.

---

## 🚀 GIAO THỨC ĐỒNG HÓA (ASSIMILATION)
* **RAM Loading**: Hệ thống sẽ quét toàn bộ khối YAML và nạp vào Redis hàng giờ hoặc sau khi có lệnh `/sync`.
* **MapGraph Injection**: Các `related_skills` sẽ được kết nối để tạo thành "Chuỗi nhận thức" (Cognitive Chain) trong bộ não của Zenith.

---
**NGHIÊM CẤM**: Đặt tên file tùy tiện hoặc thiếu khối YAML Manifest. Vi phạm sẽ bị hệ thống loại bỏ khỏi Registry.
