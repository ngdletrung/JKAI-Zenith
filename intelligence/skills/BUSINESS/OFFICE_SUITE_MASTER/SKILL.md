---
aliases_vn:
- skill zenith office master
author: Zenith Forge Auto
domain: CORE
id: SKILL_ZENITH_OFFICE_MASTER
intent_pairs:
- - EXECUTE
  - SKILL_ZENITH_OFFICE_MASTER
name_vn: Kỹ năng Skill zenith office master
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
- `read_any`
- `write_word`
- `write_excel`
- `process_office_mission`
- `execute_office_task`

## ⚖️ GIAO THỨC VẬN HÀNH
- Tự động thực thi theo logic trong `logic.py`.

## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)
- **Word Formatting Destruction:** Việc dùng `.text` trực tiếp trên Paragraph hoặc Cell sẽ làm vỡ định dạng font chữ Times New Roman và in đậm/màu chữ của template. BẮT BUỘC phải dùng phương pháp XML Deepcopy dòng và thay thế trên từng Run để giữ nguyên định dạng.
- **Excel openpyxl insert_rows corruption:** Hàm `insert_rows` của openpyxl không tự động dịch chuyển các ô gộp (`merged_cells`) ở dưới, gây hỏng file Excel khi mở. BẮT BUỘC phải viết hàm phụ trợ duyệt `sheet.merged_cells.ranges` để dịch chuyển thủ công các vùng gộp ô khi chèn dòng.
- Xem chi tiết hướng dẫn lập trình chuẩn tại tệp tin quy tắc hệ thống: `d:\Docker\N8N\intelligence\rules\rule_Office-GUIDE.md`

