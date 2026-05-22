import os
import json
import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

# 🛰️ JKAI ENGINE IMPORTS
from core.utils.engine import engine
from core.utils.converter import converter
from core.utils import path_manager

# =================================================================
# 🎭 JKAI SKILL #43: TEMPLATE MIMIC (v1.0)
# =================================================================
# Mục tiêu: Học phong cách, định dạng và cấu trúc từ file mẫu.
# Triết lý: Sao chép linh hồn, tái cấu trúc thực thể.
# =================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jkai.skill.mimic")

class TemplateMimic:
    def __init__(self):
        # 💎 DYNAMIC COORDINATE RESOLUTION
        vault_raw = path_manager.get("VAULT_TEMPLATES", "intelligence/vault/templates")
        self.vault_path = Path(vault_raw)
        self.vault_path.mkdir(parents=True, exist_ok=True)

    async def learn_template(self, file_path: str, template_name: str, task_id: str = "sys"):
        """Đọc và học cấu trúc từ một file mẫu."""
        engine.publish_mission_log("MIMIC", f"🧐 Đang nghiên cứu file mẫu: `{os.path.basename(file_path)}`", task_id)
        engine.publish_progress(20, "Đang trích xuất nội dung...", task_id)

        try:
            # 1. Chuyển đổi sang Markdown để AI dễ đọc
            content = await converter.to_markdown(file_path)
            
            # 2. Gọi PLANNER để phân tích cấu trúc
            engine.publish_progress(50, "Đang phân tích cấu trúc & phong cách...", task_id)
            prompt = f"""
            [HỆ THỐNG PHÂN TÍCH BIỂU MẪU v1.0]
            Nhiệm vụ: Phân tích file mẫu sau đây để trích xuất 'Linh hồn định dạng'.
            
            YÊU CẦU:
            - Xác định các phân mục chính (Headers).
            - Xác định tông giọng (Tone of voice).
            - Xác định các placeholder cần điền (ví dụ: [Tên], {{Ngày}}, ...).
            - Ghi chú các quy tắc định dạng đặc biệt (Bảng biểu, danh sách, ...).

            NỘI DUNG FILE MẪU:
            {content[:5000]}

            TRẢ VỀ JSON:
            {{
                "template_name": "{template_name}",
                "structure": ["Mục 1", "Mục 2", "..."],
                "tone": "Chuyên nghiệp/Trang trọng/...",
                "placeholders": ["field1", "field2"],
                "rules": "Quy tắc định dạng quan trọng",
                "full_blueprint": "Bản mô tả chi tiết để AI khác có thể bắt chước 100%"
            }}
            """
            
            blueprint = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="PLANNER",
                json_mode=True,
                task_id=task_id
            )

            # 3. Lưu vào Vault
            save_path = self.vault_path / f"{template_name}.json"
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(blueprint, f, indent=4, ensure_ascii=False)

            engine.publish_mission_log("MIMIC", f"✅ Đã học xong biểu mẫu: `{template_name}`. Sẵn sàng tái tạo!", task_id)
            engine.publish_progress(100, "Hoàn tất học mẫu.", task_id)
            
            return {"status": "success", "template": blueprint}

        except Exception as e:
            logger.error(f"❌ [MIMIC-LEARN-ERR] {e}")
            return {"status": "error", "msg": str(e)}

    async def apply_template(self, template_name: str, data: Dict[str, Any], output_name: str, task_id: str = "sys"):
        """Áp dụng biểu mẫu đã học vào dữ liệu mới."""
        engine.publish_mission_log("MIMIC", f"⚒️ Đang đúc tài liệu mới dựa trên mẫu: `{template_name}`", task_id)
        
        template_file = self.vault_path / f"{template_name}.json"
        if not template_file.exists():
            return {"status": "error", "msg": "Template không tồn tại."}

        with open(template_file, "r", encoding="utf-8") as f:
            blueprint = json.load(f)

        # Gọi AI để viết nội dung dựa trên Blueprint và Data
        prompt = f"""
        [HỆ THỐNG KIẾN TẠO TÀI LIỆU v1.1]
        Nhiệm vụ: Viết một tài liệu MỚI dựa trên BIỂU MẪU sau.
        
        BIỂU MẪU (BLUEPRINT):
        {json.dumps(blueprint, indent=2, ensure_ascii=False)}

        DỮ LIỆU ĐẦU VÀO:
        {json.dumps(data, indent=2, ensure_ascii=False)}

        YÊU CẦU:
        - Tuân thủ 100% cấu trúc và tông giọng của biểu mẫu.
        - Thay thế các placeholder bằng dữ liệu thực tế.
        - Trả về nội dung định dạng Markdown Elite.
        """

        engine.publish_progress(60, "Đang chưng cất nội dung...", task_id)
        result = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="EXECUTOR",
            task_id=task_id
        )

        # 💎 SMART PATHING: Lưu vào khu vực files/output chuẩn
        output_dir_raw = path_manager.get("FILES_OUTPUT", "files/Output")
        output_dir = Path(output_dir_raw)
        output_dir.mkdir(parents=True, exist_ok=True)
        final_path = output_dir / f"{output_name}.md"
        
        with open(final_path, "w", encoding="utf-8") as f:
            f.write(result)

        engine.publish_mission_log("MIMIC", f"🚀 Đã kiến tạo thành công tài liệu: `{output_name}.md` tại files/output.", task_id)
        engine.publish_progress(100, "Nhiệm vụ hoàn tất.", task_id)
        
        return {"status": "success", "path": str(final_path)}

# 🚀 Singleton instance
_instance = TemplateMimic()

async def learn_template(**kwargs):
    return await _instance.learn_template(**kwargs)

async def apply_template(**kwargs):
    return await _instance.apply_template(**kwargs)
