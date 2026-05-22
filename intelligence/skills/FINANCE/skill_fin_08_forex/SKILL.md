---
id: FIN_08_FOREX
name_vn: "Giao Dịch Ngoại Hối Elite"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["TRADE", "FOREX"]
  - ["ANALYZE", "CURRENCY"]
aliases_vn: ["giao dịch ngoại hối", "forex trade", "tỷ giá ngoại tệ", "fx analysis"]
schema:
  parameters:
    type: object
    properties:
      currency_pair: { type: string, description: "Cặp tiền tệ cần phân tích (VD: EUR/USD)." }
    required: ["currency_pair"]
priority: NORMAL
related_skills: ["FIN_02_TECH_ANALYSIS", "FIN_05_SENTIMENT"]
---

# 💱 GIAO DỊCH NGOẠI HỐI ELITE (FIN_08_FOREX)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm phân tích tỷ giá và các yếu tố ảnh hưởng đến thị trường ngoại hối toàn cầu.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Kiểm tra Tỷ giá**: Truy vấn tỷ giá hối đoái thời gian thực cho `currency_pair`.
2. **Quét Tin tức Vĩ mô**: Phân tích các thông tin từ Ngân hàng Trung ương (Fed, ECB, BoJ) liên quan đến cặp tiền.

### 🚀 Phase 2: Action (Thực thi)
1. **Định hướng Chiến thuật**: Kết hợp phân tích kỹ thuật và tin tức để đưa ra điểm vào/ra lệnh.
2. **Quản trị Rủi ro**: Tính toán mức độ biến động (Volatility) để bảo vệ vốn.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Giao dịch trong thời điểm công bố tin tức đỏ gây trượt giá mạnh.
- Không tính đến phí Swap và chênh lệch Spread của sàn giao dịch.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
