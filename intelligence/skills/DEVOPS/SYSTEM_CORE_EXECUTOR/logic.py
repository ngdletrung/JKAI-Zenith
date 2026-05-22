import os
import subprocess
import json
import shutil
import asyncio
from typing import Optional, List, Dict

# ⚙️ [ZENITH-SYSTEM-CORE]: Hệ vận động cốt lõi của JKAI.

async def list_dir(path: str = ".", task_id: str = "sys"):
    """📂 [SCOUTING]: Liệt kê danh sách tệp tin và thư mục."""
    try:
        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            result.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": size
            })
        return {"status": "success", "path": os.abspath(path), "items": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def view_file(path: str, start_line: int = 1, end_line: int = 500, task_id: str = "sys"):
    """👁️ [VISION]: Đọc nội dung tệp tin thấu thị."""
    try:
        if not os.path.exists(path):
            return {"status": "error", "msg": f"File '{path}' không tồn tại."}
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        content = "".join(lines[start_line-1:end_line])
        return {
            "status": "success",
            "path": os.abspath(path),
            "total_lines": len(lines),
            "content": content
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def write_to_file(path: str, content: str, overwrite: bool = False, task_id: str = "sys"):
    """✍️ [CREATION]: Kiến tạo tệp tin mới."""
    try:
        if os.path.exists(path) and not overwrite:
            return {"status": "error", "msg": f"File '{path}' đã tồn tại. Dùng overwrite=True để ghi đè."}
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "msg": f"Đã kiến tạo tệp `{path}` thành công."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def replace_file_content(path: str, target: str, replacement: str, task_id: str = "sys"):
    """🛠️ [SURGERY]: Phẫu thuật thay thế nội dung tệp tin."""
    try:
        if not os.path.exists(path):
            return {"status": "error", "msg": f"File '{path}' không tồn tại."}
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if target not in content:
            return {"status": "error", "msg": f"Không tìm thấy đoạn hội thoại mục tiêu trong `{path}`."}
            
        new_content = content.replace(target, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return {"status": "success", "msg": f"Phẫu thuật thành công trên tệp `{path}`."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def run_command(command: str, task_id: str = "sys"):
    """⚡ [EXECUTION]: Thực thi mật lệnh hệ thống."""
    try:
        # Chạy lệnh trong shell
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        return {
            "status": "success",
            "stdout": stdout.decode(errors="ignore"),
            "stderr": stderr.decode(errors="ignore"),
            "exit_code": process.returncode
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def multi_replace_file_content(path: str, replacements: List[Dict[str, str]], task_id: str = "sys"):
    """🔬 [MULTI-SURGERY]: Phẫu thuật đa điểm trên tệp tin."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        for r in replacements:
            target = r.get("target")
            rep = r.get("replacement")
            if target in content:
                content = content.replace(target, rep)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "msg": f"Đã thực hiện {len(replacements)} ca phẫu thuật trên `{path}`."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def command_status(command_id: str, task_id: str = "sys"):
    """📊 [MONITORING]: Kiểm tra trạng thái mật lệnh đang chạy."""
    return {"status": "success", "msg": "Tính năng đang được đồng bộ hóa với hệ thống n8n."}

async def search_web(query: str, task_id: str = "sys"):
    """🌐 [RECON]: Tầm soát Internet thấu thị."""
    from intelligence.skills.skill_sieutimkiem.logic import tim_kiem_web
    return await tim_kiem_web(query, task_id)

async def read_url_content(url: str, task_id: str = "sys"):
    """📄 [VISION]: Đọc nội dung URL thấu thị."""
    from intelligence.skills.skill_sieutimkiem.logic import cao_du_lieu_web
    return await cao_du_lieu_web(url)

async def generate_image(prompt: str, task_id: str = "sys"):
    """🎨 [CREATION]: Kiến tạo hình ảnh từ tri tưởng tượng."""
    from intelligence.skills.skill_generate_image.logic import skill_generate_image
    return await skill_generate_image(prompt=prompt, task_id=task_id)

async def grep_search(query: str, path: str = ".", task_id: str = "sys"):
    """🔍 [SCANNER]: Quét tìm từ khóa trong toàn bộ thư mục."""
    from intelligence.skills.skill_sieutimkiem.logic import truy_luc_thuc_dia
    return await truy_luc_thuc_dia(query, path, task_id=task_id)
