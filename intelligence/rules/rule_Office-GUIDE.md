# GIAO THỨC THAO TÁC FILE VĂN PHÒNG CHUẨN ELITE
*(OFFICE SUITE MANIPULATION PROTOCOL - SDS v18.0)*

> [!IMPORTANT]
> **ĐỊNH HƯỚNG QUY TẮC CỐT LÕI (SSoT)**:
> Mọi Đặc vụ AI (bao gồm cả JKAI và các phân thân) khi viết mã nguồn Python để đọc/ghi/chèn dòng/thay đổi nội dung các tệp tin Word (`.docx`) và Excel (`.xlsx`) BẮT BUỘC phải tuân thủ nghiêm ngặt giao thức bảo toàn định dạng dưới đây. Tuyệt đối không để xảy ra tình trạng lỗi file Excel hoặc vỡ định dạng Word.

---

## 🏛️ PHẦN 1: GIAO THỨC WORD (`python-docx`) - BẢO TOÀN ĐỊNH DẠNG 100%

### 1. Cấm dùng `p.text = ...` hoặc `cell.text = ...` trực tiếp
*   **Hậu quả:** Việc gán trực tiếp `.text` sẽ xóa sạch các `runs` bên trong paragraph, làm mất toàn bộ font chữ (Times New Roman), cỡ chữ, in đậm/in nghiêng, màu chữ mẫu và căn lề.
*   **Giải pháp chuẩn:** Thực hiện thay thế trực tiếp trên các `runs` hiện có hoặc bảo toàn thuộc tính chạy chữ:
```python
def update_runs_by_matching(paragraph, old_vals_map):
    for run in paragraph.runs:
        for old_t, new_t in old_vals_map.items():
            if old_t in run.text:
                run.text = run.text.replace(old_t, new_t)
```
*   **Trường hợp chữ bị chia nhỏ (Split runs):** Nếu từ khóa bị chia thành nhiều run (ví dụ: `Ông ` và `Hoàng Lê Vinh Hưng`), hãy xác định run chứa phần chính và thay thế nó, các run phụ gán về chuỗi rỗng `""` thay vì xóa run.

### 2. Nhân bản dòng bảng tính bằng XML Deepcopy thay vì `table.add_row()`
*   **Hậu quả:** `table.add_row()` tạo ra một dòng hoàn toàn thô (không có đường viền, không có màu chữ, dùng font mặc định của Word).
*   **Giải pháp chuẩn:** Copy sâu phần tử XML dòng mẫu và chèn trực tiếp vào chỉ mục cụ thể của bảng (`table._tbl`):
```python
import copy

# Nhân bản dòng mẫu (ví dụ dòng 1)
orig_row = table.rows[1]
new_tr = copy.deepcopy(orig_row._tr)

# Chèn vào vị trí chỉ định (ví dụ ngay sau dòng mẫu)
tr_index = table._tbl.index(orig_row._tr)
table._tbl.insert(tr_index + 1, new_tr)

# Tạo wrapper Row object để tương tác
new_row = docx.table._Row(new_tr, table)
```

### 3. Ghi dữ liệu vào ô gộp/ô bảng nhân bản bảo toàn style run
```python
def set_cell_text_styled(cell, text, style_template_cell):
    p = cell.paragraphs[0]
    # Lấy thông tin font, size, color, bold từ run đầu tiên của ô mẫu
    font_name = "Times New Roman"
    font_size = docx.shared.Pt(11)
    font_color_rgb = None
    bold = False
    
    tp = style_template_cell.paragraphs[0]
    if len(tp.runs) > 0:
        trun = tp.runs[0]
        if trun.font.name: font_name = trun.font.name
        if trun.font.size: font_size = trun.font.size
        if trun.font.color and trun.font.color.rgb: font_color_rgb = trun.font.color.rgb
        bold = trun.font.bold

    # Clear nội dung của tất cả runs hiện tại
    for r in p.runs:
        r.text = ""
        
    # Thêm hoặc cập nhật run đầu tiên
    if len(p.runs) == 0:
        run = p.add_run(str(text))
    else:
        run = p.runs[0]
        run.text = str(text)
        
    # Thiết lập lại thuộc tính font
    run.font.name = font_name
    run.font.size = font_size
    if font_color_rgb:
        run.font.color.rgb = font_color_rgb
    run.font.bold = bold
    
    # Đảm bảo các run sau trống hoàn toàn
    for r in p.runs[1:]:
        r.text = ""
```

---

## 🏛️ PHẦN 2: GIAO THỨC EXCEL (`openpyxl`) - CHỐNG LỖI CẤU TRÚC FILE

### 1. Dịch chuyển ô gộp (Merged Cells Shifting) bắt buộc khi `insert_rows`
*   **Hậu quả:** Hàm `sheet.insert_rows(idx, amount)` của `openpyxl` không tự động dịch chuyển các ô gộp nằm bên dưới chỉ mục `idx`. Điều này làm hỏng cấu trúc XML của tệp Excel và Excel sẽ báo lỗi file khi mở.
*   **Giải pháp chuẩn:** Phải lặp qua toàn bộ các vùng gộp (`sheet.merged_cells.ranges`), lọc các vùng nằm dưới vị trí chèn, gỡ bỏ chúng, dịch chuyển tọa độ dòng xuống `amount` dòng, và thêm lại vào trang tính:
```python
# Chèn dòng trước
sheet.insert_rows(insert_idx, amount)

# Dịch chuyển ô gộp thủ công để tránh lỗi hỏng file
merged_ranges = list(sheet.merged_cells.ranges)
for r_range in merged_ranges:
    if r_range.min_row >= insert_idx:
        sheet.merged_cells.remove(r_range)
        r_range.shift(row_shift=amount)
        sheet.merged_cells.add(r_range)
```

### 2. Dịch chuyển chiều cao dòng (Row Heights)
*   Tương tự như ô gộp, chiều cao dòng cũng phải được dời xuống tương ứng:
```python
row_heights = {}
for r in list(sheet.row_dimensions.keys()):
    if r >= insert_idx:
        row_heights[r + amount] = sheet.row_dimensions[r].height
for r, h in row_heights.items():
    sheet.row_dimensions[r].height = h
```

### 3. Copy Style dòng Excel mẫu cho dòng mới chèn
```python
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

def copy_cell_style(src_cell, dst_cell):
    if src_cell.has_style:
        dst_cell.font = Font(
            name=src_cell.font.name, 
            size=src_cell.font.size, 
            bold=src_cell.font.bold, 
            italic=src_cell.font.italic, 
            color=src_cell.font.color
        )
        dst_cell.fill = PatternFill(
            fill_type=src_cell.fill.fill_type, 
            start_color=src_cell.fill.start_color, 
            end_color=src_cell.fill.end_color
        )
        dst_cell.border = Border(
            left=src_cell.border.left, 
            right=src_cell.border.right, 
            top=src_cell.border.top, 
            bottom=src_cell.border.bottom
        )
        dst_cell.alignment = Alignment(
            horizontal=src_cell.alignment.horizontal, 
            vertical=src_cell.alignment.vertical
        )
        dst_cell.number_format = src_cell.number_format
```

### 4. Ghi công thức và cập nhật ô chữ ký bị trượt dòng
*   Sau khi dòng được chèn, các vị trí chữ ký ở dòng cuối (ví dụ từ `F28` trượt xuống `F29`) phải được cập nhật ở địa chỉ mới.
*   Dùng công thức viết dạng chuỗi (ví dụ: `=SUM(F16:F21)`) thay vì số cứng để Excel tự cập nhật giá trị.

---

*Giao thức đã được kiểm chứng độc lập và tối ưu hóa tối cao bởi Antigravity. Nghiêm cấm Đặc vụ AI sửa đổi hoặc vi phạm.*
