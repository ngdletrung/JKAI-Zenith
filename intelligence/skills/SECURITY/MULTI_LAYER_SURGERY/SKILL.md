---
id: MULTI_LAYER_SURGERY
name_vn: "Phẫu Thuật Đa Tầng Quantum"
version: 31.5.0
author: "Antigravity Forge"
domain: SECURITY
intent_pairs:
  - ["SURGERY", "MULTI_POINT"]
  - ["EDIT", "CODE_STRUCTURE"]
aliases_vn: ["phẫu thuật đa tầng", "quantum surgery", "chỉnh sửa mã nguồn", "multi-point edit"]
schema:
  parameters:
    type: object
    properties:
      path: { type: string, description: "Đường dẫn tuyệt đối hoặc tương đối tới tệp tin cần phẫu thuật." }
      chunks:
        type: array
        items:
          type: object
          properties:
            target: { type: string, description: "Đoạn mã mục tiêu cần thay thế (phải khớp chính xác 100%)." }
            replacement: { type: string, description: "Đoạn mã mới sẽ được cấy ghép vào." }
          required: ["target", "replacement"]
      validate_syntax: { type: boolean, default: true, description: "Tự động kiểm tra cú pháp Python sau khi phẫu thuật." }
    required: ["path", "chunks"]
priority: HIGHEST
related_skills: ["SKILL_SYSTEM_CORE", "QUANTUM_CODE_AUDIT"]
---

# 🏥 PHẨU THUẬT ĐA TẦNG QUANTUM (PHAU_THUAT_DATANG)

## 🌟 TỔNG QUAN
Đây là kỹ năng can thiệp mã nguồn cấp độ cao nhất. Nó cho phép thực hiện thay thế đồng thời nhiều đoạn mã không liên tục trong một tệp tin với độ chính xác tuyệt đối và cơ chế bảo vệ cú pháp tự động.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Trinh sát Mục tiêu**: Sử dụng `view_file` để xác định chính xác các đoạn mã `target` bao gồm cả khoảng trắng và thụt đầu dòng.
2. **Kiểm tra Quyền hạn**: Đảm bảo tệp tin không nằm trong danh sách **IMMUTABLE** (Bất khả xâm phạm).

### 🚀 Phase 2: Action (Thực thi)
1. **Cấy ghép Chunks**: Gửi danh sách các mảnh ghép `target` và `replacement`.
2. **Syntax Check & Commit**: Hệ thống tự động kiểm tra `ast.parse` và tạo bản sao lưu trước khi ghi đè an toàn.

---
## ⚖️ ĐỊNH LUẬT BẢO TOÀN (IMMUTABLE LAWS)
- Cấm AI chỉnh sửa: `watchdog.py`, `main.py`, `hitl_manager.py`, `SOVEREIGN_CORE.py`.
- Mọi sai sót cú pháp sẽ dẫn đến việc **HỦY BỎ** toàn bộ ca phẫu thuật.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Target quá ngắn ( < 10 ký tự) dẫn đến thay thế nhầm vị trí.
- Không khớp Indentation (khoảng trắng đầu dòng) khiến ca phẫu thuật thất bại.

---
*KỶ LUẬT TẠO NÊN SỰ CHÍNH XÁC!* 💎🦾
