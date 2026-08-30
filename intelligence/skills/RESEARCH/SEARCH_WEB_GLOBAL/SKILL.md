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

## ⚙️ GIAO THỨC VẬN HÀNH DEMS (DEMS OPERATIONAL PROTOCOL)

### Phase 1: Internal Recon (Trinh sát nội bộ)
- Luôn kiểm tra cache và kho tri thức nội bộ trước khi gọi API ngoài.

### Phase 2: External Extraction (Trích xuất ngoại vi)
- Kích hoạt `search_web` (Tavily/DDG/Browser cascade).
- Ghi nhận `RawTrace` bất biến vào SQLite SSoT với `Authority Level 4` (`TOOL_RUNTIME`).

### Phase 3: Scope Filtering & Verification (Lọc Scope & Kiểm chứng)
- Tự động phân loại qua `ScopeClassifier` (`scopes.yaml`) để loại bỏ 100% rác tử vi, bói toán, quảng cáo.
- Kiểm chứng facts kỹ thuật qua `FactVerifier` với Whitelist config chống xung đột giả.

### Phase 4: Epistemic Audit & Continuous Learning
- Đối soát câu trả lời qua `EpistemicAuditor` theo `GoalContract`.
- Tự động nạp bài học thất bại/thiếu hụt vào `ExperienceStore`.

---
*THẤU THỊ MỌI CHI TIẾT - QUYẾT ĐỊNH QUYỀN NĂNG!* 💎🔍🦾
