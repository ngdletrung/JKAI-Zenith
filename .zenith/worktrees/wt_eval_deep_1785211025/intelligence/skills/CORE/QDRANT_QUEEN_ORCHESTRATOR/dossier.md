# DOSSIER: QDRANT_QUEEN_ORCHESTRATOR

## 🌌 Overview
Đây là "Thẩm phán Điều phối" (Orchestration Arbiter) của Zenith. Nữ hoàng Qdrant giữ vai trò tối cao trong việc tuyển chọn những nơ-ron tinh nhuệ nhất từ Swarm để thực hiện các nhiệm vụ cụ thể. Nó biến việc chọn đặc vụ từ ngẫu nhiên thành một quy trình khoa học dựa trên Vector Embeddings.

## 🛠️ Detailed Features
- **Q-Rank Protocol (Giao thức Q-Rank)**:
  - Sử dụng tìm kiếm tương đồng vector trên Qdrant để khớp mô tả nhiệm vụ với "Dấu vân tay kỹ năng" (Skill Fingerprints) của từng đặc vụ.
  - Xếp hạng và chọn ra Top 3 đặc vụ có xác suất thành công cao nhất.
- **Explainable Selection (Giải trình Ý chí)**:
  - Không chỉ đưa ra kết quả, Nữ hoàng còn sử dụng một luồng tư duy riêng biệt để giải thích cho Master LeeTrung lý do tại sao các đặc vụ đó lại được chọn.
  - Nâng cao tính minh bạch và sự tin tưởng vào các quyết định tự trị của hệ thống.
- **Mission Log Integration**:
  - Tự động báo cáo quá trình điều phối lên Dashboard thông qua `engine.publish_mission_log`.
- **Dynamic Fallback**:
  - Trong trường hợp cơ sở dữ liệu tri thức Qdrant chưa sẵn sàng, hệ thống tự động chuyển sang cấu hình quân đoàn mặc định (PLANNER/EXECUTOR) để đảm bảo tính liên tục của nhiệm vụ.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Bắt đầu một nhiệm vụ mới mà chưa rõ nên dùng tổ hợp đặc vụ nào.
2. Cần tối ưu hóa hiệu năng bằng cách chỉ triệu hồi những đặc vụ thực sự cần thiết.
3. Muốn cung cấp cho Master một bản báo cáo chuyên nghiệp về cách hệ thống đang "nghĩ" và "phối hợp".

## 💎 Strategic Value
Thiết lập cơ chế "Quản trị Nguồn lực Thông minh" (Intelligent Resource Governance). Nó giúp Zenith vận hành như một tổ chức phối hợp nhịp nhàng, nơi mỗi đặc vụ đều được đặt vào đúng vị trí để phát huy tối đa sức mạnh.

## ⚠️ Edge Cases & Risks
- **Vector Cold Start**: Nếu các đặc vụ mới chưa được nạp profile vào Qdrant, Nữ hoàng sẽ không thể nhận diện chính xác sức mạnh của họ.
- **Semantic Overlap**: Nếu mô tả nhiệm vụ quá chung chung, Nữ hoàng có thể chọn sai quân đoàn.
- **Latency**: Việc thực hiện thêm một bước gọi LLM để giải trình sẽ tăng nhẹ thời gian phản hồi ban đầu.
