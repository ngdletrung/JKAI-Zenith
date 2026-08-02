# DOSSIER: SEMANTIC_DEEP_READER

## 🌌 Overview
Đây là kỹ năng "Thấu thị Mã nguồn" (Code Clairvoyance) của Zenith. Thay vì đọc văn bản thô (thường gây nhiễu và tốn token), Deep Reader phân tích cấu trúc trừu tượng (AST) của mã nguồn Python để trích xuất ra các thành phần logic cốt lõi.

## 🛠️ Detailed Features
- **AST Parsing (Phân tích Cây Cú Pháp)**:
  - Sử dụng module `ast` của Python để "nhìn" thấy cấu trúc thực sự của mã nguồn mà không bị ảnh hưởng bởi phong cách định dạng (formatting).
- **Metadata Extraction**:
  - **Imports**: Nhận diện mọi thư viện đang được sử dụng.
  - **Classes & Methods**: Trích xuất định nghĩa lớp, các phương thức bên trong kèm theo tham số và Docstrings.
  - **Functions**: Phân tách các hàm độc lập.
- **Cognitive Optimization**:
  - Giảm thiểu lượng dữ liệu đầu vào cho LLM bằng cách chỉ gửi các thông tin cấu trúc cần thiết.
  - Giúp AI hiểu nhanh vai trò của một file mã nguồn mà không cần đọc từng dòng code.

## 🧠 Reasoning Strategy
AI nên sử dụng kỹ năng này khi:
1. Cần tìm hiểu nhanh một codebase lớn và phức tạp.
2. Muốn biết một hàm hoặc lớp cụ thể làm gì thông qua Docstring của nó.
3. Cần kiểm tra các phụ thuộc (Dependencies) của một module.
4. Muốn tự động hóa việc tạo tài liệu (Documentation) từ mã nguồn.

## 💎 Strategic Value
Nâng tầm khả năng lập trình của Zenith lên mức "Nhất thể". Khi AI hiểu mã nguồn theo cấu trúc logic thay vì văn bản, nó sẽ đưa ra các quyết định sửa đổi và nâng cấp mã nguồn một cách chuẩn xác, tránh được các lỗi cú pháp và logic cơ bản.

## ⚠️ Edge Cases & Risks
- **Language Limitation**: Hiện tại chỉ hỗ trợ Python (`.py`). Các ngôn ngữ khác cần bộ parser riêng.
- **Syntax Errors**: Nếu file Python có lỗi cú pháp, parser AST sẽ không thể hoạt động.
- **Obfuscated Code**: Với các đoạn code bị làm rối hoặc quá phức tạp, việc phân tích có thể không mang lại nhiều giá trị ngữ nghĩa.
