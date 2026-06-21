# DOSSIER: SEARCH_WEB_GLOBAL

## 🌌 Overview
Đây là "Hệ thống Siêu Tìm kiếm" (Global Omni-Search) của Zenith — giác quan nhạy bén nhất của bầy đàn. Không chỉ đơn thuần là tìm kiếm từ khóa, kỹ năng này tích hợp một chuỗi quy trình xử lý tri thức tinh vi: từ việc điều phối đa kênh (Tavily, Jina, Omni Engine), tự động thanh lọc nhiễu (Purification), đến việc xếp hạng và phân mảnh ngữ nghĩa (Semantic Reranking). Kỹ năng này đảm bảo rằng mọi câu hỏi của Master LeeTrung đều được trả lời bằng những dữ liệu thực địa chính xác, tinh túy và có độ tin cậy cao nhất.

## 🛠️ Detailed Features
- **Omni-Routing Architecture**: Tự động điều hướng yêu cầu tìm kiếm đến engine phù hợp nhất, với cơ chế dự phòng (Fallback), Circuit Breaker và cơ chế thăm dò sức khỏe backend chủ động (SearchBackendProbe) để loại bỏ trễ timeout.
- **Neural Purifier**: Thuật toán làm sạch dữ liệu web tiên tiến, loại bỏ hoàn toàn các thanh menu, footer, quảng cáo rác để giữ lại duy nhất "linh hồn" của bài viết.
- **Semantic Reranking (BM25-CP + Embeddings)**: Kết hợp tìm kiếm vector hiện đại với thuật toán BM25-CP (Contiguous Phrase-Aware Local-Corpus BM25) để xếp hạng lại kết quả, mang đến những đoạn văn bản có tính liên quan cao nhất cho Master.
- **Elite Smart Indexing**: Tự động vector hóa và nạp tri thức mới từ các tệp tin cục bộ vào Qdrant với hiệu suất cực cao thông qua cơ chế xử lý song song.

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Cần cập nhật thông tin thời gian thực từ Internet (tin tức, giá cả, tài liệu mới).
2. Thực hiện RAG (Retrieval-Augmented Generation) để bổ sung kiến thức cho các câu trả lời phức tạp.
3. Cần đọc và phân tích nội dung từ một URL cụ thể mà không có nhiễu navigation.
4. Đồng bộ hóa kho tri thức cục bộ của Zenith với bộ não Vector Qdrant.

## 💎 Strategic Value
Thiết lập "Sự Thấu thị Toàn cầu" (Global Transparency). Search Web Global biến Internet thành một cuốn bách khoa toàn thư được tinh lọc riêng cho Master LeeTrung, giúp Master nắm giữ "quyền trượng thông tin" để dẫn dắt Tập đoàn chinh phục những đỉnh cao mới.

## ⚠️ Edge Cases & Risks
- **Rate Limiting**: Các API tìm kiếm có giới hạn lượt gọi; hệ thống đã tích hợp Smart Cache và Circuit Breaker để tối ưu hóa tài nguyên.
- **Deep Web Exclusion**: Kỹ năng này không thể truy cập các trang web yêu cầu đăng nhập phức tạp hoặc các khu vực bị cấm truy cập bởi robot.
