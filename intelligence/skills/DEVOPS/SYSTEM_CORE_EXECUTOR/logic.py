import os
import subprocess
import json
import shutil
import asyncio
from typing import Optional, List, Dict
from core.utils.security_audit import auditor
from core.utils.engine import engine

# ⚙️ [ZENITH-SYSTEM-CORE]: Hệ vận động cốt lõi của JKAI.

async def list_dir(path: str = ".", directory_path: str = ".", task_id: str = "sys", **kwargs):
    """📂 [SCOUTING]: Liệt kê danh sách tệp tin và thư mục."""
    target_path = path if path != "." else (directory_path or ".")
    try:
        items = os.listdir(target_path)
        result = []
        for item in items:
            full_path = os.path.join(target_path, item)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            result.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": size
            })
        return {"status": "success", "path": os.path.abspath(target_path), "items": result}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def view_file(path: str = "", file_path: str = "", AbsolutePath: str = "", start_line: int = 1, end_line: int = 500, task_id: str = "sys", **kwargs):
    """👁️ [VISION]: Đọc nội dung tệp tin thấu thị."""
    target_path = path or file_path or AbsolutePath or ""
    try:
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}
        
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        content = "".join(lines[start_line-1:end_line])
        return {
            "status": "success",
            "path": os.path.abspath(target_path),
            "total_lines": len(lines),
            "content": content
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def write_to_file(path: str = "", file_path: str = "", TargetFile: str = "", content: str = "", CodeContent: str = "", overwrite: bool = False, task_id: str = "sys", **kwargs):
    """✍️ [CREATION]: Kiến tạo tệp tin mới."""
    target_path = path or file_path or TargetFile or ""
    target_content = content or CodeContent or ""
    try:
        if os.path.exists(target_path) and not overwrite:
            return {"status": "error", "msg": f"File '{target_path}' đã tồn tại. Dùng overwrite=True để ghi đè."}
        
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # 🛡️ [SECURITY-AUDIT]: Thẩm định an ninh trước khi ghi file
        report = auditor.audit_diff(target_content)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định tệp `{target_path}`:\n{log_msg}", task_id)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(target_content)
        return {"status": "success", "msg": f"Đã kiến tạo tệp `{target_path}` thành công."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def replace_file_content(path: str = "", file_path: str = "", TargetFile: str = "", target: str = "", TargetContent: str = "", replacement: str = "", ReplacementContent: str = "", task_id: str = "sys", **kwargs):
    """🛠️ [SURGERY]: Phẫu thuật thay thế nội dung tệp tin."""
    target_path = path or file_path or TargetFile or ""
    tgt = target or TargetContent or ""
    repl = replacement or ReplacementContent or ""
    try:
        if not os.path.exists(target_path):
            return {"status": "error", "msg": f"File '{target_path}' không tồn tại."}
        
        with open(target_path, "r", encoding="utf-8") as f:
            file_content = f.read()
            
        if tgt not in file_content:
            return {"status": "error", "msg": f"Không tìm thấy đoạn hội thoại mục tiêu trong `{target_path}`."}
            
        new_content = file_content.replace(tgt, repl)
        
        # 🛡️ [SECURITY-AUDIT]: Thẩm định an ninh phần thay thế
        report = auditor.audit_diff(repl)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định phẫu thuật trên `{target_path}`:\n{log_msg}", task_id)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return {"status": "success", "msg": f"Phẫu thuật thành công trên tệp `{target_path}`."}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def run_command(command: str = "", CommandLine: str = "", task_id: str = "sys", **kwargs):
    """⚡ [EXECUTION]: Thực thi mật lệnh hệ thống."""
    cmd = command or CommandLine or ""
    try:
        # 🛡️ [SECURITY-AUDIT]: Thẩm định lệnh shell
        report = auditor.audit_diff(cmd)
        if report.factors:
            log_msg = auditor.format_report_for_log(report)
            tag = "RISK" if report.is_dangerous else "AUDIT"
            engine.publish_mission_log(tag, f"Thẩm định mật lệnh `{cmd}`:\n{log_msg}", task_id)

        # Chạy lệnh trong shell
        process = await asyncio.create_subprocess_shell(
            cmd,
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

def _clean_query(query) -> str:
    if not query:
        return ""
    if isinstance(query, dict):
        for key in ["query", "q", "extracted_params", "description", "value"]:
            if val := query.get(key):
                return _clean_query(val)
        if len(query) == 1:
            return _clean_query(list(query.values())[0])
        return json.dumps(query)
    if isinstance(query, list):
        if len(query) > 0:
            return _clean_query(query[0])
        return ""
    if isinstance(query, str):
        query_str = query.strip()
        if query_str.startswith("{") and query_str.endswith("}"):
            try:
                parsed = json.loads(query_str)
                return _clean_query(parsed)
            except Exception:
                pass
        return query_str
    return str(query)

async def search_web(query: str, task_id: str = "sys"):
    """🌐 [RECON]: Tầm soát Internet thấu thị."""
    query = _clean_query(query)
    try:
        from intelligence.skills.CORE.OMNI_SEARCH_ENGINE.logic import omni_search
        return await omni_search(query=query, task_id=task_id)
    except Exception as e:
        import httpx
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post("https://api.tavily.com/search", json={
                        "api_key": api_key, "query": query, "search_depth": "advanced"
                    })
                    if resp.status_code == 200:
                        return resp.json()
                    else:
                        return {"status": "error", "msg": f"Tavily API Error: {resp.status_code} - {resp.text}"}
            except Exception as ex:
                return {"status": "error", "msg": f"Search Connection Fault: {str(ex)}"}
        return {"status": "error", "msg": f"Search failed: {str(e)}"}

async def read_url_content(url: str, task_id: str = "sys"):
    """📄 [VISION]: Đọc nội dung URL thấu thị."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"https://r.jina.ai/{url}")
            if resp.status_code == 200:
                return {"status": "success", "content": resp.text[:5000]}
            else:
                return {"status": "error", "msg": f"Jina.ai API Error: {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

async def generate_image(prompt: str, task_id: str = "sys"):
    """🎨 [CREATION]: Kiến tạo hình ảnh từ tri tưởng tượng."""
    from intelligence.skills.skill_generate_image.logic import skill_generate_image
    return await skill_generate_image(prompt=prompt, task_id=task_id)

async def grep_search(query: str, path: str = ".", task_id: str = "sys"):
    """🔍 [SCANNER]: Quét tìm từ khóa trong toàn bộ thư mục."""
    import re
    import concurrent.futures
    from pathlib import Path
    
    if not path or path == ".":
        path = os.getcwd()
        
    base_path = Path(path)
    pattern = re.compile(query, re.IGNORECASE)
    
    results = []
    
    def scan_file(file_path):
        file_results = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if pattern.search(line):
                        file_results.append({
                            "file": str(file_path),
                            "line": i,
                            "content": line.strip()
                        })
        except Exception:
            pass
        return file_results

    try:
        target_files = []
        for ext in [".py", ".js", ".md", ".txt", ".json", ".xml", ".ini", ".yaml", ".yml", ".ts", ".tsx", ".html", ".css"]:
            target_files.extend(
                [f for f in base_path.rglob(f"*{ext}") 
                 if not any(x in str(f) for x in [".git", "node_modules", "__pycache__", ".svelte-kit", "dist", "build"])]
            )
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {executor.submit(scan_file, f): f for f in target_files}
            for future in concurrent.futures.as_completed(future_to_file):
                results.extend(future.result())

        if not results:
            return {"status": "success", "msg": "Không tìm thấy kết quả nào trên thực địa."}

        report = f"✅ Đã tìm thấy {len(results)} kết quả. Dưới đây là các vị trí trọng tâm:\n"
        for r in results[:20]:
            report += f"- `{r['file']}:{r['line']}`: {r['content'][:100]}\n"
            
        return {
            "status": "success",
            "count": len(results),
            "data": results[:50],
            "report": report
        }
    except Exception as e:
        return {"status": "error", "msg": str(e)}

