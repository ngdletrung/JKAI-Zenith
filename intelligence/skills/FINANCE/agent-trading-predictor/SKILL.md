---
id: AGENT-TRADING-PREDICTOR
name_vn: "Đặc Vụ Dự Báo Giao Dịch"
version: 2.0.0
author: "Antigravity Forge"
domain: FINANCE
intent_pairs:
  - ["PREDICT", "TRADING"]
  - ["CONSULT", "FINANCE"]
aliases_vn: ["dự báo giao dịch", "trading predictor", "tư vấn đầu tư"]
schema:
  parameters:
    type: object
    properties:
      prompt: { type: string, description: "Yêu cầu dự báo hoặc phân tích thị trường." }
    required: ["prompt"]
priority: NORMAL
related_skills: ["FIN_02_TECH_ANALYSIS", "FIN_05_SENTIMENT"]
---

# 💹 ĐẶC VỤ DỰ BÁO GIAO DỊCH (AGENT-TRADING-PREDICTOR)

## 🌟 TỔNG QUAN
Đây là đặc vụ tư duy chuyên sâu về thị trường tài chính. Nó sử dụng nơ-ron Tầng 2 để tổng hợp tri thức và đưa ra các nhận định dự báo dựa trên bối cảnh thị trường hiện tại.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Phân tích Yêu cầu**: Trích xuất các tham số giao dịch từ `prompt`.
2. **Truy vấn Tri thức**: Triệu hồi nơ-ron Tầng 2 (Knowledge Brain) để tìm kiếm các mẫu hình lịch sử liên quan.

### 🚀 Phase 2: Action (Thực thi)
1. **Đúc kết Nhận định**: Trả về dự báo chi tiết và các rủi ro tiềm ẩn.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Dự báo chỉ mang tính tham khảo, không phải là lời khuyên tài chính tuyệt đối.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
