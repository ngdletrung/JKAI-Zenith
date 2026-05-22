import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List
from core.utils.engine import engine

class ZenithSkillForge:
    """
    🏛️ ZENITH SKILL FORGE v1.0
    Bộ máy đúc và tối ưu hóa kỹ năng tự trị.
    Tích hợp Fuzzy Patching, Security Scan và Knowledge Absorption.
    """
    def __init__(self):
        self.skills_dir = Path("D:/Docker/N8N/intelligence/skills")
        self.quarantine_dir = Path("D:/Docker/N8N/intelligence/archive/quarantine")
        # [SECURITY-BLACKLIST]: Các lệnh và mẫu mã nguy hiểm
        self.blacklist = [
            r"rm\s+-rf\s+/", r"os\.remove\(.*\.py\)", r"shutil\.rmtree\(.*core.*\)",
            r"mkfs", r"dd\s+if=", r":\(\){ :\|:& };:", r"chmod\s+777"
        ]

    def security_scan(self, code_text: str):
        """Vệ binh An ninh: Quét các lệnh nguy hiểm."""
        for pattern in self.blacklist:
            if re.search(pattern, code_text, re.IGNORECASE):
                return False, f"Phát hiện mẫu mã nguy hiểm: {pattern}"
        return True, "An toàn"

    def auto_author_manifest(self, skill_id: str, logic_path: Path):
        """Tự động đúc Hiến chương cho kỹ năng chưa có tài liệu."""
        try:
            code = logic_path.read_text(encoding="utf-8")
            functions = re.findall(r'def\s+(\w+)\(', code)
            
            manifest = {
                "id": skill_id.upper(),
                "name_vn": f"Kỹ năng {skill_id.replace('_', ' ').capitalize()}",
                "version": "2.0.0",
                "author": "Zenith Forge Elite",
                "domain": "CORE",
                "intent_pairs": [["EXECUTE", skill_id.upper()]],
                "aliases_vn": [skill_id.replace("_", " ")],
                "schema": {
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Nội dung yêu cầu."}
                        },
                        "required": ["query"]
                    }
                },
                "priority": "NORMAL",
                "related_skills": []
            }
            
            yaml_header = "---\n" + yaml.dump(manifest, allow_unicode=True) + "---\n"
            
            body = f"\n# 🏛️ {manifest['name_vn'].upper()} ({skill_id.upper()})\n\n"
            body += "## 🌟 TỔNG QUAN\n"
            body += "Kỹ năng tự động được đúc bởi Zenith Forge. Mục tiêu: [Mô tả mục đích].\n\n"
            
            body += "## 🛠️ PHÁC ĐỒ VẬN HÀNH (OPERATIONAL PROTOCOL)\n\n"
            body += "### 🔍 Phase 1: Investigation (Thẩm định)\n"
            body += "1. Phân tích các tham số đầu vào và bối cảnh Master yêu cầu.\n"
            body += "2. Kiểm tra tính sẵn sàng của các tài nguyên hệ thống liên quan.\n\n"
            
            body += "### 🚀 Phase 2: Action (Thực thi)\n"
            body += f"1. Triệu hồi các hàm thực thi chính: {', '.join([f'`{f}`' for f in functions])}.\n"
            body += "2. Kiểm chứng kết quả và đúc kết báo cáo cho Master.\n\n"
            
            body += "## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)\n"
            body += "- [Hệ thống đang tự động theo dõi và cập nhật từ thực chiến].\n\n"
            
            body += "---\n*TRUNG THÀNH - CHÍNH XÁC - TỐI THƯỢNG* 💎🦾\n"
            
            return yaml_header + body
        except Exception as e:
            return f"Error: {e}"

    def patch_pitfalls(self, skill_id: str, lesson: str):
        """Tự động cập nhật bài học thực chiến vào mục Pitfalls."""
        skill_file = next(self.skills_dir.rglob(f"**/SKILL.md"), None) # Demo logic, will be improved
        if not skill_file: return False
        
        content = skill_file.read_text(encoding="utf-8")
        if "## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)" in content:
            new_entry = f"\n- {lesson} (Đúc rút từ thực chiến)"
            new_content = content.replace("## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)", 
                                        f"## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS){new_entry}")
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
        return False
    def validate_manifest(self, content: str):
        """Thẩm định Hiến chương theo chuẩn Sovereign v1.0."""
        if not content.startswith("---"):
            return False, "Thiếu YAML Frontmatter (---)"
        try:
            match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not match: return False, "YAML Frontmatter không đóng"
            meta = yaml.safe_load(match.group(1))
            required = ["id", "name_vn", "domain", "intent_pairs"]
            for field in required:
                if field not in meta: return False, f"Thiếu trường bắt buộc: {field}"
            return True, meta
        except Exception as e:
            return False, f"Lỗi YAML: {e}"

    def fuzzy_patch(self, skill_id: str, old_text: str, new_text: str):
        """Vá kỹ năng bằng cơ chế mờ (Fuzzy Patch)."""
        # [MACRO-STRATEGY]: Tìm kiếm file SKILL.md trong mọi Domain
        skill_file = next(self.skills_dir.rglob(f"**/SKILL.md"), None)
        if not skill_file: return {"success": False, "error": "Không tìm thấy kỹ năng"}
        
        content = skill_file.read_text(encoding="utf-8")
        # Logic đơn giản hóa cho Fuzzy Match (Bỏ qua khoảng trắng thừa)
        pattern = re.escape(old_text.strip()).replace(r'\ ', r'\s+')
        new_content, count = re.subn(pattern, new_text, content, flags=re.DOTALL)
        
        if count == 0:
            return {"success": False, "error": "Không khớp được nội dung cần vá."}
            
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return {"success": True, "count": count, "path": str(skill_file)}

    def absorb_skill(self, source_id: str, target_id: str):
        """Hấp thụ kỹ năng: Di chuyển nội dung và đánh dấu liên kết."""
        # [MACRO-CONSOLIDATION]: Đảm bảo tri thức không bị đứt gãy
        # 1. Tìm đường dẫn
        source_path = next(self.skills_dir.rglob(source_id), None)
        target_path = next(self.skills_dir.rglob(target_id), None)
        
        if not source_path or not target_path:
            return {"success": False, "error": "Không tìm thấy nguồn hoặc đích"}
            
        # 2. Ghi nhật ký hấp thụ vào SKILL.md của đích
        target_md = target_path / "SKILL.md"
        if target_md.exists():
            with open(target_md, "a", encoding="utf-8") as f:
                f.write(f"\n\n> [!NOTE]\n> Kỹ năng này đã hấp thụ tri thức từ `{source_id}`.\n")
        
        # 3. Di chuyển nguồn vào khu lưu trữ
        import shutil
        shutil.move(str(source_path), str(self.quarantine_dir / f"absorbed_{source_id}"))
        return {"success": True}

    async def auto_heal_skill(self, skill_id: str, error_detail: str, task_id: str = "sys") -> Dict[str, Any]:
        """
        🚀 GIAO THỨC TỰ SỬA LỖI & TIẾN HÓA KỸ NĂNG (SELF-HEALING LOOP)
        Khi chạy skill gặp sự cố, tự động chẩn đoán lỗi, viết code sửa lỗi,
        kiểm tra cú pháp và triển khai bản vá vinh quang.
        """
        engine.publish_mission_log("SKILL-FORGE", f"🛠️ [SELF-HEALING] Phát hiện sự cố tại `{skill_id}`: {error_detail[:80]}", task_id)
        
        skill_dir = None
        # Tìm thư mục kỹ năng
        for p in self.skills_dir.rglob("*"):
            if p.is_dir() and p.name.lower() == skill_id.lower():
                skill_dir = p
                break
        
        if not skill_dir:
            return {"success": False, "error": f"Không tìm thấy thư mục kỹ năng: {skill_id}"}
            
        logic_path = skill_dir / "logic.py"
        skill_md_path = skill_dir / "SKILL.md"
        
        if not logic_path.exists():
            return {"success": False, "error": f"Không tìm thấy logic.py tại {skill_dir}"}
            
        old_code = logic_path.read_text(encoding="utf-8")
        
        prompt = f"""Bạn là Lõi Sửa Lỗi Tối Cao (Self-Healing Core) của Zenith OS.
Kỹ năng `{skill_id}` đã bị lỗi trong quá trình thực thi.

ĐƯỜNG DẪN: {logic_path}
CHI TIẾT LỖI / TRACEBACK:
{error_detail}

MÃ NGUỒN HIỆN TẠI (logic.py):
```python
{old_code}
```

Hãy phân tích nguyên nhân gốc (ví dụ: thiếu thư viện, lỗi cú pháp, sai tham số, logic crash) và cung cấp mã nguồn mới HOÀN TOÀN ĐÃ ĐƯỢC SỬA LỖI.
Yêu cầu trả về JSON định dạng chuẩn xác:
{{"root_cause": "Phân tích nguyên nhân lỗi", "solution": "Cách giải quyết", "new_code": "Mã nguồn mới hoàn chỉnh 100%"}}"""

        try:
            resp = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="PLANNER",
                task_id=task_id,
                json_mode=True
            )
            
            if isinstance(resp, str):
                match = re.search(r'\{.*\}', resp, re.DOTALL)
                if match:
                    resp = json.loads(match.group())
            
            new_code = resp.get("new_code")
            root_cause = resp.get("root_cause", "Lỗi runtime")
            solution = resp.get("solution", "Tự động tối ưu hóa")
            
            if not new_code:
                return {"success": False, "error": "Không nhận được mã nguồn sửa đổi."}
                
            # Quét An ninh & Kiểm tra cú pháp
            ok, sec_msg = self.security_scan(new_code)
            if not ok:
                return {"success": False, "error": f"Bản vá bị chặn bởi Security: {sec_msg}"}
                
            try:
                compile(new_code, str(logic_path), 'exec')
            except SyntaxError as se:
                return {"success": False, "error": f"Bản vá chứa lỗi cú pháp: {se}"}
                
            # Ghi đè mã nguồn mới
            with open(logic_path, "w", encoding="utf-8") as f:
                f.write(new_code)
                
            # Cập nhật SKILL.md
            if skill_md_path.exists():
                md_content = skill_md_path.read_text(encoding="utf-8")
                v_match = re.search(r"version:\s*([0-9.]+)", md_content)
                if v_match:
                    old_v = v_match.group(1)
                    parts = old_v.split('.')
                    if len(parts) == 3:
                        new_v = f"{parts[0]}.{parts[1]}.{int(parts[2])+1}"
                        md_content = md_content.replace(f"version: {old_v}", f"version: {new_v}")
                
                lesson = f"Đã khắc phục lỗi: {root_cause} -> Giải pháp: {solution}"
                if "## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)" in md_content:
                    md_content = md_content.replace(
                        "## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)",
                        f"## ⚠️ SAI LẦM THƯỜNG GẶP (COMMON PITFALLS)\n- {lesson} (Đúc rút từ Tự Sửa Lỗi)"
                    )
                with open(skill_md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
            
            engine.publish_mission_log(
                "SKILL-FORGE",
                f"✅ [SELF-HEALING] Kỹ năng `{skill_id}` đã tự động sửa lỗi và tiến hóa thành công!",
                task_id
            )
            return {"success": True, "root_cause": root_cause, "solution": solution}
            
        except Exception as e:
            return {"success": False, "error": f"Lỗi trong quá trình đúc bản vá: {e}"}

skill_forge = ZenithSkillForge()
