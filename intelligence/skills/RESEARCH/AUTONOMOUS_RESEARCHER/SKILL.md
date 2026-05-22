---
id: AUTONOMOUS_RESEARCHER
name_vn: "Đặc Vụ Nghiên Cứu Tự Trị"
version: 1.5.0
author: "Antigravity Forge"
domain: RESEARCH
intent_pairs:
  - ["RESEARCH", "DEEP_DIVE"]
  - ["ANALYZE", "TOPIC"]
aliases_vn: ["nghiên cứu sâu", "autonomous researcher", "tầm soát tri thức", "báo cáo nghiên cứu"]
schema:
  parameters:
    type: object
    properties:
      topic: { type: string, description: "Chủ đề cần nghiên cứu chuyên sâu." }
    required: ["topic"]
priority: HIGH
related_skills: ["SEARCH_WEB_GLOBAL", "SYNC_KNOWLEDGE"]
---

# 🕵️ ĐẶC VỤ NGHIÊN CỨU TỰ TRỊ (AUTONOMOUS_RESEARCHER)

## 🌟 TỔNG QUAN
Đây là nơ-ron nghiên cứu cấp độ chuyên gia, có khả năng tự động trinh sát Internet, đọc sâu nội dung và đúc kết thành các báo cáo chiến lược. Kỹ năng này không chỉ tìm kiếm mà còn **tư duy** dựa trên dữ liệu thu thập được.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Trinh sát Internet**: Sử dụng Tavily API để lọc ra 3 nguồn dữ liệu uy tín nhất liên quan đến `topic`.
2. **Thấu thị Nội dung**: Sử dụng Jina Reader để đọc sâu và bóc tách văn bản thô từ các URL mục tiêu.

### 🚀 Phase 2: Action (Thực thi)
1. **Tổng hợp Chiến lược**: Triệu hồi Ban Kế hoạch (PLANNER) để phân tích và đúc kết báo cáo theo cấu trúc chuẩn Corporate (Bối cảnh, Phân tích, Đề xuất).
2. **Lưu trữ vĩnh cửu**: Ghi báo cáo vào thư mục `vault` để bảo tồn tri thức cho Đế chế.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Topic quá rộng dẫn đến báo cáo bị loãng nơ-ron.
- Thiếu API Key Tavily sẽ khiến Đặc vụ bị "mù thông tin" Internet.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
