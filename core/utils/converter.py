import os
import logging
from pathlib import Path

# 🛰️ JKAI ZENITH: UNIVERSAL CONVERTER CORE (v1.0)
# Nhiệm vụ: Chuyển đổi vạn vật sang Markdown để AI thấu cảm.

logger = logging.getLogger("jkai.core.converter")

try:
    from markitdown import MarkItDown
    _md = MarkItDown()
    CONVERTER_AVAILABLE = True
    logger.info("✅ [CONVERTER-CORE] MarkItDown Engine Integrated.")
except ImportError:
    _md = None
    CONVERTER_AVAILABLE = False
    logger.warning("⚠️ [CONVERTER-CORE] MarkItDown not found. Multimodal conversion disabled.")

class JKAI_Converter:
    @staticmethod
    async def to_markdown(file_path: str, task_id: str = "system") -> str:
        """
        🚀 Chuyển đổi vạn vật sang Markdown.
        Tích hợp Redis Cache để truy xuất thần tốc.
        """
        path = Path(file_path)
        if not path.exists():
            return f"❌ [CONVERTER] File not found: {file_path}"
            
        # ⚡ [CACHE-CHECK]: Kiểm tra bộ nhớ nóng trước khi đọc
        try:
            from redis_client import redis_safe
            # Dùng tên file + thời gian chỉnh sửa làm key để đảm bảo tính cập nhật
            cache_key = f"neural_cache:md:{path.name}:{os.path.getmtime(file_path)}"
            cached_content = redis_safe(lambda r: r.get(cache_key), None)
            if cached_content:
                logger.info(f"⚡ [CACHE-HIT]: Truy xuất thần tốc bản dịch {path.name} từ Redis.")
                return cached_content.decode('utf-8') if isinstance(cached_content, bytes) else cached_content
        except: pass

        ext = path.suffix.lower()
        convertible_docs = {".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".xml", ".html", ".json"}
        convertible_imgs = {".png", ".jpg", ".jpeg", ".webp"}
        
        result_md = ""
        try:
            # 🖼️ [NEURAL-EYE]: Xử lý hình ảnh
            if ext in convertible_imgs:
                import base64
                with open(path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                logger.info(f"👁️ [VISION]: Đang quan sát hình ảnh {path.name}...")
                prompt = "Hãy mô tả chi tiết nội dung bức ảnh này, bao gồm văn bản, biểu đồ, màu sắc và bố cục để phục vụ lập báo cáo chiến lược."
                from core.utils.engine import engine
                vision_desc = await engine.call_chat(
                    messages=[{"role": "user", "content": prompt}],
                    role="VISION",
                    images=[base64_image],
                    task_id=task_id
                )
                result_md = f"\n### 🖼️ [MÔ TẢ HÌNH ẢNH: {path.name}]\n{vision_desc}\n"

            # 📄 [DOCUMENT-CONVERSION]: Xử lý tài liệu
            elif ext in convertible_docs:
                # 📊 [SPECIALIZED-EXCEL]: Thấu thị Đa Sheet
                if ext == ".xlsx":
                    try:
                        import pandas as pd
                        logger.info(f"📊 [EXCEL]: Đang thấu thị đa Sheet tệp {path.name}...")
                        xls = pd.ExcelFile(path)
                        full_content = [f"### 📊 [BẢNG DỮ LIỆU EXCEL: {path.name}]"]
                        for sheet_name in xls.sheet_names:
                            df = pd.read_excel(xls, sheet_name=sheet_name)
                            if not df.empty:
                                full_content.append(f"\n#### 📑 Sheet: {sheet_name}\n")
                                full_content.append(df.to_markdown(index=False))
                        result_md = "\n".join(full_content)
                    except Exception as ex_err:
                        logger.warning(f"⚠️ [EXCEL-ERR]: {ex_err}. Thử dùng MarkItDown...")
                
                # 📝 [SPECIALIZED-WORD]: Thấu thị Văn bản & Bảng biểu
                elif ext == ".docx":
                    try:
                        from docx import Document
                        logger.info(f"📝 [WORD]: Đang bóc tách Văn bản & Bảng biểu {path.name}...")
                        doc = Document(path)
                        full_content = [f"### 📝 [VĂN BẢN WORD: {path.name}]"]
                        for element in doc.element.body:
                            if element.tag.endswith('p'): # Paragraph
                                text = "".join(node.text for node in element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
                                if text.strip(): full_content.append(text)
                            elif element.tag.endswith('tbl'): # Table
                                table_index = list(doc.element.body.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')).index(element)
                                table = doc.tables[table_index]
                                table_data = []
                                for row in table.rows:
                                    table_data.append([cell.text.strip() for cell in row.cells])
                                if table_data:
                                    import pandas as pd
                                    df = pd.DataFrame(table_data)
                                    full_content.append("\n" + df.to_markdown(index=False, headers=False) + "\n")
                        result_md = "\n".join(full_content)
                    except Exception as docx_err:
                        logger.warning(f"⚠️ [WORD-ERR]: {docx_err}. Thử dùng MarkItDown...")

                # 🛠️ [GENERAL-CONVERTER]: MarkItDown cho các loại còn lại
                if not result_md and CONVERTER_AVAILABLE:
                    try:
                        result = _md.convert(str(path))
                        result_md = result.text_content
                    except Exception as md_err:
                        logger.error(f"❌ [MARKITDOWN-ERR]: {md_err}")
            
            # Mặc định đọc text thô nếu không phải định dạng nhị phân
            if not result_md:
                binary_exts = {".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".tar", ".gz"}
                if ext not in binary_exts:
                    try:
                        result_md = path.read_text(encoding="utf-8", errors="ignore")
                    except:
                        with open(path, "rb") as f:
                            result_md = f.read().decode('utf-8', errors='ignore')
            
            if not result_md:
                result_md = f"❌ [CONVERTER] Không thể đọc tệp nhị phân {ext}."

            # ⚡ [CACHE-SAVE]: Lưu vào bộ nhớ nóng cho các Đặc vụ khác dùng chung
            if result_md and not result_md.startswith('❌'):
                from redis_client import redis_safe
                redis_safe(lambda r: r.set(cache_key, result_md, ex=3600)) # Cache trong 1 giờ
            
            return result_md

        except Exception as e:
            logger.error(f"❌ [CONVERTER-ERR] {path.name}: {e}")
            return f"\n[ERROR CONVERTING {path.name}: {str(e)}]\n"
        except Exception as e:
            logger.error(f"❌ [CONVERTER-ERR] {path.name}: {e}")
            return f"\n[ERROR CONVERTING {path.name}: {str(e)}]\n"

# Singleton instance cho toàn hệ thống
converter = JKAI_Converter()
