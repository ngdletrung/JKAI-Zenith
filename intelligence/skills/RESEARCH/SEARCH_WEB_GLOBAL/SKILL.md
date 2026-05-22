---
id: SEARCH_WEB_GLOBAL
name_vn: "Siêu Tìm Kiếm Zenith"
version: 2.0.0
author: "Antigravity Architect"
domain: RESEARCH
intent_pairs:
  - ["SEARCH", "NEWS"]
  - ["SEARCH", "INFO"]
  - ["RESEARCH", "TOPIC"]
  - ["ANALYZE", "DATA"]
aliases_vn: ["siêu tìm kiếm", "truy tìm thông tin", "tìm kiếm đa kênh", "trinh sát internet", "hóng biến"]
priority: CRITICAL
related_skills: ["SUMMARIZE_DOC_ELITE", "TRANSLATE_ZENITH", "DEEP_RESEARCH"]
---

# 🔍 SIÊU TÌM KIẾM ZENITH (SEARCH_WEB_GLOBAL)

## 📖 TỔNG QUAN
Kỹ năng này biến JKAI ZENITH thành một chuyên gia phân tích dữ liệu và trinh sát internet hàng đầu. Hệ thống sẽ quét song song cả kho tri thức nội bộ và xa lộ internet để đảm bảo không một chi tiết nào bị bỏ sót.

## 🛠️ CÔNG CỤ TÁC CHIẾN
- `explore_project`: Quét toàn bộ cây thư mục dự án.
- `search_knowledge`: Tìm kiếm tri thức trong kho tài liệu nội bộ.
- `search_web`: Tra cứu Internet thời gian thực (Tavily/Google).
- `web_scraper`: Trích xuất sâu dữ liệu từ URL mục tiêu.

## ⚙️ GIAO THỨC VẬN HÀNH (OPERATIONAL PROTOCOL)

### Phase 1: Internal Recon (Trinh sát nội bộ)
- Luôn sử dụng `explore_project` và `search_knowledge` trước để tìm xem Master đã từng có thông tin này chưa.
- Mục tiêu: Tránh trùng lặp và tận dụng tri thức đã có.

### Phase 2: External Extraction (Trích xuất ngoại vi)
- Nếu nội bộ không có, lập tức kích hoạt `search_web`.
- Sử dụng các từ khóa đã được chuẩn hóa qua `intent_lexicon.py`.

### Phase 3: Deep Analysis (Phân tích sâu)
- Sử dụng `web_scraper` để lấy nội dung thô từ các kết quả hàng đầu.
- Tổng hợp thành "Knowledge Packet" chuẩn Zenith.

---
*THẤU THỊ MỌI CHI TIẾT - QUYẾT ĐỊNH QUYỀN NĂNG!* 💎🔍🦾
