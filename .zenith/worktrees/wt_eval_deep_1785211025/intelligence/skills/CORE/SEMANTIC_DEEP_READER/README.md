# Kỹ năng: Phân tích Ngữ nghĩa Mã nguồn (Semantic Read)

## Mô tả
`semantic_read` là khả năng đặc quyền giúp JKAI "hiểu" mã nguồn thay vì chỉ "đọc" nó. Kỹ năng này sử dụng Cây Cú pháp Trừu tượng (AST) của Python để bóc tách cấu trúc file.

## Tham số
- `file_path` (string): Đường dẫn tuyệt đối hoặc tương đối tới file `.py` cần phân tích.

## Đầu ra (Output)
Trả về một JSON Document bao gồm:
- Danh sách thư viện Import.
- Danh sách các Class (kèm docstring và danh sách Method).
- Danh sách các Function độc lập.

## Ứng dụng
- Quét nhanh kiến trúc một file code trước khi quyết định dùng công cụ chỉnh sửa (`patch_file`).
- Nắm bắt luồng logic thay vì phải đọc toàn bộ hàng ngàn dòng lệnh.
