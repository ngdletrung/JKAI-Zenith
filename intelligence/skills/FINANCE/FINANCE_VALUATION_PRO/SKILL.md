---
id: FIN_04_VALUATION
name_vn: "Định Giá Doanh Nghiệp Vĩ Mô"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["VALUATE", "COMPANY"]
  - ["ANALYZE", "EQUITY"]
aliases_vn: ["định giá doanh nghiệp", "valuation", "phân tích cơ bản", "định giá cổ phiếu"]
schema:
  parameters:
    type: object
    properties:
      symbol: { type: string, description: "Mã chứng khoán hoặc tên doanh nghiệp." }
    required: ["symbol"]
priority: NORMAL
related_skills: ["FIN_01_CASHFLOW"]
---

# 🏢 ĐỊNH GIÁ DOANH NGHIỆP VĨ MÔ (FIN_04_VALUATION)

## 🌟 TỔNG QUAN
Kỹ năng này thực hiện định giá giá trị nội tại của doanh nghiệp dựa trên các mô hình tài chính (DCF, P/E, P/B).

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Thu thập Báo cáo**: Tìm kiếm báo cáo tài chính 4 quý gần nhất của `symbol`.
2. **Trinh sát Vĩ mô**: Phân tích ngành và vị thế cạnh tranh của doanh nghiệp.

### 🚀 Phase 2: Action (Thực thi)
1. **Chạy Mô hình**: Áp dụng các phương pháp định giá phù hợp.
2. **Xác định Giá trị**: Trả về mức giá hợp lý và biên an toàn cho Master.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Định giá sai lệch do dữ liệu tài chính đầu vào bị xào nấu (Creative Accounting).
- Sử dụng sai tỷ lệ chiết khấu (Discount Rate).

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
