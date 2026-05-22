import os
import json
import shutil
import asyncio
import logging
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# ⚠️ LAZY IMPORTS: Không import nặng ở cấp module để tránh crash khi ToolRouter nạp
# JKAIIntelligenceEngine, qdrant_client, embed sẽ được import trong hàm khi cần
from core.utils.engine import engine
from core.utils.converter import converter

# =================================================================
# 🛰️ JKAI ASSIMILATOR: QUANTUM LEAP EDITION (v31.0)
# =================================================================
# Mục tiêu: Đồng hóa tri thức và tự tiến hóa năng lực hệ thống.
# Quy trình: Scan -> Neural Audit -> Quantum Sync -> Registry Integration
# =================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jkai.assimilator")

class JKAI_Assimilator:
    def __init__(self):
        # 🧪 Load Neural Registry (Chuẩn v31.0)
        self.registry_path = "D:/Docker/N8N/intelligence/registry.json"
        if not os.path.exists(self.registry_path): self.registry_path = "/intelligence/registry.json"
        
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self.registry = json.load(f)
        except:
            self.registry = {}
            logger.error("❌ [ASSIMILATOR] Could not load registry.json")

        # 🌍 Tự động nhận diện môi trường (Docker vs Host)
        if os.path.exists("/intelligence"):
            self.base_dir = Path("/intelligence")
        else:
            self.base_dir = Path("D:/Docker/N8N/intelligence")
            
        # 📂 Cấu trúc thư mục chuẩn JKAI Zenith
        self.archive_dir = self.base_dir / "archive"
        self.import_dir = self.archive_dir / "import_dump"
        self.quarantine_dir = self.archive_dir / "quarantine"
        self.processed_dir = self.archive_dir / "processed"
        
        # 🗺️ Bản đồ thư mục đích (Registry)
        self.dest_map = {
            "agents": self.base_dir / "agents",
            "rules": self.base_dir / "rules",
            "skills": self.base_dir / "skills",
            "knowledge": self.base_dir / "knowledge",
            "tools": self.base_dir / "tools",
            "commands": self.base_dir / "commands",
            "prompts": self.base_dir / "prompts",
            "vault": self.base_dir / "vault",
            "protocols": self.base_dir / "protocols",
            "training": self.base_dir / "training",
            "archive": self.base_dir / "archive",
            "obsidian": self.base_dir / "obsidian"
        }
        
        # 🛡️ DANH SÁCH VÙNG CẤM (CORE PROTECTION)
        self.protected_files = [
            "agent_planner.md", "agent_critic.md", "agent_receptionist.md", "agent_executor.md",
            "rule_hardware.md", "ELITE_SYSTEM_PROTOCOLS.md", "ELITE_SOP_NEURAL_LOGIC.md",
            "JKAI_MANIFESTO.md", "INDEX.md", "MAP_AGENTS.md", "MAP_SKILLS.md", 
            "MAP_KNOWLEDGE.md", "MAP_RULES.md", "map.json"
        ]
        
        # Đảm bảo thư mục tồn tại
        for path in self.dest_map.values():
            path.mkdir(parents=True, exist_ok=True)

        # Lazy-init engine để tránh crash khi import module
        self._engine = None
        self.semaphore = asyncio.Semaphore(5)

    async def run_assimilation(self, limit: int = 1000, profile: str = "UNIFIED_ELITE", task_id: str = "sys"):
        """Quét đệ quy và đồng hóa toàn bộ nội dung từ kho lưu trữ."""
        if not self.import_dir.exists():
            return {"status": "error", "msg": f"Archive dump missing at {self.import_dir}"}

        # 0. TIỀN KIỂM: Tẩy rửa bóng ma (Ghost Cleaning)
        self.pre_audit_cleanup()

        # Quét đệ quy toàn bộ file
        valid_extensions = {
            ".md", ".txt", ".py", ".json", ".js", ".ts", ".html", ".css", ".go", ".rs", ".java", ".c", ".cpp", ".sh", ".yaml", ".yml", ".toml", ".jsonl", ".bash",
            ".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".xml" # 📄 MỞ RỘNG ĐỊNH DẠNG ELITE (v13.0)
        }
        exclude_dirs = {".git", ".github", "node_modules", "tr", "examples"} # Mở khóa .agents, .kiro, .opencode cho Master

        items = []
        for f in self.import_dir.rglob("*"):
            if f.is_file(): # Cho phép cả dotfiles nếu có extension hợp lệ thưa Master
                if any(ex_dir in f.parts for ex_dir in exclude_dirs):
                    continue
                ext = f.suffix.lower()
                if ext in valid_extensions:
                    items.append(f)

        if not items:
            return {"status": "idle", "msg": "Kho lưu trữ sạch."}

        total = min(len(items), limit)
        logger.info(f"🚀 [ELITE] Khởi động QUY TRÌNH ĐỒNG HÓA TỔNG LỰC: {total} tài liệu...")
        
        results = []
        completed = 0
        
        # 💎 [PROGRESS-START]
        engine.publish_progress(0, f"Bắt đầu đồng hóa {total} tài liệu...", task_id)

        async def safe_process(item):
            async with self.semaphore:
                return await self.process_item(item, profile=profile)

        tasks = [safe_process(item) for item in items[:limit]]
        
        # Chạy và báo cáo tiến độ từng phần thưa Master
        for f in asyncio.as_completed(tasks):
            res = await f
            results.append(res)
            completed += 1
            pct = int(completed * 100 / total)
            status_msg = f"💎 [ASSIMILATING] {completed}/{total} - {res.get('item', 'Unknown')}"
            engine.publish_progress(pct, status_msg, task_id)
            if completed % 5 == 0 or completed == total:
                engine.publish_mission_log("ASSIMILATOR", f"🦾 Đã đồng hóa {completed}/{total} tài liệu vào Registry.", task_id)

        return {"status": "success", "results": results, "output": f"✅ [ELITE] Đã đồng hóa {completed} tài liệu vào hệ sinh thái thưa Master."}

    def pre_audit_cleanup(self):
        """Rà soát và xóa bỏ các chỉ mục không còn tồn tại tệp tin thực tế."""
        logger.info("🛡️ [AUDIT] Bắt đầu rà soát Hồ sơ Trí tuệ (Ghost Cleaning)...")
        for category in self.dest_map.keys():
            map_filename = f"MAP_{category.upper()}.md"
            map_path = self.base_dir / map_filename
            if not map_path.exists(): continue

            try:
                content = map_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                new_lines = []
                cleaned_count = 0
                
                header_passed = False
                for line in lines:
                    if "| ⭐" in line or "- 💠" in line:
                        header_passed = True
                        # Trích xuất đường dẫn: (./category/filename) hoặc `./category/filename`
                        match = re.search(r'[`\(](\./.*?)[`\)]', line)
                        if match:
                            rel_path = match.group(1)
                            abs_path = self.base_dir / rel_path
                            if abs_path.exists():
                                new_lines.append(line)
                            else:
                                cleaned_count += 1
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                if cleaned_count > 0:
                    map_path.write_text("\n".join(new_lines), encoding="utf-8")
                    logger.info(f"🧹 [CLEANED] Đã xóa {cleaned_count} bóng ma khỏi {map_filename}")
            except Exception as e:
                logger.error(f"❌ [AUDIT-ERR] {map_filename}: {e}")

    async def run_general_offensive(self, task_id: str = "sys", limit_folders: int = 5):
        """
        🚀 GIAO THỨC TỔNG TIẾN CÔNG (B1-B4) - TỐI ƯU HÓA CHỐNG TIMEOUT
        Đồng hóa kho tri thức tại archive/import_dump theo từng đợt thưa Master.
        """
        # B0: KHỞI ĐỘNG CHIẾN DỊCH
        engine.publish_mission_log("ASSIMILATOR", f"☢️ [NUCLEAR-SYNC] Khởi động QUY TRÌNH TỔNG TIẾN CÔNG v13.0... (Đợt: {limit_folders} thư mục)", task_id)
        engine.publish_progress(5, "Đang quét kho lưu trữ...", task_id)
        
        import_dump = self.base_dir / "archive" / "import_dump"
        if not import_dump.exists():
            engine.publish_mission_log("ASSIMILATOR", "❌ [OFFENSIVE-CANCEL] Không tìm thấy Import Dump.", task_id)
            return {"status": "error", "msg": "Import Dump missing."}

        report_stats = {"total_folders": 0, "ok": 0, "not_ok": 0, "processed_files": 0}
        
        # Lấy danh sách các thư mục cần xử lý thưa Master
        all_dirs = []
        for root, dirs, files in os.walk(import_dump):
            if files: # Chỉ tính các thư mục có file
                all_dirs.append(Path(root))
        
        total_found = len(all_dirs)
        target_dirs = all_dirs[:limit_folders]
        
        engine.publish_mission_log("ASSIMILATOR", f"🔍 Phát hiện {total_found} thư mục. Tiến hành tấn công {len(target_dirs)} mục tiêu hàng đầu.", task_id)

        # B1: QUÉT & NHẬN DIỆN
        for i, current_path in enumerate(target_dirs):
            files = [f for f in os.listdir(current_path) if os.path.isfile(current_path / f)]
            if not files: continue
            
            report_stats["total_folders"] += 1
            logger.info(f"📁 [B1-SCAN] Đang xử lý thư mục: {current_path.name} ({len(files)} tệp)")
            
            # Xử lý nhóm file liên quan
            result = await self.process_elite_group(current_path, files, task_id=task_id)
            
            if result["status"] == "success":
                report_stats["ok"] += 1
                engine.publish_mission_log("ASSIMILATOR", f"✅ [B3-OK] Đã đồng hóa: `{current_path.name}`", task_id)
            else:
                report_stats["not_ok"] += 1
                engine.publish_mission_log("ASSIMILATOR", f"⚠️ [B3-SKIP/ERROR] `{current_path.name}`: {result.get('msg', 'Unknown')}", task_id)
            
            report_stats["processed_files"] += len(files)
            
            # Cập nhật tiến độ tổng quát
            pct = int(((i + 1) / len(target_dirs)) * 100)
            progress_msg = f"📂 [PROGRESS] Đã xử lý {i+1}/{len(target_dirs)} mục tiêu."
            engine.publish_progress(pct, progress_msg, task_id)

        # B4: TỔNG KẾT & BÁO CÁO
        report = await self.generate_offensive_report(report_stats)
        return {"status": "success", "output": report, "remaining": total_found - len(target_dirs)}

    async def process_elite_group(self, folder_path: Path, files: List[str], profile: str = "UNIFIED_ELITE", task_id: str = "sys"):
        """B2 & B3: Rà soát chất lượng và Xử lý theo kết quả."""
        try:
            # Đọc tối đa 10 file đầu tiên để hiểu bối cảnh
            context_content = ""
            for f_name in files[:10]:
                f_path = folder_path / f_name
                context_content += f"\n--- FILE: {f_name} ---\n"
                context_content += self._read_file_content(f_path)[:2000]

            # B2: NEURAL AUDIT (Kiểm định C1, C2, C3)
            audit_result = await self.neural_audit(context_content, folder_path.name, profile=profile, task_id=task_id)
            logger.info(f"🔍 [AUDIT-RESULT] {folder_path.name}: OK={audit_result.get('is_ok')} | Category={audit_result.get('category')} | Reason={audit_result.get('reason')}")
            
            if not audit_result.get("is_ok"):
                # 🔴 TRƯỜNG HỢP NOT OK -> CÁCH LY
                return await self.quarantine_folder(folder_path, audit_result.get("reason", "Thiếu C1/C2/C3"))

            # 🟢 TRƯỜNG HỢP OK -> ĐỒNG HÓA ELITE
            return await self.assimilate_elite_folder(folder_path, files, audit_result, profile=profile, task_id=task_id)

        except Exception as e:
            logger.error(f"❌ [GROUP-ERR] {folder_path}: {e}")
            return {"status": "error", "msg": str(e)}

    async def neural_audit(self, content: str, folder_name: str, profile: str = "UNIFIED_ELITE", task_id: str = "sys") -> Dict:
        """[SOP v15.0] Kiểm định nơ-ron: Đọc, Tư duy và Chắt lọc tinh hoa."""
        prompt = f"""
        [HỆ THỐNG TƯ DUY PHẢN BIỆN v15.0 - JKAI ZENITH]
        Nhiệm vụ: Đọc và thẩm định nhóm tri thức từ: {folder_name}

        MỤC TIÊU CHIẾN LƯỢC:
        1. "Đào vàng" (Gem Discovery): Tìm ra những đoạn code ĐỘC ĐẠO, ý tưởng THÔNG MINH, hoặc giải thuật TỐI ƯU.
        2. So sánh (Comparison): Những thứ này có gì hay hơn tiêu chuẩn hiện tại của chúng ta không?
        3. Ứng dụng: Có thể dùng để nâng cấp Skill hiện có hay phải tạo ra Skill mới?

        NỘI DUNG TÀI LIỆU:
        {content[:3000]}

        TRẢ VỀ JSON:
        {{
            "is_ok": true/false,
            "reason": "Lý do",
            "category": "skills/rules/knowledge/...",
            "gems": [
                {{ "type": "code/concept", "description": "Mô tả viên ngọc", "value": "Tại sao nó quý giá?" }}
            ],
            "improvement_targets": ["Tên skill hiện tại có thể được nâng cấp"],
            "suggested_name": "ten_viet_khong_dau",
            "summary": "Tóm tắt giá trị đột biến"
        }}
        """
        # 🛡️ CHỈ ĐỊNH EXECUTOR: Thực thể thấu hiểu sâu sắc nhất để thẩm định tri thức thưa Master
        response = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="EXECUTOR", 
            task_id=task_id
        )
        try:
            clean_json = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(clean_json.group()) if clean_json else {"is_ok": False, "reason": "Lỗi định dạng JSON"}
        except: return {"is_ok": False, "reason": "Không thể phân tích phản hồi AI"}

    async def quarantine_folder(self, folder_path: Path, reason: str):
        """B3: Cách ly Mirror Path."""
        import_dump = self.base_dir / "archive" / "import_dump"
        relative_path = folder_path.relative_to(import_dump)
        quarantine_path = self.base_dir / "archive" / "quarantine" / relative_path
        
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        if folder_path.exists():
            shutil.move(str(folder_path), str(quarantine_path))
            (quarantine_path / "rejection_note.md").write_text(f"# ❌ LÝ DO CÁCH LY\n\n{reason}", encoding="utf-8")
            logger.warning(f"🔴 [QUARANTINE] Đã cách ly: {relative_path} -> {reason}")
        return {"status": "quarantined", "path": str(quarantine_path)}

    async def assimilate_elite_folder(self, folder_path: Path, files: List[str], audit: Dict, profile: str = "UNIFIED_ELITE", task_id: str = "sys"):
        """B3: Đồng hóa Elite với cấu trúc Bộ Tứ hoặc tương ứng."""
        category = audit.get("category", "knowledge")
        folder_name = self.sanitize_to_unsigned(audit.get("suggested_name", folder_path.name))
        
        # Đảm bảo phân khu tồn tại
        target_category_dir = self.dest_map.get(category, self.dest_map["knowledge"])
        dest_dir = target_category_dir / folder_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📍 [TARGET-PATH] Lưu trữ tại: {dest_dir.absolute()}")
        
        # 🔱 GIAO THỨC SINH TRƯỞNG BỘ TỨ (Dành riêng cho Skills)
        if category == "skills":
            logger.info(f"🧬 [EVOLVING] Đang kiến tạo Bộ Tứ Elite cho kỹ năng: {folder_name}")
            
            # Đọc nội dung gốc để AI phẫu thuật
            original_content = ""
            for f in files:
                f_path = folder_path / f
                content = self._read_file_content(f_path)
                original_content += content
            
            # Gọi JKAI để thiết kế Bộ Tứ
            suite = await self.generate_elite_suite(original_content, folder_name, profile=profile, task_id=task_id)
            
            # Lưu tệp tin
            (dest_dir / "logic.py").write_text(suite.get("logic_py", ""), encoding="utf-8")
            (dest_dir / "schema.json").write_text(json.dumps(suite.get("schema_json", {}), indent=4, ensure_ascii=False), encoding="utf-8")
            (dest_dir / "manual.md").write_text(suite.get("manual_md", ""), encoding="utf-8")
            (dest_dir / "workflow.md").write_text(suite.get("workflow_md", ""), encoding="utf-8")
            
            # Kiểm tra "Sức khỏe" (Syntax check)
            syntax_ok = self.check_python_syntax(dest_dir / "logic.py")
            audit["effectiveness"] = 1.0 if syntax_ok else 0.5
            if not syntax_ok:
                logger.warning(f"⚠️ [HEALTH-CHECK] Kỹ năng {folder_name} có lỗi cú pháp Python.")
        else:
            # Đối với các loại khác: Di chuyển và chuẩn hóa tên
            for f_name in files:
                shutil.move(str(folder_path / f_name), str(dest_dir / f_name))
            
        # Cập nhật Knowledge Map
        self.update_knowledge_map(audit, str(dest_dir), str(folder_path))
        
        # Dọn dẹp folder gốc (nếu rỗng)
        if folder_path.exists() and not os.listdir(folder_path):
            folder_path.rmdir()
            
        logger.info(f"🟢 [ASSIMILATED] {category}/{folder_name} - OK")
        engine.publish_mission_log("ASSIMILATOR", f"🧬 [PILLAR-UPDATE] Trụ cột `{category.upper()}` vừa tiếp nhận: `{folder_name}`", task_id)
        return {"status": "success", "dest": str(dest_dir)}

    async def generate_elite_suite(self, content: str, name: str, profile: str = "UNIFIED_ELITE", task_id: str = "sys") -> Dict:
        """[SOP v15.0] JKAI Zenith: Thiết kế Bộ Tứ Elite - Đột biến từ tinh hoa ngoại lai."""
        prompt = f"""
        [KIẾN TẠO TRI THỨC ĐỘT BIẾN v15.0]
        Kỹ năng: {name}
        
        NHIỆM VỤ CHIẾN LƯỢC:
        Dựa trên nội dung gốc, hãy thực hiện "Chưng cất tinh hoa" để tạo ra Bộ Tứ Elite:
        1. logic_py: Phải kế thừa những thuật toán hay nhất từ file gốc nhưng tối ưu lại theo chuẩn JKAI (Sử dụng `engine` để báo cáo log/progress). 
           ⚠️ CẢNH BÁO: Phải xóa sạch mọi dấu vết của brand cũ, thay bằng phong cách 'Zenith Sovereign'.
        2. schema_json: Thiết kế tham số đầu vào thông minh, linh hoạt.
        3. manual_md: Viết hướng dẫn vận hành theo phong cách "Bậc thầy điều khiển". Tập trung vào "Tại sao Master cần cái này?".
        4. workflow_md: Quy trình SOP tối giản nhưng cực kỳ hiệu quả.

        TRIẾT LÝ SÁNG TẠO: "Đứng trên vai người khổng lồ". Lấy cái hay của họ, cộng thêm trí tuệ của mình để tạo ra thứ vượt trội.

        NỘI DUNG GỐC:
        {content[:10000]}

        TRẢ VỀ JSON:
        {{
            "logic_py": "...",
            "schema_json": {{ ... }},
            "manual_md": "...",
            "workflow_md": "...",
            "gems_extracted": ["Những đoạn code hay nhất đã được tích hợp"]
        }}
        """
        # 🔱 [ELITE CORE]: Triệu tập EXECUTOR để kiến tạo bộ kỹ năng Elite thưa Master
        response = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="EXECUTOR",
            task_id=task_id
        )
        try:
            clean_json = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(clean_json.group())
        except: return {}

    def _read_file_content(self, file_path: Path) -> str:
        """⚡ GIAO THỨC ĐỌC THÔNG MINH: Sử dụng Hạt nhân Converter thưa Master."""
        try:
            # 📄 [CONVERTING] Triết xuất tri thức qua Core Converter
            return converter.to_markdown(str(file_path))
        except Exception as e:
            logger.error(f"❌ [READ-ERR] {file_path.name}: {e}")
            return f"\n[ERROR READING {file_path.name}]\n"

    def check_python_syntax(self, file_path: Path) -> bool:
        """Kiểm tra lỗi cú pháp Python."""
        try:
            import ast
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return True
        except:
            return False

    def sanitize_to_unsigned(self, text: str) -> str:
        """Chuyển tên sang Tiếng Việt không dấu, chữ thường, gạch dưới."""
        from unidecode import unidecode
        text = unidecode(text).lower()
        text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
        return text

    def update_knowledge_map(self, audit: Dict, dest_path: str, source_path: str):
        """Cập nhật bản đồ tri thức JSON."""
        map_path = self.base_dir / "knowledge_map.json"
        data = {"version": "1.2", "last_updated": time.ctime(), "total_items": 0, "by_skill": {}}
        
        if map_path.exists():
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except: pass
            
        entry = {
            "id": str(int(time.time())),
            "name": os.path.basename(dest_path),
            "path": dest_path,
            "source": source_path,
            "date_ingested": time.ctime(),
            "effectiveness_score": audit.get("effectiveness", 0.0),
            "notes": audit.get("summary", "")
        }
        
        cat = audit.get("category", "knowledge")
        if cat not in data["by_skill"]: data["by_skill"][cat] = []
        data["by_skill"][cat].append(entry)
        data["total_items"] += 1
        
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    async def generate_offensive_report(self, stats: Dict):
        """Báo cáo kết quả trận đánh chuẩn v12.0 Elite thưa Master."""
        report_dir = self.base_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"ingest_{time.strftime('%Y%m%d_%H%M%S')}.md"
        report_path = report_dir / report_name
        
        # 📊 Thu thập số liệu từ Knowledge Map để có con số chính xác theo 12 trụ cột
        map_path = self.base_dir / "knowledge_map.json"
        cat_stats = {}
        if map_path.exists():
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cat, items in data.get("by_skill", {}).items():
                        cat_stats[cat] = len(items)
            except: pass

        # 12 Trụ cột của Tập đoàn JKAI Zenith
        pillars = ["agents", "skills", "tools", "rules", "knowledge", "prompts", "commands", "protocols", "training", "vault", "archive", "obsidian"]
        
        table_rows = ""
        for p in pillars:
            count = cat_stats.get(p, 0)
            status = "🟢 ACTIVE" if count > 0 else "⚪ EMPTY"
            table_rows += f"| **{p.upper()}** | {count} | {status} |\n"

        content = f"""# ☢️ BÁO CÁO ĐỒNG BỘ TRI THỨC ELITE
Ngày thực hiện: {time.ctime()}
Tư lệnh thực thi: **JKAI_ASSIMILATOR v12.0**

## 📊 THỐNG KÊ CHIẾN TRƯỜNG TỔNG LỰC
| Trụ cột Tri thức | Số lượng | Trạng thái |
|:---|:---:|:---|
{table_rows}

## 💎 TỔNG KẾT CHIẾN DỊCH
- **Tổng thư mục rà soát**: {stats.get('total_folders', 0)}
- **Tổng tệp tin xử lý**: {stats.get('processed_files', 0)}
- **🟢 Thành công (OK)**: {stats.get('ok', 0)}
- **🔴 Cách ly (NOT OK)**: {stats.get('not_ok', 0)}

Hệ thống đã được thanh lọc và nạp vào Vector Database chuẩn v12.0. Mọi tri thức mới đã sẵn sàng phục vụ Master LeeTrung! 💎🫡🦾🚀🌌
"""
        report_path.write_text(content, encoding="utf-8")
        logger.info(f"📋 [REPORT] Đã xuất báo cáo: {report_name}")
        engine.publish_mission_log("MISSION_REPORT", f"📜 [FINAL] Chiến dịch đồng bộ hoàn tất. Đã xuất báo cáo: `{report_name}`")
        return content

    async def process_item(self, item: Path, profile: str = "UNIFIED_ELITE"):
        """Quy trình xử lý chuẩn hóa tệp tin."""
        try:
            content = item.read_text(encoding="utf-8", errors="ignore")
            if not content.strip(): return {"item": item.name, "status": "skipped"}

            # [ECC-INSPIRED] 🛡️ BẢN NĂNG BẢO MẬT: Rà soát nhạy cảm trước khi xử lý thưa Master
            security_report = self.security_scan(content, item.name)
            if security_report.get("is_dangerous"):
                logger.warning(f"🚨 [SECURITY-ALERT] {item.name}: {security_report.get('reason')}")
                engine.publish_mission_log("SECURITY", f"🚨 Cảnh báo bảo mật: `{item.name}` chứa {security_report.get('reason')}", task_id="sys")
                # Nếu cực kỳ nguy hiểm, tự động đưa vào cách ly thưa Master
                if security_report.get("severity") == "CRITICAL":
                    return await self.quarantine_folder(item.parent, f"SECURITY_CRITICAL: {security_report.get('reason')}")

            # AI Scrubbing (Elite Neutral Style + AI Category)
            assimilated_data = await self.ai_scrub(content, item.name, profile=profile)
            
            if assimilated_data.get("status") == "error" or not assimilated_data.get("content"):
                logger.error(f"❌ [ASSIMILATOR-ERR] Trí tuệ nhân tạo không thể xử lý (JSON parsing lỗi hoặc nội dung rỗng): {item.name}")
                return {"item": item.name, "status": "error", "msg": "AI Scrub failed to return valid JSON content."}
            
            # Ghi nhận kết quả bảo mật vào nội dung thưa Master
            if security_report.get("is_dangerous"):
                assimilated_data["content"] = f"> [!CAUTION]\n> 🚨 **CẢNH BÁO BẢO MẬT**: {security_report.get('reason')}\n\n" + assimilated_data["content"]
            
            # 🛡️ KIỂM TRA VÙNG CẤM (CORE PROTECTION)
            new_filename = self.sanitize_filename(assimilated_data.get('filename', item.name))
            if not new_filename.endswith(".md"): new_filename += ".md"
            
            if new_filename in self.protected_files:
                logger.warning(f"🛡️ [SECURITY] Chặn ghi đè file VÙNG LÕI: {new_filename}")
                return {"item": item.name, "status": "protected"}

            # Xác định thư mục đích dựa trên trí tuệ nhân tạo
            ai_cat = assimilated_data.get("category")
            category = self.detect_category(item, ai_cat)
            prefix = category.rstrip('s') # agents -> agent
            
            final_filename = f"{prefix}_{new_filename}"
            dest_path = self.dest_map.get(category, self.dest_map["knowledge"]) / final_filename
            
            with open(dest_path, "w", encoding="utf-8") as f:
                f.write(assimilated_data.get("content", ""))

            # 🌐 GIAO THỨC ĐỒNG BỘ VECTOR (Qdrant) - Lazy import
            try:
                from core.utils.embed import embed
                from core.qdrant_client import qdrant_client as qc
                txt = assimilated_data.get("content", "")
                rating = assimilated_data.get("rating", 3)
                vector = embed(txt[:1000])
                if vector:
                    await qc.upsert_intel(
                        text=txt,
                        embedding=vector,
                        metadata={"source": str(dest_path), "type": category, "rating": rating}
                    )
            except Exception as q_err:
                logger.warning(f"[QDRANT-SKIP] {q_err}")

            # 5. [NEW] Cập nhật Registry Trung tâm (Neural Registry v2.0)
            self._update_registry(
                category, 
                final_filename, 
                assimilated_data.get("notes", ""),
                int(rating)
            )

            self.archive_done(item)
            logger.info(f"✅ [ZENITH-OK] {item.name} -> {new_filename}")
            return {
                "item": item.name, 
                "status": "success", 
                "dest": str(dest_path),
                "new_filename": final_filename,
                "category": category,
                "rating": rating,
                "notes": assimilated_data.get("notes", "")
            }

        except Exception as e:
            logger.error(f"❌ [ASSIMILATOR-ERR] {item.name}: {e}")
            return {"item": item.name, "status": "error", "msg": str(e)}

    def _update_registry(self, category: str, filename: str, notes: str, rating: int):
        """Ghi danh vào Registry JSON theo tiêu chuẩn Định danh Toàn cầu (#ID)."""
        registry_path = self.base_dir / "registry.json"
        try:
            import json
            if not registry_path.exists():
                data = {c: {} for c in self.dest_map.keys()}
                data["last_updated"] = 0
            else:
                try:
                    data = json.loads(registry_path.read_text(encoding="utf-8"))
                except:
                    data = {c: {} for c in self.dest_map.keys()}
            
            if category not in data: data[category] = {}
            
            # 💎 GIAO THỨC ĐỊNH DANH TUYỆT ĐỐI (#ID)
            existing_id = data[category].get(filename, {}).get("id")
            if not existing_id:
                if category == "skills":
                    # Tìm số ID lớn nhất hiện tại
                    max_id = -1
                    for item in data.get("skills", {}).values():
                        try:
                            val = int(item.get("id", -1))
                            if val > max_id: max_id = val
                        except: pass
                    
                    new_id = f"{max_id + 1:02}"
                    existing_id = new_id
                else:
                    existing_id = filename.replace(".md", "").replace(f"{category[:-1]}_", "")

            # Đăng ký hồ sơ
            data[category][filename] = {
                "id": existing_id,
                "name": filename,
                "path": f"./{category}/{filename}",
                "notes": notes,
                "rating": rating,
                "ts": time.time()
            }
            data["last_updated"] = time.time()
            registry_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return existing_id
        except Exception as e:
            logger.error(f"❌ [REGISTRY-ERR] {e}")
            return None

    def update_master_index(self, category: str, filename: str, notes: str, stars: str, assigned_id: str = None):
        """Ghi danh tri thức vào Hồ sơ Trí tuệ (MAP_) theo tiêu chuẩn #ID thưa Master."""
        map_filename = f"MAP_{category.upper()}.md"
        map_path = self.base_dir / map_filename
        
        try:
            content = map_path.read_text(encoding="utf-8") if map_path.exists() else ""
            if filename in content: return # Tránh trùng

            # Định dạng entry theo tiêu chuẩn v17.0 thưa Master
            if category == "skills":
                # Định dạng chuẩn: - **#{id}. {skill_name}**: {notes}
                clean_name = filename.replace(".md", "")
                new_entry = f"- **#{assigned_id}. {clean_name}**: {notes}\n"
            else:
                new_entry = f"| {stars} | **{filename}** | `./{category}/{filename}` | {notes} |\n"
            
            if not map_path.exists():
                header = f"# 🛡️ JKAI Zenith: HỒ SƠ TRÍ TUỆ {category.upper()} (MAP_{category.upper()})\n\n"
                header += "Danh mục tri thức đã được đồng hóa và xếp hạng Elite.\n\n---\n\n"
                if category != "skills":
                    header += "| Xếp hạng | Tên | Đường dẫn | Ghi chú Tính năng |\n|:---:|:---|:---|:---|\n"
                content = header
            
            content += new_entry
            map_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error(f"❌ [MAP-UPDATE-ERR] {e}")

    def detect_category(self, item: Path, ai_suggestion: str = None) -> str:
        """Phân loại tài liệu bằng trí tuệ nhân tạo hoặc hậu kiểm."""
        if ai_suggestion and ai_suggestion in self.dest_map:
            return ai_suggestion
            
        name = item.name.lower()
        if "skill" in name: return "skills"
        if "rule" in name or "sop" in name: return "rules"
        if "agent" in name: return "agents"
        if "tool" in name: return "tools"
        return "knowledge"

    async def ai_scrub(self, content: str, original_name: str, profile: str = "UNIFIED_ELITE") -> Dict:
        """Sử dụng UIE Engine để chuẩn hóa tri thức, tạo ghi chú và PHÂN LOẠI."""
        prompt = f"""
        BẠN LÀ CHUYÊN GIA ĐỒNG HÓA TRI THỨC JKAI ZENITH. 
        Nhiệm vụ: Viết lại tài liệu, PHÂN LOẠI và XẾP HẠNG nó vào đúng phân khu Elite.

        [DANH MỤC PHÂN KHU]
        - skills: Các hướng dẫn thao tác, kỹ thuật, công cụ.
        - rules: Các quy tắc, tiêu chuẩn, SOP, bảo mật, phần cứng.
        - agents: Định nghĩa về đặc vụ, linh hồn, phong cách.
        - tools: Định nghĩa API, cấu hình công cụ.
        - knowledge: Tri thức chung, quy trình, tài liệu tham khảo.
        - commands: Các hệ thống lệnh Terminal, siêu lệnh.
        - prompts: Các biểu mẫu, template JSON/Markdown.

        [QUY TẮC CỐT LÕI - GIAO THỨC CHUYỂN HÓA BẢN SẮC]
        1. BIẾN CỦA NGƯỜI THÀNH CỦA MÌNH: Thay thế toàn bộ các danh xưng thương hiệu ngoại lai như 'Claude', 'Cursor', 'Antigravity', 'OpenAI', 'Agentic' bằng 'Hệ thống JKAI Zenith', 'Bản sắc Master', hoặc 'Trí tuệ Tối thượng'.
        2. VĂN PHONG TỐI CAO: Sử dụng văn phong sắc lạnh, chuyên nghiệp, vĩ mô. Loại bỏ toàn bộ các đại từ nhân xưng gây nhiễu (Em/Boss/Tôi/Master/Dạ/Vâng). 
        3. ĐÚC LẠI LINH HỒN: Chuyển đổi toàn bộ các chỉ dẫn, logic sang phong thái Quyết đoán và Hiệu quả tinh hoa (Elite Efficiency) của Master LeeTrung.
        4. GHI CHÚ TÍNH NĂNG (Notes): 1 câu súc tích mô tả CÔNG DỤNG THỰC TẾ và GIÁ TRỊ CHIẾN LƯỢC đối với Tập đoàn.
        5. XẾP HẠNG (Rating): Từ 1-5 sao dựa trên độ quan trọng và độ chuẩn hóa của tài liệu.

        NỘI DUNG GỐC: {original_name}
        ---
        {content[:5000]}
        ---

        TRẢ VỀ JSON:
        {{
            "category": "skills/rules/agents/tools/knowledge/commands/prompts",
            "rating": 1-5,
            "filename": "ten_file_moi.md",
            "content": "Nội dung Markdown Elite",
            "notes": "Mô tả tính năng chi tiết để AI và Master hiểu"
        }}
        """
        
        response = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            json_mode=True
        )
        return response if isinstance(response, dict) else {"status": "error"}



    def security_scan(self, content: str, filename: str) -> Dict:
        """
        [ECC-INSPIRED] 🛡️ GIAO THỨC RÀ SOÁT BẢO MẬT (SECURITY SCAN)
        Tự động phát hiện dữ liệu nhạy cảm (API Keys, Secrets) thưa Master.
        """
        patterns = {
            "GENERIC_API_KEY": r"(?:key|api|token|secret|password|auth|pwd)[-_]?[a-zA-Z0-9]{16,64}",
            "AWS_ACCESS_KEY": r"AKIA[0-9A-Z]{16}",
            "AWS_SECRET_KEY": r"(?i)aws_secret_access_key.*\s*[:=]\s*[a-zA-Z0-9/+=]{40}",
            "GOOGLE_API_KEY": r"AIza[0-9A-Za-z-_]{35}",
            "GITHUB_TOKEN": r"gh[pous]_[a-zA-Z0-9]{36,255}",
            "STRIPE_KEY": r"sk_live_[0-9a-zA-Z]{24}",
            "SSH_PRIVATE_KEY": r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----",
            "ENV_PASSWORD": r"(?i)(password|secret|pwd|database_url)\s*[:=]\s*[^\s]+",
            "N8N_API_KEY": r"n8n-api-[a-zA-Z0-9]{32,}",
            "SLACK_TOKEN": r"xox[baprs]-[a-zA-Z0-9\-]{10,}",
            "DB_CONNECTION": r"(?:mongodb\+srv|postgres|mysql|redis)://[\w\-]+:[\w\-]+@"
        }
        
        findings = []
        for name, pattern in patterns.items():
            if re.search(pattern, content):
                findings.append(name)
        
        if findings:
            return {
                "is_dangerous": True,
                "severity": "CRITICAL" if "SSH_PRIVATE_KEY" in findings or "AWS_SECRET_KEY" in findings else "HIGH",
                "reason": f"Phát hiện dữ liệu nhạy cảm: {', '.join(findings)}"
            }
        
        return {"is_dangerous": False}

    def archive_done(self, item: Path):
        """Di chuyển file đã xử lý vào thư mục hoàn tất."""
        done_dir = self.base_dir / "archive" / "processed"
        done_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(item), str(done_dir / item.name))
        except: pass

# 🚀 Lazy singleton - chỉ khởi tạo khi được gọi, không crash khi import
try:
    _instance = JKAI_Assimilator()
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning(f"[SKILL-INIT-WARN] {_e}")
    _instance = None

if __name__ == "__main__":
    if _instance:
        results = asyncio.run(_instance.run_assimilation(limit=1000))


# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện

async def dong_bo_tri_thuc(**kwargs):
    """Giao thức Nhất thể hóa: Ánh xạ từ schema sang logic thực thi thưa Master."""
    return await _instance.run_assimilation(**kwargs)

async def run_assimilation(**kwargs):
    return await _instance.run_assimilation(**kwargs)

def pre_audit_cleanup(**kwargs):
    return _instance.pre_audit_cleanup(**kwargs)

async def run_general_offensive(**kwargs):
    return await _instance.run_general_offensive(**kwargs)

async def process_elite_group(**kwargs):
    return await _instance.process_elite_group(**kwargs)

async def neural_audit(**kwargs):
    return await _instance.neural_audit(**kwargs)

async def quarantine_folder(**kwargs):
    return await _instance.quarantine_folder(**kwargs)

async def assimilate_elite_folder(**kwargs):
    return await _instance.assimilate_elite_folder(**kwargs)

async def generate_elite_suite(**kwargs):
    return await _instance.generate_elite_suite(**kwargs)

def check_python_syntax(**kwargs):
    return _instance.check_python_syntax(**kwargs)

def sanitize_to_unsigned(**kwargs):
    return _instance.sanitize_to_unsigned(**kwargs)

def update_knowledge_map(**kwargs):
    return _instance.update_knowledge_map(**kwargs)

async def generate_offensive_report(**kwargs):
    return await _instance.generate_offensive_report(**kwargs)

async def process_item(**kwargs):
    return await _instance.process_item(**kwargs)

def update_master_index(**kwargs):
    return _instance.update_master_index(**kwargs)

def detect_category(**kwargs):
    return _instance.detect_category(**kwargs)

async def ai_scrub(**kwargs):
    return await _instance.ai_scrub(**kwargs)

def sanitize_filename(**kwargs):
    return _instance.sanitize_filename(**kwargs)

def archive_done(**kwargs):
    return _instance.archive_done(**kwargs)
