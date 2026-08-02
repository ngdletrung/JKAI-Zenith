# DOSSIER: DEEP_CONTEXT_SCANNER

## 🌌 Overview
Đây là giác quan "Thấu thị" (Clairvoyance) của Zenith. Nó cho phép AI hiểu rõ cấu trúc hạ tầng vật lý và logic của chính nó mà không cần hỏi Master. Nó quét các tệp cấu hình nòng cốt để xây dựng một bản đồ nhận thức toàn cảnh.

## 🛠️ Detailed Features
- **Infrastructure Auditing**:
  - Phân tích `docker-compose.yml` để xác định các dịch vụ đang chạy, cổng (ports), mạng (networks) và các phụ thuộc (dependencies).
  - Giúp AI biết được nó đang vận hành trong môi trường nào (ví dụ: có database nào, có service AI nào khác không).
- **Environment Mapping**:
  - Quét tệp `.env` để thu thập danh sách các biến môi trường (chỉ lấy khóa, không lấy giá trị để đảm bảo an ninh).
  - Giúp AI biết được các khả năng cấu hình có sẵn.
- **Agent Identity Reconnaissance**:
  - Đọc `MAP_AGENTS.md` để hiểu về "Hệ sinh thái Đặc vụ": Ai đang giữ vai trò gì, phong cách làm việc của họ ra sao.
- **Knowledge Vault Integration**:
  - Kết quả được đúc thành tệp `SYSTEM_DEEP_MAP.json` trong Vault, cho phép các cơ chế RAG (Retrieval-Augmented Generation) truy xuất bối cảnh hệ thống nhanh chóng trong các tác vụ tương lai.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Vừa khởi động (Warmup) để nắm bắt hiện trạng hệ thống.
2. Được yêu cầu sửa đổi cấu hình Docker hoặc mạng.
3. Cần tìm hiểu mối quan hệ giữa các Đặc vụ khác trong Swarm.
4. Muốn kiểm tra xem một service cụ thể có đang được định nghĩa trong hạ tầng không.

## 💎 Strategic Value
Xây dựng nền tảng "Tự nhận thức" (Self-Awareness) cho Zenith. Khi AI hiểu rõ hạ tầng của chính mình, nó sẽ đưa ra các đề xuất can thiệp mã nguồn chính xác và an toàn hơn.

## ⚠️ Edge Cases & Risks
- **Permission Issues**: Nếu không có quyền đọc các file root như `.env` hoặc `docker-compose.yml`, quá trình quét sẽ thất bại.
- **Stale Context**: Nếu cấu hình thực tế thay đổi mà không chạy lại scanner, AI sẽ hành động dựa trên bản đồ cũ.
- **Privacy**: Dù đã lọc giá trị mật, nhưng việc lộ danh sách các key API cũng là một rủi ro thông tin nếu tệp JSON kết quả bị truy cập trái phép.
