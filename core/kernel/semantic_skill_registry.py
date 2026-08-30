# -*- coding: utf-8 -*-
"""
🧠 SEMANTIC SKILL REGISTRY (CANONICAL GROUND TRUTH)
Kho đăng ký năng lực kỹ năng định danh ngữ nghĩa chuẩn v35.0 (MCP & SOTA AI Agents).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from core.kernel.skill_manifest_schema import SemanticSkillManifest, SkillDomain

logger = logging.getLogger("JKAI.SemanticSkillRegistry")

# ==============================================================================
# BỘ MANIFEST KỸ NĂNG CỐT LÕI (CORE CANONICAL MANIFESTS)
# ==============================================================================

CORE_MANIFESTS: List[SemanticSkillManifest] = [
    SemanticSkillManifest(
        skill_id="SEARCH_WEB_GLOBAL",
        display_name="Tìm kiếm Web Toàn Cầu & Dữ liệu Realtime",
        domain=SkillDomain.WEB_RESEARCH,
        description="Tra cứu dữ liệu thời gian thực từ Internet qua công cụ tìm kiếm toàn cầu, thu thập tin tức, dữ liệu giá thị trường mới nhất.",
        when_to_use=[
            "Khi người dùng hỏi về sự kiện hiện tại, tin tức nóng, tỷ giá, giá vàng, cổ phiếu hôm nay hoặc tuần này.",
            "Khi cần số liệu thống kê, báo cáo cập nhật mới nhất mà tri thức tĩnh của mô hình không có.",
            "Khi cần kiểm chứng một sự kiện hay thông tin mới diễn ra trên mạng."
        ],
        when_not_to_use=[
            "Khi câu hỏi là kiến thức lý thuyết chung (Toán học, Lập trình căn bản, Ngữ pháp, Lịch sử cổ đại).",
            "Khi người dùng yêu cầu đọc hoặc phân tích nội dung tệp tin cục bộ trong hệ thống.",
            "Khi người dùng chỉ chào hỏi hoặc tương tác hội thoại xã giao thông thường."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa tìm kiếm ngắn gọn, súc tích và chính xác (VD: 'giá vàng SJC hôm nay 15/08')"
                }
            },
            "required": ["query"]
        },
        examples=[
            {"query": "giá vàng SJC hôm nay"},
            {"query": "tỷ giá USD VND Vietcombank mới nhất"}
        ],
        aliases=["OMNI_SEARCH_ENGINE", "skill_super_search", "web_search", "google_search"],
        tags=["web", "search", "realtime", "news", "finance_lookup"]
    ),
    SemanticSkillManifest(
        skill_id="SKILL_DATA_48_GRAPH",
        display_name="Phân tích Mạng lưới & Đồ thị Quan hệ",
        domain=SkillDomain.DATA_SCIENCE,
        description="Phân tích cấu trúc đồ thị, mô hình hóa các mối quan hệ liên đới phức tạp, chuỗi tác động đa chiều giữa các thực thể.",
        when_to_use=[
            "Khi cần phân tích mạng lưới quan hệ giữa các yếu tố (VD: Mối tương quan giữa USD, Lãi suất FED, Địa chính trị và Giá vàng).",
            "Khi cần tính toán đường đi, độ ảnh hưởng trọng yếu (Centrality) hoặc phân cụm thực thể (Clustering).",
            "Khi bài toán yêu cầu xây dựng bản đồ liên đới nguyên nhân - kết quả."
        ],
        when_not_to_use=[
            "Khi câu hỏi chỉ đơn giản là tra cứu một số liệu đơn lẻ.",
            "Khi chỉ cần tính toán số học hoặc đọc văn bản thuần túy."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách các thực thể / nút cần phân tích (VD: ['Vàng', 'USD', 'FED', 'Địa chính trị'])"
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "relation": {"type": "string"}
                        },
                        "required": ["source", "target", "relation"]
                    },
                    "description": "Các cạnh liên kết quan hệ giữa các thực thể"
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["centrality", "influence_propagation", "clustering", "full_network"],
                    "description": "Loại phân tích đồ thị cần thi hành"
                }
            },
            "required": ["nodes", "analysis_type"]
        },
        examples=[
            {
                "nodes": ["Vang", "USD", "FED", "Dia_chinh_tri"],
                "analysis_type": "influence_propagation"
            }
        ],
        aliases=["GRAPH_NETWORK_ANALYST", "skill_graph_analysis"],
        tags=["graph", "network", "causality", "influence", "correlation"]
    ),
    SemanticSkillManifest(
        skill_id="VIEW_FILE",
        display_name="Đọc & Kiểm Tra Nội Dung Tệp Tin",
        domain=SkillDomain.CODE_ENGINEERING,
        description="Đọc trực tiếp nội dung các tệp tin trong hệ thống workspace hoặc mã nguồn cục bộ.",
        when_to_use=[
            "Khi cần kiểm tra nội dung mã nguồn, file cấu hình, log, hoặc tài liệu có đường dẫn cụ thể.",
            "Khi cần định vị một đoạn mã trước khi chỉnh sửa."
        ],
        when_not_to_use=[
            "Khi tìm kiếm dữ liệu trên Internet (phải dùng SEARCH_WEB_GLOBAL).",
            "Khi chỉ cần xem danh sách thư mục (phải dùng LIST_DIR)."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "AbsolutePath": {
                    "type": "string",
                    "description": "Đường dẫn tuyệt đối đến tệp tin cần đọc"
                },
                "StartLine": {
                    "type": "integer",
                    "description": "Dòng bắt đầu cần đọc (1-indexed, tùy chọn)"
                },
                "EndLine": {
                    "type": "integer",
                    "description": "Dòng kết thúc cần đọc (1-indexed, tùy chọn)"
                }
            },
            "required": ["AbsolutePath"]
        },
        aliases=["read_file", "view_file", "cat_file"],
        tags=["file", "read", "inspect", "code"]
    ),
    SemanticSkillManifest(
        skill_id="RUN_COMMAND",
        display_name="Thực Thi Lệnh Hệ Thống Terminal",
        domain=SkillDomain.DEVOPS_SYS,
        description="Chạy các lệnh terminal (PowerShell / Bash / Docker / Pytest) trong môi trường thực thi an toàn.",
        when_to_use=[
            "Khi cần chạy kiểm thử (pytest, unit tests), kiểm tra container (docker), cài đặt thư viện hoặc build dự án.",
            "Khi cần kiểm tra trạng thái tiến trình hệ điều hành."
        ],
        when_not_to_use=[
            "Tuyệt đối KHÔNG dùng để thay thế việc đọc/ghi file văn bản (hãy dùng VIEW_FILE / WRITE_TO_FILE).",
            "Tuyệt đối KHÔNG chạy các lệnh phá hoại không thể khôi phục."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "CommandLine": {
                    "type": "string",
                    "description": "Chuỗi lệnh shell cần thực thi"
                },
                "Cwd": {
                    "type": "string",
                    "description": "Thư mục làm việc hiện tại khi chạy lệnh"
                }
            },
            "required": ["CommandLine", "Cwd"]
        },
        aliases=["run_command", "exec_cmd", "bash", "powershell"],
        tags=["terminal", "command", "bash", "devops", "test"]
    ),
    SemanticSkillManifest(
        skill_id="HOI_DONG_CHUYEN_GIA",
        display_name="Hội Đồng Chuyên Gia Tranh Luận Đa Chiều",
        domain=SkillDomain.GENERAL,
        description="Kích hoạt hội đồng đa nhân cách/chuyên gia (Kiến trúc sư, Nhà tài chính, Chuyên gia Bảo mật) để tranh luận và phản biện chuyên sâu cho các bài toán chiến lược.",
        when_to_use=[
            "Khi gặp bài toán phức tạp cần góc nhìn đa chiều, ra quyết định lớn, đánh đổi kiến trúc.",
            "Khi Master yêu cầu tham vấn ý kiến hội đồng hoặc tranh biện sâu."
        ],
        when_not_to_use=[
            "Khi câu hỏi là các thao tác công cụ đơn giản (tìm kiếm tin tức, đọc file).",
            "Khi câu hỏi yêu cầu câu trả lời trực tiếp, ngắn gọn."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Chủ đề hoặc vấn đề chiến lược cần Hội đồng tranh luận"
                }
            },
            "required": ["topic"]
        },
        aliases=["COUNCIL_OF_MINDS_DEBATE", "expert_council", "brainstorm_council"],
        tags=["debate", "council", "strategy", "architecture", "multi_agent"]
    ),
    SemanticSkillManifest(
        skill_id="OFFICE_SUITE_MASTER",
        display_name="Tạo & Chỉnh Sửa File Excel / Word / PDF Chuyên Nghiệp",
        domain=SkillDomain.OFFICE_DOCS,
        description="Tạo tệp tin Excel (.xlsx kèm biểu đồ trực quan), Word (.docx định dạng chuẩn công vụ) và PDF thực tế trên đĩa hệ thống.",
        when_to_use=[
            "Khi người dùng yêu cầu tạo file Excel, tạo bảng tính, xuất file xlsx, vẽ biểu đồ theo dõi tiến độ, bảng lương, báo cáo tài chính.",
            "Khi người dùng yêu cầu tạo file Word, soạn thảo văn bản docx, đơn từ, hợp đồng, biên bản.",
            "Khi cần xuất báo cáo văn phòng định dạng Office thực tế để tải về."
        ],
        when_not_to_use=[
            "Khi chỉ cần trả lời thông tin ngắn dạng text mà không yêu cầu tạo tệp tin tải về.",
            "Khi chỉ cần đọc nội dung file đã có sẵn (phải dùng VIEW_FILE)."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_excel", "write_word", "create_pdf", "write_excel", "create_docx"],
                    "description": "Loại tác vụ tạo file: 'create_excel' (cho file .xlsx kèm biểu đồ) hoặc 'write_word' (cho file .docx)"
                },
                "filename": {
                    "type": "string",
                    "description": "Tên file xuất ra không dấu, cách nhau bởi dấu gạch dưới (VD: 'Bao_Cao_Tien_Do_Phong_Ban.xlsx')"
                },
                "title": {
                    "type": "string",
                    "description": "Tiêu đề của bảng tính hoặc văn bản"
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách tiêu đề các cột trong bảng Excel (VD: ['STT', 'Họ và tên', 'Nhiệm vụ', 'Tiến độ (%)', 'Trạng thái'])"
                },
                "rows": {
                    "type": "array",
                    "items": {"type": "array"},
                    "description": "Dữ liệu các dòng tương ứng với các cột (VD: [[1, 'Nguyễn Văn A', 'Thiết kế UI', 100, 'Hoàn thành'], ...])"
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "pie", "line", "column"],
                    "description": "Loại biểu đồ trực quan hóa: 'bar', 'pie', hoặc 'line'"
                },
                "chart_title": {
                    "type": "string",
                    "description": "Tiêu đề biểu đồ trực quan"
                },
                "content": {
                    "type": "string",
                    "description": "Nội dung chi tiết văn bản (đối với tác vụ write_word)"
                }
            },
            "required": ["action", "filename", "title"]
        },
        examples=[
            {
                "action": "create_excel",
                "filename": "Bao_Cao_Tien_Do_10_Nhan_Vien.xlsx",
                "title": "BÁO CÁO TIẾN ĐỘ CÔNG VIỆC PHÒNG BAN",
                "columns": ["STT", "Họ và tên", "Công việc phụ trách", "Tiến độ (%)", "Trạng thái", "Ghi chú"],
                "rows": [
                    [1, "Nguyễn Văn An", "Phát triển API Backend", 90, "Đang xử lý", "Đúng hạn"],
                    [2, "Trần Thị Bích", "Thiết kế giao diện UI/UX", 100, "Hoàn thành", "Xuất sắc"]
                ],
                "chart_type": "bar",
                "chart_title": "Tỷ lệ Hoàn Thành Tiến Độ Theo Nhân Viên"
            }
        ],
        aliases=["create_excel", "tao_excel", "write_excel", "write_word", "create_word", "tao_word", "tao_file_excel", "skill_quanlyvanphong"],
        tags=["excel", "word", "office", "spreadsheet", "xlsx", "docx", "chart", "report", "báo cáo", "tiến độ", "tạo file"]
    ),
    SemanticSkillManifest(
        skill_id="WRITE_TO_FILE",
        display_name="Ghi & Tạo Tệp Tin Mã Nguồn / Văn Bản",
        domain=SkillDomain.CODE_ENGINEERING,
        description="Ghi hoặc tạo mới một tệp tin văn bản thuần (Python, JSON, Markdown, HTML, SQL, Text) vào workspace.",
        when_to_use=[
            "Khi cần tạo một file mã nguồn (.py, .js, .html, .css) hoặc file cấu hình (.json, .yaml, .md).",
            "Khi cần ghi đè nội dung file trong workspace."
        ],
        when_not_to_use=[
            "Khi tạo file Office phức tạp như Excel kèm biểu đồ hoặc Word định dạng chuẩn (phải dùng OFFICE_SUITE_MASTER)."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "TargetFile": {
                    "type": "string",
                    "description": "Đường dẫn tuyệt đối đến tệp tin cần ghi"
                },
                "CodeContent": {
                    "type": "string",
                    "description": "Nội dung toàn bộ của tệp tin cần ghi"
                },
                "Overwrite": {
                    "type": "boolean",
                    "description": "Cho phép ghi đè nếu tệp đã tồn tại (mặc định true)"
                }
            },
            "required": ["TargetFile", "CodeContent"]
        },
        aliases=["write_file", "write_to_file", "create_file", "save_file"],
        tags=["file", "write", "create", "save", "code", "script"]
    ),
    SemanticSkillManifest(
        skill_id="CODE_GREP",
        display_name="Truy Vết & Tìm Kiếm Chuỗi Ký Tự Trong Codebase",
        domain=SkillDomain.CODE_ENGINEERING,
        description="Tìm kiếm biểu thức chính quy (Regex) hoặc chuỗi văn bản chính xác trong toàn bộ cây thư mục mã nguồn.",
        when_to_use=[
            "Khi cần tìm vị trí định nghĩa hàm, class, biến hoặc chuỗi văn bản trong toàn bộ dự án.",
            "Khi cần rà soát các tệp bị ảnh hưởng trước khi thực hiện thay đổi mã nguồn."
        ],
        when_not_to_use=[
            "Khi tìm kiếm tin tức trên mạng Internet (phải dùng SEARCH_WEB_GLOBAL)."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Chuỗi tìm kiếm hoặc regex pattern"},
                "path": {"type": "string", "description": "Đường dẫn thư mục cần quét (mặc định workspace root)"}
            },
            "required": ["query"]
        },
        aliases=["grep", "code_grep", "search_code", "find_in_files"],
        tags=["grep", "search", "code", "find", "recon"]
    ),
    SemanticSkillManifest(
        skill_id="SYSTEM_TELEMETRY",
        display_name="Giám Sát & Trắc Lượng Phần Cứng Host",
        domain=SkillDomain.DEVOPS_SYS,
        description="Kiểm tra trạng thái sức khỏe máy chủ: CPU, RAM, GPU VRAM, nhiệt độ và các container đang chạy.",
        when_to_use=[
            "Khi Master hỏi về tình trạng máy chủ, dung lượng RAM, nhiệt độ CPU hoặc VRAM GPU.",
            "Khi hệ thống gặp tải chậm cần chẩn đoán tài nguyên vật lý."
        ],
        when_not_to_use=[
            "Khi hỏi về tin tức thời sự bên ngoài."
        ],
        parameters_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["all", "gpu", "cpu", "ram", "docker"], "description": "Mục tiêu cần đo lường"}
            },
            "required": []
        },
        aliases=["system_health", "kiemtrasuckhoe", "giam_sat_he_thong", "telemetry"],
        tags=["system", "health", "telemetry", "hardware", "vram", "ram"]
    )
]


class SemanticSkillRegistry:
    """Singleton quản lý toàn bộ kho Manifest năng lực của JKAI."""

    _instance: Optional[SemanticSkillRegistry] = None

    def __new__(cls) -> SemanticSkillRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._manifests = {}
            cls._instance._alias_map = {}
            cls._instance._load_core_manifests()
        return cls._instance

    def _load_core_manifests(self):
        for m in CORE_MANIFESTS:
            self.register_manifest(m)
        self._discover_physical_skills()
        logger.info("[SKILL-REGISTRY] Đã nạp thành công %d Semantic Skill Manifests (Bao gồm Auto-Discovered).", len(self._manifests))

    def _discover_physical_skills(self):
        """Tự động quét và nạp toàn bộ 138 skill vật lý có trên đĩa cứng theo chuẩn Z-SOS 5 tệp."""
        import os
        import glob
        import json
        # Tìm đường dẫn thư mục skills linh hoạt (Hỗ trợ cả Host Windows lẫn Docker Linux container /skills)
        candidates = [
            "/skills",
            os.getenv("SKILLS_DIR", ""),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligence", "skills")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "intelligence", "skills")),
            "/shared/skills"
        ]
        skills_root = next((c for c in candidates if c and os.path.exists(c) and os.path.isdir(c)), None)
        if not skills_root:
            logger.warning("[SKILL-AUTO-DISCOVERY] Không tìm thấy thư mục skills trên đĩa/container.")
            return

        manifest_files = glob.glob(os.path.join(skills_root, "**", "manifest.json"), recursive=True)
        
        domain_mapping = {
            "BUSINESS": SkillDomain.OFFICE_DOCS,
            "CODING": SkillDomain.CODE_ENGINEERING,
            "CORE": SkillDomain.GENERAL,
            "DATA_SCIENCE": SkillDomain.DATA_SCIENCE,
            "DEVOPS": SkillDomain.DEVOPS_SYS,
            "FINANCE": SkillDomain.FINANCE,
            "RESEARCH": SkillDomain.WEB_RESEARCH,
            "SECURITY": SkillDomain.SECURITY,
        }

        for mf in manifest_files:
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                skill_id = data.get("id") or os.path.basename(os.path.dirname(mf))
                if skill_id in self._manifests:
                    continue

                rel_dir = os.path.relpath(os.path.dirname(mf), skills_root).replace("\\", "/")
                parent_domain_str = rel_dir.split("/")[0].upper() if "/" in rel_dir else "GENERAL"
                domain = domain_mapping.get(parent_domain_str, SkillDomain.GENERAL)

                triggers = data.get("triggers", [])
                description = data.get("description", f"Thực thi kỹ năng {skill_id}")
                schema = data.get("schema", {}).get("input", {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": f"Tham số đầu vào cho {skill_id}"}},
                    "required": ["query"]
                })

                manifest = SemanticSkillManifest(
                    skill_id=skill_id,
                    display_name=data.get("name", skill_id.replace("_", " ").title()),
                    domain=domain,
                    description=description,
                    when_to_use=triggers[:5] if triggers else [f"Khi cần thực thi tác vụ {skill_id}"],
                    when_not_to_use=[],
                    parameters_schema=schema,
                    aliases=[skill_id.lower(), skill_id.replace("-", "_").lower()],
                    tags=[t.lower() for t in triggers[:8]]
                )
                self.register_manifest(manifest)
            except Exception as e:
                logger.debug("[SKILL-AUTO-DISCOVERY] Lỗi khi nạp manifest %s: %s", mf, e)

    def register_manifest(self, manifest: SemanticSkillManifest):
        self._manifests[manifest.skill_id] = manifest
        # Đăng ký các bí danh (aliases)
        for alias in manifest.aliases:
            self._alias_map[alias.lower()] = manifest.skill_id
        self._alias_map[manifest.skill_id.lower()] = manifest.skill_id

    def get_manifest(self, skill_id: str) -> Optional[SemanticSkillManifest]:
        canon_id = self._alias_map.get(skill_id.lower(), skill_id)
        return self._manifests.get(canon_id)

    def list_all_manifests(self) -> List[SemanticSkillManifest]:
        return list(self._manifests.values())

    def get_manifests_by_domain(self, domain: SkillDomain) -> List[SemanticSkillManifest]:
        return [m for m in self._manifests.values() if m.domain == domain]


semantic_skill_registry = SemanticSkillRegistry()
