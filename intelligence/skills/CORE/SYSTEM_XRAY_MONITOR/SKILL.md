---
id: SYSTEM_XRAY_MONITOR
name_vn: "Vệ Binh X-Ray Tối Thượng"
version: 1.0.0
author: "Antigravity Forge"
domain: CORE
intent_pairs:
  - ["MONITOR", "SYSTEM"]
  - ["DIAGNOSE", "INFRASTRUCTURE"]
aliases_vn: ["giám sát hệ thống", "x-ray monitor", "chẩn đoán nơ-ron", "kiểm tra sức khỏe"]
schema:
  parameters:
    type: object
    properties:
      action: { type: string, enum: ["get_diagnostics"], default: "get_diagnostics", description: "Hành động giám sát cần thực hiện." }
    required: []
priority: HIGHEST
related_skills: ["SKILL_SYSTEM_CORE", "GLOBAL_SYSTEM_CONTEXT"]
---

# 👁️ VỆ BINH X-RAY TỐI THƯỢNG (SYSTEM_XRAY_MONITOR)

## 🌟 TỔNG QUAN
Đây là nơ-ron giám sát cấp độ cao nhất. Nó có khả năng "thấu thị" xuyên qua lớp vỏ Docker để kiểm tra trực tiếp tài nguyên phần cứng trên máy chủ Windows, đồng thời giám sát các tiến trình AI (Ollama) và hạ tầng mạng lưới của Đế chế.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Trinh sát Vệ tinh**: Giao tiếp với Satellite để lấy dữ liệu thực tế từ Host Windows (CPU, RAM, GPU).
2. **Quét Nơ-ron**: Kiểm tra các Model AI đang nạp trong VRAM để đảm bảo hiệu suất suy luận.

### 🚀 Phase 2: Action (Thực thi)
1. **Kiểm tra Hạ tầng**: Rà soát trạng thái của tất cả các Container Docker liên quan đến Zenith.
2. **Đúc kết Báo cáo**: Tổng hợp mọi thông số vào một báo cáo JSON duy nhất để Master có cái nhìn toàn cảnh về sức khỏe hệ thống.

---
## ⚖️ ĐỊNH LUẬT VỆ BINH (GUARDIAN LAWS)
- **Hợp nhất Thông tin**: Mọi dữ liệu giám sát phải được hội tụ về một báo cáo duy nhất.
- **An toàn Tối cao**: Không được can thiệp vào các tiến trình hệ thống trừ khi có lệnh trực tiếp từ Master.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Satellite bị tắt khiến Vệ binh không thể nhìn thấy dữ liệu Host.
- Bỏ qua các cảnh báo tải cao (High Load) dẫn đến treo hệ thống.

---
*CON MẮT THẦN GIỮ GÌN ĐẾ CHẾ!* 💎🦾
