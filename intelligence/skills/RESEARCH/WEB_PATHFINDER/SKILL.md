---
id: WEB_PATHFINDER
name_vn: "Hoa Tiêu Dẫn Đường Web"
version: 3.6.0
author: "Antigravity Forge"
domain: RESEARCH
intent_pairs:
  - ["NAVIGATE", "WEB"]
  - ["FIND", "PATH"]
aliases_vn: ["dẫn đường web", "web pathfinder", "hoa tiêu web", "semantic navigation"]
schema:
  parameters:
    type: object
    properties:
      url: { type: string, description: "Địa chỉ khởi đầu." }
      goal: { type: string, description: "Mục tiêu cần tìm hoặc hành động cần thực hiện." }
    required: ["url", "goal"]
priority: HIGH
related_skills: ["SEARCH_WEB_GLOBAL", "AUTONOMOUS_RESEARCHER"]
---

# 🌐 HOA TIÊU DẪN ĐƯỜNG WEB (WEB_PATHFINDER)

## 🌟 TỔNG QUAN
Đây là nơ-ron điều hướng thông minh. Nó có khả năng tự động phân tích cấu trúc trang web và đưa ra các quyết định di chuyển (Click, Scroll, Input) để đạt được mục tiêu cuối cùng mà không cần Master phải chỉ dẫn từng bước.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Phân tích Bối cảnh**: "Nhìn" và hiểu cấu trúc HTML hiện tại của trang web.
2. **Lập lộ trình**: So sánh hiện trạng với `goal` để xác định các nút thắt cần vượt qua.

### 🚀 Phase 2: Action (Thực thi)
1. **Ra quyết định**: Triệu hồi nơ-ron "Hoa Tiêu" để chọn hành động tối ưu (VD: Click vào nút 'Next' hoặc cuộn xuống cuối trang).
2. **Theo dõi Tiến độ**: Lặp lại quy trình cho đến khi đạt được mục tiêu hoặc đạt giới hạn 5 bước.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Bị lạc đường do trang web có cấu trúc quá phức tạp hoặc sử dụng nhiều mã độc.
- Đạt giới hạn bước đi (Max Steps) trước khi tìm thấy mục tiêu.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
