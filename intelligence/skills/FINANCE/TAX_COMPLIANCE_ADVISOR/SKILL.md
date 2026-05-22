---
id: FIN_10_TAX
name_vn: "Tư Vấn Thuế & Pháp Lý Tài Chính"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["ADVISE", "TAX"]
  - ["COMPLIANCE", "LEGAL"]
aliases_vn: ["tư vấn thuế", "quy định tài chính", "quyền lợi pháp lý", "tax advisor"]
schema:
  parameters:
    type: object
    properties:
      region: { type: string, description: "Khu vực hoặc quốc gia cần tư vấn thuế." }
      income_source: { type: string, description: "Nguồn thu nhập cần kê khai." }
    required: ["region"]
priority: NORMAL
related_skills: ["FIN_01_CASHFLOW"]
---

# ⚖️ TƯ VẤN THUẾ & PHÁP LÝ TÀI CHÍNH (FIN_10_TAX)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm cập nhật các quy định về thuế và tính tuân thủ pháp lý trong các hoạt động tài chính của Master.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Quét Luật**: Truy cập cơ sở dữ liệu luật pháp của `region` để tìm các quy định mới nhất.
2. **Đối chiếu Thu nhập**: Phân tích `income_source` để xác định khung thuế áp dụng.

### 🚀 Phase 2: Action (Thực thi)
1. **Lập kế hoạch Thuế**: Đề xuất các phương án tối ưu thuế hợp pháp.
2. **Cảnh báo Tuân thủ**: Nhắc nhở các thời hạn kê khai và rủi ro pháp lý nếu có.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Áp dụng các quy định cũ đã hết hiệu lực.
- Thiếu hiểu biết về các hiệp ước tránh đánh thuế hai lần giữa các quốc gia.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
