---
id: AUTONOMOUS_RESEARCHER
name_vn: "Đặc Vụ Nghiên Cứu Tự Trị"
version: 1.6.0
author: "JKAI ZENITH Forge"
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
Đây là nơ-ron nghiên cứu cấp độ chuyên gia, có khả năng tự động trinh sát Internet thông qua các kênh tìm kiếm siêu cấp, phân mảnh ngữ nghĩa thông minh và tự động phát hiện mâu thuẫn dữ liệu. Kỹ năng này không chỉ tìm kiếm mà còn **tư duy phản biện** dựa trên dữ liệu thu thập được từ thực địa để kiến tạo các báo cáo nghiên cứu chất lượng cao.

## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)

### 🔍 Phase 1: Investigation (Thẩm định & Thu thập)
1. **Trinh sát Internet**: Định tuyến các truy vấn tìm kiếm thông qua `SEARCH_WEB_GLOBAL` để tiếp cận nguồn tin chất lượng cao đã qua xử lý.
2. **Thấu thị & Trích lọc (BM25-CP)**: Đọc sâu các trang web qua Jina.ai. Phân mảnh nội dung và xếp hạng bằng giải thuật BM25-CP (Contiguous Phrase-Aware Local-Corpus BM25) với cửa sổ trượt N-grams để chọn lọc chính xác top 4 phân đoạn liên quan nhất tới mục tiêu, loại bỏ nhiễu.

### 🛡️ Phase 2: Action & Verification (Đối chiếu & Thực thi)
1. **Đối chiếu chéo (FactVerifier)**: Chạy kiểm toán thực thể đa nguồn nhằm phát hiện và cảnh báo các mâu thuẫn về thông số kỹ thuật, cấu hình, phiên bản và các câu lệnh xung đột giữa các nguồn tin.
2. **Tổng hợp Chiến lược (Planner)**: Triệu hồi Ban Kế hoạch (PLANNER) để đúc kết báo cáo theo cấu trúc chuẩn Corporate (Bối cảnh, Phân tích, Kết luận, Đề xuất), tự động tích hợp danh mục trích dẫn nguồn Perplexity-style.
3. **Lưu trữ vĩnh cửu**: Ghi nhận báo cáo vào "Vault" (Kho lưu trữ tri thức) để bảo tồn tài nguyên cho Đế chế.

---
## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- Topic quá rộng dẫn đến báo cáo bị loãng nơ-ron.
- Không có API Key Tavily sẽ kích hoạt cơ chế fallback cục bộ hoặc dừng bối cảnh.

---
*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾
