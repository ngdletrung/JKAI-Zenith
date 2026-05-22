---
id: FIN_02_TECH_ANALYSIS
name_vn: "Phân Tích Kỹ Thuật Elite"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["ANALYZE", "TECHNICAL"]
  - ["PREDICT", "MARKET"]
aliases_vn: ["phân tích kỹ thuật", "tech analysis", "soi kèo", "dự báo thị trường"]
schema:
  parameters:
    type: object
    properties:
      query: { type: string, description: "Cặp giao dịch hoặc mã cổ phiếu cần phân tích (VD: BTC/USDT)." }
    required: ["query"]
priority: NORMAL
related_skills: ["FIN_01_CASHFLOW", "AGENT-TRADING-PREDICTOR"]
---

# 📈 PHÂN TÍCH KỸ THUẬT ELITE (FIN_02_TECH_ANALYSIS)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm phân tích các chỉ số kỹ thuật (RSI, EMA, Trendline) để đưa ra các nhận định về xu hướng thị trường.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Xác định Đối tượng**: Nhận diện mã tài sản cần phân tích từ `query`.
2. **Quét dữ liệu**: Truy vấn dữ liệu nến (OHLC) từ các nguồn cung cấp tích hợp.

### 🚀 Phase 2: Action (Thực thi)
1. **Tính toán Chỉ số**: Triệu hồi thuật toán phân tích kỹ thuật.
2. **Đưa ra Khuyến nghị**: Đúc kết báo cáo về xu hướng và các vùng hỗ trợ/kháng cự quan trọng.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Phân tích sai lệch do dữ liệu nến bị trễ (Lag).
- Bỏ qua các tin tức vĩ mô có thể phá vỡ mọi chỉ báo kỹ thuật.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
