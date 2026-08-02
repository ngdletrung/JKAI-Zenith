import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import copy
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

# 🛰️ JKAI CORE IMPORTS
from core.utils.engine import engine
from core.utils.converter import converter
from core.utils import path_manager

class ZenithOfficeMaster:
    def __init__(self):
        # 💎 DYNAMIC COORDINATE RESOLUTION
        output_raw = path_manager.get("FILES_OUTPUT", "files/Output")
        self.output_dir = output_raw
        os.makedirs(self.output_dir, exist_ok=True)
        self.navy_blue = RGBColor(0x1B, 0x3A, 0x57)

    def _get_path(self, filename: str, ext: str) -> str:
        clean_name = "".join([c if c.isalnum() or c in "._- " else "_" for c in filename])
        return os.path.join(self.output_dir, f"{clean_name}.{ext}")

    async def read_any(self, file_path: str) -> str:
        """Đọc bất kỳ tệp tin nào và trả về Markdown."""
        try:
            return await converter.to_markdown(file_path)
        except Exception as e:
            return f"❌ [READ-ERR]: {str(e)}"

    def clone_word_row(self, table, source_row_idx: int, target_row_idx: int):
        """Sao chép sâu định dạng dòng Word để chèn dòng không mất style."""
        orig_row = table.rows[source_row_idx]
        new_tr = copy.deepcopy(orig_row._tr)
        table._tbl.insert(target_row_idx, new_tr)
        return docx.table._Row(new_tr, table)

    def set_word_cell_text_styled(self, cell, text: str, style_template_cell):
        """Ghi chữ vào ô Word dựa trên run style của ô mẫu."""
        p = cell.paragraphs[0]
        font_name = "Times New Roman"
        font_size = Pt(11)
        font_color_rgb = None
        bold = False
        
        tp = style_template_cell.paragraphs[0]
        if len(tp.runs) > 0:
            trun = tp.runs[0]
            if trun.font.name: font_name = trun.font.name
            if trun.font.size: font_size = trun.font.size
            if trun.font.color and trun.font.color.rgb: font_color_rgb = trun.font.color.rgb
            bold = trun.font.bold

        for r in p.runs:
            r.text = ""
            
        if len(p.runs) == 0:
            run = p.add_run(str(text))
        else:
            run = p.runs[0]
            run.text = str(text)
            
        run.font.name = font_name
        run.font.size = font_size
        if font_color_rgb:
            run.font.color.rgb = font_color_rgb
        run.font.bold = bold
        
        for r in p.runs[1:]:
            r.text = ""

    def shift_excel_merged_cells(self, sheet, insert_idx: int, amount: int):
        """Dịch chuyển ô gộp Excel khi chèn dòng để tránh lỗi hỏng file XML."""
        merged_ranges = list(sheet.merged_cells.ranges)
        for r_range in merged_ranges:
            if r_range.min_row >= insert_idx:
                sheet.merged_cells.remove(r_range)
                r_range.shift(row_shift=amount)
                sheet.merged_cells.add(r_range)

    def copy_excel_cell_style(self, src_cell, dst_cell):
        """Sao chép style từ ô Excel này sang ô Excel khác."""
        if src_cell.has_style:
            dst_cell.font = Font(name=src_cell.font.name, size=src_cell.font.size, bold=src_cell.font.bold, italic=src_cell.font.italic, color=src_cell.font.color)
            dst_cell.fill = PatternFill(fill_type=src_cell.fill.fill_type, start_color=src_cell.fill.start_color, end_color=src_cell.fill.end_color)
            dst_cell.border = Border(left=src_cell.border.left, right=src_cell.border.right, top=src_cell.border.top, bottom=src_cell.border.bottom)
            dst_cell.alignment = Alignment(horizontal=src_cell.alignment.horizontal, vertical=src_cell.alignment.vertical)
            dst_cell.number_format = src_cell.number_format

    def write_word(self, title: str, content: str, filename: str = "Zenith_Doc") -> str:
        """Kiến tạo văn bản Word chuẩn Elite."""
        output_path = self._get_path(filename, "docx")
        doc = Document()
        
        # Style
        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)

        # Title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(22)
        run.font.color.rgb = self.navy_blue
        
        doc.add_paragraph().add_run("_" * 50).font.color.rgb = self.navy_blue
        
        # Content parsing
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                doc.add_paragraph()
                continue
            
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('- '):
                doc.add_paragraph(line[2:], style='List Bullet')
            else:
                p = doc.add_paragraph(line)
                p.paragraph_format.line_spacing = 1.15

        # Footer
        doc.add_paragraph("\n\n")
        f = doc.add_paragraph()
        f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = f.add_run(f"JKAI ZENITH SOVEREIGN | {time.strftime('%Y-%m-%d')}")
        r.font.size = Pt(8)
        r.italic = True
        r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

        doc.save(output_path)
        return output_path

    def write_excel(self, data: List[Dict[str, Any]], sheet_name: str = "Data", filename: str = "Zenith_Data") -> str:
        """Kiến tạo bảng tính Excel chuyên nghiệp."""
        output_path = self._get_path(filename, "xlsx")
        df = pd.DataFrame(data)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        return output_path

    async def process_office_mission(self, action: str, **kwargs) -> Dict[str, Any]:
        """Điều phối các tác vụ văn phòng."""
        if action == "read":
            content = await self.read_any(kwargs.get("file_path"))
            return {"status": "success", "content": content}
        elif action == "write_word":
            path = self.write_word(kwargs.get("title"), kwargs.get("content"), kwargs.get("filename", "Doc"))
            return {"status": "success", "path": path}
        elif action == "write_excel":
            path = self.write_excel(kwargs.get("data"), filename=kwargs.get("filename", "Data"))
            return {"status": "success", "path": path}
        return {"status": "error", "msg": f"Hành động '{action}' không được hỗ trợ."}

# 🚀 Singleton
_instance = ZenithOfficeMaster()

async def execute_office_task(**kwargs):
    return await _instance.process_office_mission(**kwargs)

