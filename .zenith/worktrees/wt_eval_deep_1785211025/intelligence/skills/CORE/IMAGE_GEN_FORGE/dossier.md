# DOSSIER: IMAGE_GEN_FORGE

## 🌌 Overview
Đây là "Mắt thần Sáng tạo" của Zenith, cho phép hệ thống hiện thực hóa các ý tưởng trừu tượng thành hình ảnh thị giác sinh động. Nó sử dụng sức mạnh của Stable Diffusion (thông qua giao thức SDNext) để đúc ra các tác phẩm nghệ thuật kỹ thuật số chất lượng cao.

## 🛠️ Detailed Features
- **Text-to-Image Generation**:
  - Chuyển đổi mô tả văn bản (Prompts) thành hình ảnh PNG 24-bit.
  - Hỗ trợ `Negative Prompts` để lọc bỏ các chi tiết không mong muốn (mờ, chất lượng thấp, watermark).
- **Advanced Parameter Control**:
  - Cho phép điều chỉnh kích thước (`Width/Height`), số bước khử nhiễu (`Steps`), và mức độ tuân thủ prompt (`CFG Scale`).
  - Hỗ trợ nhiều thuật toán `Sampler` khác nhau để thay đổi phong cách nghệ thuật.
- **Sovereign GPU Management (Giao thức Điều phối GPU)**:
  - **Flush Phase**: Trước khi tạo ảnh, hệ thống tự động yêu cầu `engine` xả VRAM của các mô hình ngôn ngữ đang nạp để dành toàn bộ tài nguyên cho việc render ảnh.
  - **Restore Phase**: Sau khi hoàn tất, hệ thống tự động nạp lại các nơ-ron ngôn ngữ để tiếp tục phục vụ Master.
- **Output Management**:
  - Tự động lưu ảnh vào thư mục `outputs/generated/` với tên file chứa timestamp để tránh trùng lặp.
  - Trả về mã base64 xem trước (preview) để hiển thị tức thời trên giao diện Dashboard.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Master yêu cầu "Vẽ cho tôi một bức tranh về [X]".
2. Cần tạo ra các tài liệu minh họa trực quan cho các báo cáo hoặc dự án.
3. Cần thiết kế các thành phần giao diện (UI/UX) sơ bộ.
4. Muốn thể hiện các ý tưởng sáng tạo không thể mô tả bằng lời.

## 💎 Strategic Value
Cung cấp khả năng "Tư duy Thị giác" (Visual Thinking) cho Zenith. Một AI không chỉ biết nói mà còn biết vẽ là một AI có khả năng truyền cảm hứng và hỗ trợ Master LeeTrung trong các tác vụ thiết kế và sáng tạo nghệ thuật.

## ⚠️ Edge Cases & Risks
- **Hardware Requirement**: Đòi hỏi GPU mạnh và dịch vụ SDNext phải đang chạy (`Online`).
- **Prompt Sensitivity**: Kết quả phụ thuộc rất lớn vào chất lượng Prompt (tiếng Anh cho kết quả tốt nhất).
- **VRAM Conflict**: Nếu việc xả VRAM không thành công, quá trình tạo ảnh có thể gây treo hệ thống hoặc lỗi Out-of-Memory.
