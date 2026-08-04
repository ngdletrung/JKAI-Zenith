---
aliases_vn:
- skill zenith office master
- SKILL_ZENITH_OFFICE_MASTER
author: Zenith Forge Auto
domain: CORE
id: OFFICE_SUITE_MASTER
intent_pairs:
- - EXECUTE
  - OFFICE_SUITE_MASTER
name_vn: Kỹ năng Office Suite Master
priority: NORMAL
related_skills: []
version: 1.0.0
---

# Kỹ năng Skill zenith office master

## 📖 TỔNG QUAN
Kỹ năng tự động được đúc bởi Zenith Forge.

## 🛠️ CÁC HÀM CỐT LÕI
- `__init__`
- `_get_path`
- `read_any` — đọc mọi file (docx/xlsx/pdf/txt) → markdown
- `write_word` — tạo văn bản Word chuẩn hành chính VN (A4, header/footer, markdown→table)
- `edit_word` — chỉnh sửa file Word có sẵn (replace chuỗi giữ định dạng, append)
- `write_excel` — tạo bảng Excel chuyên nghiệp (header đậm, số format, autofilter, freeze)
- `edit_excel` — sửa file Excel có sẵn (set ô, append dòng)
- `add_chart` — vẽ biểu đồ bar/line/pie từ dữ liệu
- `write_pdf` — tạo PDF A4 hỗ trợ tiếng Việt (font Unicode nhúng)
- `process_office_mission` — điều phối tác vụ, tự hỏi lại thông tin thiếu
- `execute_office_task` — entrypoint async

## ⚖️ GIAO THỨC VẬN HÀNH
- Mọi tác vụ đi qua `process_office_mission(action=..., **kwargs)`.
- Hành động `auto`/`plan_dossier`/`create_document` với goal mơ hồ sẽ trả `status: need_info` + câu hỏi bổ sung thay vì bịa nội dung.
- Output được ghi vào `FILES_OUTPUT` (mặc định `workspace/outputs`).
- Các action: read, write_word, write_excel, write_pdf, add_chart, edit_word, edit_excel.

## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- **Word Formatting Destruction:** Việc dùng `.text` trực tiếp trên Paragraph hoặc Cell sẽ làm vỡ định dạng font chữ Times New Roman và in đậm/màu chữ của template. BẮT BUỘC phải dùng phương pháp XML Deepcopy dòng và thay thế trên từng Run để giữ nguyên định dạng.
- **Excel openpyxl insert_rows corruption:** Hàm `insert_rows` của openpyxl không tự động dịch chuyển các ô gộp (`merged_cells`) ở dưới, gây hỏng file Excel khi mở. BẮT BUỘC phải viết hàm phụ trợ duyệt `sheet.merged_cells.ranges` để dịch chuyển thủ công các vùng gộp ô khi chèn dòng.
- Xem chi tiết hướng dẫn lập trình chuẩn tại tệp tin quy tắc hệ thống: `d:\Docker\JKAI\intelligence\rules\rule_Office-GUIDE.md`

