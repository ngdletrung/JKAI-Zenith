---
id: FIN_09_ARBITRAGE
name_vn: "Giao Dịch Chênh Lệch Giá"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["TRADE", "ARBITRAGE"]
  - ["SCAN", "PRICE_GAP"]
aliases_vn: ["giao dịch chênh lệch giá", "arbitrage", "price gap scanner"]
schema:
  parameters:
    type: object
    properties:
      asset: { type: string, description: "Tài sản cần quét chênh lệch giá." }
    required: ["asset"]
priority: NORMAL
related_skills: ["FIN_03_WHALE_TRACK", "SEARCH_WEB_GLOBAL"]
---

# ⚖️ GIAO DỊCH CHÊNH LỆCH GIÁ (FIN_09_ARBITRAGE)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm tầm soát sự khác biệt về giá của cùng một loại tài sản trên các sàn giao dịch khác nhau để thực thi các lệnh mua thấp bán cao tức thì.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Quét Sàn**: Truy vấn giá của `asset` trên danh sách các sàn giao dịch (CEX/DEX) được Master chỉ định.
2. **Tính toán Phí**: Trừ đi phí giao dịch và phí chuyển tiền (Transfer fee) để xác định lợi nhuận ròng.

### 🚀 Phase 2: Action (Thực thi)
1. **Báo động Cơ hội**: Phát tín hiệu khi mức chênh lệch đạt ngưỡng có lợi.
2. **Kích hoạt Lệnh**: Thực hiện mua ở sàn giá thấp và bán ở sàn giá cao đồng thời.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Trượt giá (Slippage) trong lúc chuyển tài sản giữa các sàn.
- Nghẽn mạng Blockchain khiến giao dịch không kịp thực thi tại mức giá mục tiêu.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
