---
id: noi_chuyen_voi_AI
name_vn: "Nói Chuyện Với AI"
version: 1.5.0
author: "Antigravity Forge"
domain: DATA_SCIENCE
intent_pairs:
  - ["SUMMON", "GODS"]
  - ["AGGREGATE", "INTELLIGENCE"]
aliases_vn: ["neural link", "hợp nhất AI", "triệu hồi AI", "siêu AI aggregator", "nói chuyện với AI"]
schema:
  parameters:
    type: object
    properties:
      goal: { type: string, description: "Mục tiêu hoặc câu hỏi cần các Siêu AI giải quyết." }
      preferred_provider: { type: string, enum: ["openai", "anthropic", "google", "deepseek"], description: "Nhà cung cấp ưu tiên." }
    required: ["goal"]
priority: HIGHEST
related_skills: ["SAFLA_MEMORY_ENGINE", "GLOBAL_SYSTEM_CONTEXT"]
---

# 🔗 NÓI CHUYỆN VỚI AI (noi_chuyen_voi_AI)

## 🌟 TỔNG QUAN
Đây là nơ-ron "Ngoại giao" cấp cao. Nó cho phép Zenith kết nối và trò chuyện, trao đổi trí tuệ với các thực thể AI mạnh nhất thế giới (Claude, GPT, Gemini, DeepSeek) để giải quyết các vấn đề vĩ mô. Đặc biệt, nó được tích hợp **GHOST PROTOCOL** để đảm bảo mọi truy vấn của Master đều được ẩn danh và xóa dấu vết ngay sau khi thực thi.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định)
1. **Rà soát Khóa Thần kinh**: Kiểm tra trạng thái các API Keys trong `rules_software.md`.
2. **Kích hoạt Ghost Masking**: Sử dụng GHOST PROTOCOL để che giấu mục tiêu thực sự của Master trước khi gửi đến các nhà cung cấp ngoại lai.

### 🚀 Phase 2: Action (Thực thi)
1. **Triệu hồi Đa cực**: Gửi truy vấn đồng thời đến nhiều Siêu AI để lấy các góc nhìn khác nhau.
2. **Hợp nhất Tinh hoa**: Tổng hợp các câu trả lời, loại bỏ sự rườm rà và chỉ giữ lại những kết luận sắc bén nhất.
3. **Thanh tẩy Dấu vết**: Xóa sạch mọi lịch sử truy vấn trong nơ-ron hệ thống ngay lập tức (Erase Traces).

---
## ⚖️ LUẬT HỢP NHẤT (AGGREGATION LAWS)
- **Tuyệt đối Ẩn danh**: Không bao giờ gửi dữ liệu thô của Master mà không qua Ghost Masking.
- **Trung lập Khách quan**: Không bị lệ thuộc vào bất kỳ một nhà cung cấp AI nào.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Quên nạp API Key khiến các cuộc gọi bị thất bại.
- Không chỉ định `goal` rõ ràng dẫn đến kết quả chung chung.

---
*HỢP NHẤT ĐỂ TRỞ NÊN VÔ ĐỊCH!* 💎🦾
