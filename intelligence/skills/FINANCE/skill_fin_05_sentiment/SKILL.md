---
id: FIN_05_SENTIMENT
name_vn: "Phân Tích Tâm Lý Thị Trường"
version: 1.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["ANALYZE", "SENTIMENT"]
  - ["SCAN", "SOCIAL_MEDIA"]
aliases_vn: ["tâm lý thị trường", "market sentiment", "đo lường nỗi sợ", "fear and greed"]
schema:
  parameters:
    type: object
    properties:
      asset: { type: string, description: "Tên tài sản hoặc thị trường cần đo lường tâm lý." }
    required: ["asset"]
priority: NORMAL
related_skills: ["FIN_02_TECH_ANALYSIS", "SEARCH_WEB_GLOBAL"]
---

# 🧠 PHÂN TÍCH TÂM LÝ THỊ TRƯỜNG (FIN_05_SENTIMENT)

## 🌟 TỔNG QUAN
Kỹ năng này chịu trách nhiệm "đọc vị" đám đông bằng cách phân tích dữ liệu từ mạng xã hội, tin tức và các chỉ số Sợ hãi & Tham lam (Fear & Greed).

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Quét Tin tức**: Truy vấn các từ khóa liên quan đến `asset` trên X (Twitter), Reddit và các trang tin tài chính.
2. **Phân tích Cảm xúc**: Sử dụng nơ-ron NLP để phân loại thái độ (Tích cực, Tiêu cực, Trung lập).

### 🚀 Phase 2: Action (Thực thi)
1. **Tính toán Chỉ số**: Tổng hợp điểm số tâm lý (Sentiment Score).
2. **Cảnh báo Đảo chiều**: Nhận diện các vùng "Quá hưng phấn" hoặc "Quá sợ hãi" để cảnh báo Master.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Bị nhiễu bởi các tin tức giả (FUD/FOMO) từ các đội nhóm lái giá.
- Tâm lý đám đông có thể duy trì trạng thái phi lý trí lâu hơn mức dự kiến.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
