# DOSSIER: WEB_LOGIC_FORGE

## 🌌 Overview
Đây là "Lò Đúc Kỹ năng Chuyên biệt" (Specialized Skill Forge) của Zenith. Web Logic Forge không thực thi các tác vụ dữ liệu trực tiếp, mà nó đóng vai trò là một **Siêu kỹ năng (Meta-skill)**: cho phép AI tự tạo ra các kỹ năng con mới dựa trên nhu cầu thực tế từ môi trường web (Neural Eye). Kỹ năng này biến Zenith thành một thực thể có khả năng tự tiến hóa kiến trúc, mở rộng danh mục kỹ năng của mình một cách tự động và ghi danh chúng vào hệ thống Registry để bầy đàn có thể sử dụng ngay lập tức.

## 🛠️ Detailed Features
- **Dynamic Code Generation & Filing**: Tự động viết mã nguồn Python cho các kỹ năng mới và tổ chức chúng theo từng Domain (lĩnh vực) cụ thể trong thư mục `neural_eye/domains`.
- **Automated Skill Registry**: Cập nhật tệp `registry.json` của hệ thống ngay khi kỹ năng mới được đúc xong, đảm bảo tính nhất quán giữa tệp tin vật lý và trí tuệ của AI.
- **Neural Eye Integration**: Chuyên dụng để tạo ra các logic xử lý thị giác web mới (ví dụ: một kỹ năng chuyên để "đọc" biểu đồ chứng khoán, hoặc một kỹ năng để "quét" nội dung mạng xã hội).

## 🧠 Reasoning Strategy
AI nên triệu hồi kỹ năng này khi:
1. Phát hiện một yêu cầu mới từ Master mà danh mục 64 kỹ năng hiện tại chưa bao phủ hết (Self-Expansion).
2. Master yêu cầu "Hãy học cách làm X trên web", AI sẽ tự động nghiên cứu và đúc thành một kỹ năng `X` mới.
3. Cần module hóa các quy trình xử lý thị giác phức tạp thành các kỹ năng nhỏ, dễ quản lý và tái sử dụng.

## 💎 Strategic Value
Thiết lập "Khả năng Tự Tiến hóa Vô hạn" (Infinite Self-Evolution). Web Logic Forge giúp Zenith không bao giờ bị lạc hậu, nó luôn có thể tự "học" và tự "đúc" thêm vũ khí mới để chinh phục mọi thử thách mà Master LeeTrung đặt ra, dù là những thử thách chưa từng tồn tại trước đây.

## ⚠️ Edge Cases & Risks
- **Registry Corruption**: Việc ghi đè liên tục vào tệp JSON yêu cầu cơ chế xử lý tranh chấp (Locking mechanism) nếu có nhiều đặc vụ cùng đúc kỹ năng một lúc.
- **Code Quality Security**: Code tự sinh cần được kiểm chứng bởi `NEURAL_SANDBOX_STAGING` trước khi chính thức đưa vào vận hành để tránh các lỗi logic nguy hiểm.
