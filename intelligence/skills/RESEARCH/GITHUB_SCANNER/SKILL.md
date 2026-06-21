---
id: GITHUB_SCANNER
name: "GitHub Trend Scanner"
description: "Quét và phân tích xu hướng các kho lưu trữ (repositories) trên GitHub theo thời gian thực."
intent: "Tìm kiếm và tổng hợp các dự án GitHub nổi bật trong tháng 05/2026."
---

# 🚀 GITHUB_SCANNER

## 📖 TỔNG QUAN
Skill này được thiết kế để cung cấp cái nhìn thấu thị về các xu hướng công nghệ mới nhất trên GitHub. Đặc vụ sử dụng skill này để xác định các Repo đang "hot", có tốc độ tăng trưởng sao nhanh chóng hoặc các công nghệ đột phá vừa xuất hiện.

## 🛠️ CÔNG CỤ SỬ DỤNG
- `SEARCH_WEB_GLOBAL`: Để trích xuất dữ liệu thực tế từ Internet (GitHub Trending, Tech Blogs, v.v.)
- `read_browser_page`: Để thấu thị các trang web hiện đại nếu cần thiết.

## ⚙️ GIAO THỨC VẬN HÀNH
1. **Tiếp nhận**: Xác định query của Master về xu hướng GitHub.
2. **Thực thi**: Gọi `SEARCH_WEB_GLOBAL` với tham số tối ưu (ví dụ: "top trending github repositories May 2026").
3. **Xử lý**: Trích xuất Tên Repo, Link, Số sao và Mô tả.
4. **Trình bày**: Trình bày dưới dạng bảng Markdown chuyên nghiệp.

---
*CẬP NHẬT NHỊP ĐẬP CÔNG NGHỆ - DẪN ĐẦU KỶ NGUYÊN!* 🛠️🦾⚡
