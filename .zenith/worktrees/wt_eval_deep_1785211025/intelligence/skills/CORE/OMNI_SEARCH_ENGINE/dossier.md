# DOSSIER: OMNI_SEARCH_ENGINE

## 🌌 Overview
Đây là "Hệ thống Truy xuất Toàn năng" (Omni-Retrieval System) của Zenith. Không chỉ đơn thuần là tìm kiếm, nó hoạt động như một bộ não phân tích thông tin đa nguồn, có khả năng tự thẩm định độ tin cậy và kiểm chứng sự thật trước khi trình bày kết quả cho Master.

## 🛠️ Detailed Features
- **Multi-Source Hybrid Search**:
  - Tích hợp 3 tầng Fallback: **Tavily API** (Ưu tiên), **AI-Browse** (Vật lý qua DuckDuckGo), và **Cloud LLM Search** (Dự phòng).
  - Đảm bảo khả năng truy cập thông tin toàn cầu ngay cả khi một số API bị giới hạn quota.
- **Neural Cognitive Reranking (v8.0)**:
  - Sử dụng thuật toán **Hybrid Reranker** kết hợp:
    - **BM25-lite**: So khớp từ khóa chính xác.
    - **Semantic Cosine**: So khớp ý nghĩa nơ-ron thông qua Embeddings.
    - **Trust Score**: Đánh giá uy tín tên miền (GitHub, StackOverflow, v.v.).
    - **Freshness Score**: Ưu tiên các tri thức mới nhất (2025-2026).
- **Fact Verification & Contradiction Detection**:
  - Tự động trích xuất các "Sự thật kỹ thuật" (Ports, Versions, Commands).
  - Cảnh báo Master nếu có sự mâu thuẫn giữa các nguồn tin (ví dụ: Nguồn A bảo dùng Port 3000, Nguồn B bảo Port 5000).
- **Persistent Neural Cache**:
  - Lưu trữ tri thức đã xử lý vào **Qdrant Vector DB** và đĩa cục bộ.
  - Cơ chế **TTL (Time-To-Live)** thông minh: Tin tức thời sự hết hạn nhanh, kiến thức cơ bản tồn tại lâu hơn.
- **Query Optimization (Query Planner)**:
  - Tự động dịch và mở rộng truy vấn sang tiếng Anh để tối ưu hóa kết quả tìm kiếm trên quy mô toàn cầu.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Master hỏi về các sự kiện, công nghệ hoặc tin tức mới nhất (sau thời điểm cắt dữ liệu của model).
2. Cần tìm kiếm mã nguồn, thư viện hoặc tài liệu hướng dẫn (Documentation) chính xác.
3. Cần kiểm chứng một giả thuyết kỹ thuật từ nhiều nguồn khác nhau.
4. Muốn tổng hợp một báo cáo chuyên sâu về một chủ đề cụ thể.

## 💎 Strategic Value
Cung cấp "Tầm nhìn Thời gian thực" (Real-time Vision) cho Zenith. Nó đảm bảo rằng mọi quyết định và câu trả lời của AI đều dựa trên dữ liệu thực tế và mới nhất của thế giới.

## ⚠️ Edge Cases & Risks
- **Hallucination in Synthesis**: Dù có verify, bước tổng hợp cuối cùng vẫn có thể gặp sai sót nếu dữ liệu đầu vào quá nhiễu.
- **Quota Dependency**: Phụ thuộc vào API Key của Tavily để đạt hiệu suất cao nhất.
- **Latency**: Do trải qua nhiều tầng xử lý (Embed -> Search -> Rerank -> Verify -> Synthesize), thời gian phản hồi có thể lâu hơn tìm kiếm thông thường.
