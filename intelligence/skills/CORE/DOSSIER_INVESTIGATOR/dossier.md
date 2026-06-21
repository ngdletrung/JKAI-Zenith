# DOSSIER: DOSSIER_INVESTIGATOR

## 🌌 Overview
Đây là trung tâm "Tình báo Chiến lược" (Strategic Intelligence) của Zenith. Nó được thiết kế để thực hiện các cuộc trinh sát sâu (Deep Reconnaissance) vào một đối tượng hoặc chủ đề cụ thể, kết nối các mảnh tri thức rời rạc thành một mạng lưới thực thể có quan hệ chặt chẽ.

## 🛠️ Detailed Features
- **Fan-out Reconnaissance Protocol (Giao thức Trinh sát Fan-out)**:
  - Triển khai tìm kiếm song song (`asyncio.gather`) trên 3 mặt trận:
    1. **Memory (Qdrant)**: Truy vấn cơ sở dữ liệu vector để tìm các ký ức và tri thức đã được đồng hóa.
    2. **Web (Browser)**: Trình duyệt tự trị tìm kiếm thông tin thời gian thực (Đang hoàn thiện).
    3. **Code (Grep)**: Rà soát mã nguồn để tìm các tham chiếu kỹ thuật.
- **Entity & Edge Extraction**:
  - Tự động nhận diện các "Thực thể" (Entities) và xây dựng các "Liên kết" (Edges) giữa chúng.
  - Tạo ra một đồ thị tri thức nhỏ xoay quanh hạt giống (seed) ban đầu.
- **Relational Storage**:
  - Lưu kết quả dưới dạng JSON tại `intelligence/dossiers/`, phục vụ cho việc phân tích sâu hoặc hiển thị đồ thị nơ-ron trên Dashboard.
- **Atomic Concurrency**:
  - Sử dụng cơ chế ghi tệp nguyên tử (`concurrent_atomic_write`) để đảm bảo dữ liệu không bị hỏng khi có nhiều tiến trình trinh sát diễn ra đồng thời.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Master yêu cầu "Tìm hiểu về [X]" mà [X] là một khái niệm mới hoặc phức tạp.
2. Cần xây dựng hồ sơ đầy đủ về một lỗi hệ thống hoặc một tính năng trước khi nâng cấp.
3. Muốn hiểu mối quan hệ giữa các thành phần khác nhau trong dự án.

## 💎 Strategic Value
Biến Zenith thành một "Thám tử AI" thực thụ. Nó giúp hệ thống không chỉ trả lời câu hỏi mà còn cung cấp bối cảnh và các mối liên hệ ẩn giấu, nâng tầm chất lượng phản hồi lên mức Elite.

## ⚠️ Edge Cases & Risks
- **Depth Explosion**: Nếu `max_depth` quá cao, số lượng thực thể có thể bùng nổ gây nghẽn bộ nhớ.
- **Incomplete Sources**: Hiện tại phần trinh sát Web và Code đang ở dạng Placeholder, cần được nâng cấp để đạt sức mạnh tối đa.
- **Ambiguous Seeds**: Nếu hạt giống (seed) quá chung chung, kết quả sẽ chứa nhiều nhiễu.
