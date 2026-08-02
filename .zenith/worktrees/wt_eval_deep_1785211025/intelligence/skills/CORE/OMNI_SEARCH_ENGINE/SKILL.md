---
name: omni_search
description: "Bộ máy tìm kiếm Internet hợp nhất. Tự động chạy fallback qua các kênh: Tavily -> Cloud LLM -> AI-Browse."
---

# OMNI SEARCH ENGINE

Bộ công cụ tìm kiếm hợp nhất của hệ thống. Nhận truy vấn và trả về kết quả tìm kiếm an toàn, tích hợp sẵn chống lỗi Quota (429) và Timeout.

## Tham số
- `query` (str): Nội dung cần tìm kiếm (bắt buộc).
- `mode` (str): `fast` hoặc `deep` (tùy chọn).

## Cách hoạt động (Fallback Chain)
1. Thử gọi **Tavily API**.
2. Nếu lỗi hoặc hết Quota/Token, nhờ **Cloud LLM (Gemini/ChatGPT)** qua Engine gọi web native.
3. Nếu vẫn lỗi, gọi **ai_browse** để tự động mở Google/DuckDuckGo cạo văn bản trực tiếp.
