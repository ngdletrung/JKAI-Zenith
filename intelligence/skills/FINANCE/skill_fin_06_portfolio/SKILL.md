---
id: FIN_06_PORTFOLIO
name_vn: "Tối Ưu Danh Mục Đầu Tư"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["OPTIMIZE", "PORTFOLIO"]
  - ["REBALANCE", "ASSETS"]
aliases_vn: ["tối ưu danh mục", "quản lý tài sản", "rebalance portfolio", "phân bổ vốn"]
schema:
  parameters:
    type: object
    properties:
      risk_level: { type: string, enum: ["LOW", "MEDIUM", "HIGH"], description: "Mức độ chấp nhận rủi ro của Master." }
    required: ["risk_level"]
priority: NORMAL
related_skills: ["FIN_04_VALUATION", "FIN_02_TECH_ANALYSIS"]
---

# 📊 TỐI ƯU DANH MỤC ĐẦU TƯ (FIN_06_PORTFOLIO)

## 🌟 TỔNG QUAN
Kỹ năng này giúp Master phân bổ vốn và tái cấu trúc danh mục đầu tư (Rebalance) để đạt được tỷ suất lợi nhuận tối ưu ứng với mức rủi ro cho phép.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Kiểm kê Tài sản**: Liệt kê toàn bộ các vị thế đang nắm giữ trong danh mục.
2. **Tính toán Tương quan**: Phân tích sự tương quan giữa các lớp tài sản (Correlation) để giảm thiểu rủi ro hệ thống.

### 🚀 Phase 2: Action (Thực thi)
1. **Mô hình hóa Markowitz**: Sử dụng lý thuyết danh mục hiện đại để tìm điểm tối ưu.
2. **Đề xuất Tái cơ cấu**: Đưa ra các lệnh mua/bán cụ thể để đưa danh mục về trạng thái cân bằng.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Tập trung quá nhiều vào một lớp tài sản (Over-concentration) gây rủi ro lớn.
- Tái cơ cấu quá thường xuyên dẫn đến lãng phí phí giao dịch.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
