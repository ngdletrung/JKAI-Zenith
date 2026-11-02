# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: core/kernel/tool_arbiter.py
- Role: Deterministic Tool Arbiter & Pentad Actuators Intent Router (SDS v28.26.0)
- Ownership: Master LeeTrung / JKAI-Zenith
- Status: Active | Elite Hardened

[ARCHITECTURAL PRINCIPLES]:
1. "Thân là Cốt lõi — Đầu là Linh kiện": Không để SLM 3B-4B tự đoán mò công cụ khi ranh giới
   nhiệm vụ có thể phân định xác định 100% bằng quy tắc toán học / regex / AST trong < 0.1ms.
2. BỘ NGŨ TAY CHÂN THỰC CHIẾN (The Pentad Sovereign Actuators Matrix):
   - M0 (FILE): Thao tác tệp workspace (đọc, sửa, tạo, vá AST, list dir, grep tìm kiếm codebase).
   - M1 (TERMINAL): Chạy lệnh hệ thống, test, git, docker qua Thang phê duyệt 4 nấc & Chained SHA-256 Ledger.
   - M2 (BROWSER): Mở URL trực tiếp, tương tác DOM trực quan, chụp ảnh màn hình (screenshot) qua ai-browser.
   - M3 (SEARCHWEB): Tra cứu tri thức internet khi CHƯA có URL đích danh (web_search / SEARCH_WEB_GLOBAL).
   - M4 (FAST_DOC): Đọc sâu văn bản/URL/llms.txt siêu tốc (<200ms, 0MB VRAM) không cần bật browser engine.
3. KHẢ NĂNG THÍCH ỨNG ĐA DẠNG & GIẢ TƯỞNG (Counterfactual & Edge-Case Robustness):
   - Tự động bóc tách các lớp vỏ giả định/giả tưởng ("giả sử...", "nếu có URL...", "kịch bản mô phỏng...").
   - Phân định rạch ròi Codebase Search (grep local) vs Internet Search (searchweb global).
   - Phân định Visual Browser (M2 - screenshot/DOM) vs Fast Doc Reader (M4 - trích xuất text 0MB VRAM).
   - Hỗ trợ luồng liên hoàn (HYBRID Multi-Stage Workflows: Browse->Save, File->Test, Terminal->Inspect).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


class ToolDomain(str, enum.Enum):
    FILE = "FILE"           # M0: File system & codebase search
    TERMINAL = "TERMINAL"   # M1: Shell commands, test, docker, git
    BROWSER = "BROWSER"     # M2: Visual web, screenshot, DOM interaction
    SEARCHWEB = "SEARCHWEB" # M3: Global web search (no URL)
    FAST_DOC = "FAST_DOC"   # M4: Headless URL reader, llms.txt, text extraction
    DESKTOP_OS = "DESKTOP_OS" # M5: Native Windows OS GUI Automation, UIA, smooth mouse
    HYBRID = "HYBRID"       # Multi-stage composite workflows
    GENERAL = "GENERAL"     # Pure reasoning / conceptual chat


@dataclass
class ArbiterVerdict:
    primary_domain: ToolDomain
    secondary_domains: List[ToolDomain] = field(default_factory=list)
    confidence: float = 1.0
    extracted_urls: List[str] = field(default_factory=list)
    extracted_files: List[str] = field(default_factory=list)
    extracted_commands: List[str] = field(default_factory=list)
    extracted_search_query: Optional[str] = None
    extracted_code_query: Optional[str] = None
    is_hypothetical: bool = False
    hypothetical_wrapper: Optional[str] = None
    core_cleaned_goal: str = ""
    is_visual_required: bool = False
    is_codebase_search: bool = False
    mandatory_tools: List[str] = field(default_factory=list)
    forbidden_tools: List[str] = field(default_factory=list)
    primary_target: Optional[str] = None
    reason: str = ""

    def is_browser(self) -> bool:
        """Hỗ trợ tương thích ngược: BROWSER hoặc FAST_DOC đều truy cập URL."""
        return self.primary_domain in (ToolDomain.BROWSER, ToolDomain.FAST_DOC)

    def is_pure_browser(self) -> bool:
        """Kiểm tra xem có bắt buộc dùng visual browser engine (Playwright Chromium) không."""
        return self.primary_domain == ToolDomain.BROWSER

    def is_fast_doc(self) -> bool:
        """Kiểm tra xem có ưu tiên Fast Doc reader (0MB VRAM) không."""
        return self.primary_domain == ToolDomain.FAST_DOC

    def is_desktop_os(self) -> bool:
        """Kiểm tra xem có phải tác vụ điều khiển toàn màn hình Desktop Windows M5 không."""
        return self.primary_domain == ToolDomain.DESKTOP_OS

    def is_search_web(self) -> bool:
        return self.primary_domain == ToolDomain.SEARCHWEB

    def is_file(self) -> bool:
        return self.primary_domain == ToolDomain.FILE

    def is_terminal(self) -> bool:
        return self.primary_domain == ToolDomain.TERMINAL

    def is_hybrid(self) -> bool:
        return self.primary_domain == ToolDomain.HYBRID

    def has_file(self) -> bool:
        return self.primary_domain == ToolDomain.FILE or ToolDomain.FILE in self.secondary_domains

    def has_terminal(self) -> bool:
        return self.primary_domain == ToolDomain.TERMINAL or ToolDomain.TERMINAL in self.secondary_domains

    def has_browser(self) -> bool:
        return self.primary_domain in (ToolDomain.BROWSER, ToolDomain.FAST_DOC) or any(
            d in self.secondary_domains for d in (ToolDomain.BROWSER, ToolDomain.FAST_DOC)
        )

    def has_search_web(self) -> bool:
        return self.primary_domain == ToolDomain.SEARCHWEB or ToolDomain.SEARCHWEB in self.secondary_domains


class DeterministicToolArbiter:
    """
    [DETERMINISTIC-TOOL-ARBITER]
    Trọng tài phân tuyến công cụ Bộ Ngũ xác định (Pentad Sovereign Actuators Matrix).
    Đảm bảo: Đúng công cụ, đúng việc, xử lý triệt để các tình huống cụ thể và giả tưởng.
    """

    # 1. Bóc tách lớp vỏ giả định/giả tưởng (Hypothetical & Counterfactual wrappers)
    HYPOTHETICAL_REGEX = re.compile(
        r"^(?:giả sử\s*(?:rằng|như|là)?|"
        r"nếu\s*(?:như)?\s*(?:tôi|chúng ta|hệ thống|bạn)?\s*(?:muốn|cần|có)?|"
        r"trong trường hợp\s*(?:mà|nếu)?|"
        r"hãy tưởng tượng\s*(?:rằng|bạn là)?|"
        r"kịch bản mô phỏng\s*[:\-]|\s*giả định\s*(?:rằng|là)?|"
        r"thử nghiệm\s*(?:xem|rằng)?|"
        r"ví dụ\s*(?:như|là)?|"
        r"đặt trường hợp\s*(?:là)?|"
        r"suppose\s*(?:that)?|"
        r"imagine\s*(?:that|you are)?|"
        r"hypothetically\s*[,:]?|"
        r"what if\s*|"
        r"in case\s*(?:that)?|"
        r"scenario\s*[:\-])\s*",
        re.IGNORECASE,
    )

    # 2. Nhận diện URL & Domain mọi biến thể (Scheme, bare domains, dev ports)
    URL_REGEX = re.compile(
        r"(https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}(?:\.[a-zA-Z0-9()]{1,6})?(?::\d+)?\b[-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
        re.IGNORECASE,
    )
    BARE_DOMAIN_REGEX = re.compile(
        r"\b((?:[a-zA-Z0-9-]+\.)+(?:vn|com|org|net|io|edu|gov|dev|ai|me|info|app|tech)(?:/[^\s'\"<>\)]*)?)\b",
        re.IGNORECASE,
    )
    LOCALHOST_REGEX = re.compile(
        r"\b((?:localhost|127\.0\.0\.1):\d+(?:/[^\s'\"<>\)]*)?)\b",
        re.IGNORECASE,
    )

    # 3. Phân định Trực quan (Visual M2) vs Đọc nhanh (FastDoc M4)
    VISUAL_KEYWORDS = {
        "chụp màn hình", "screenshot", "chụp ảnh", "giao diện", "trực quan",
        "thao tác trực quan", "click", "bấm", "nhấn", "điền form", "nhập liệu",
        "đăng nhập", "cuộn trang", "scroll", "interactive", "visual", "ui/ux",
        "dom", "view trực quan", "mở trình duyệt", "open browser"
    }
    FAST_DOC_KEYWORDS = {
        "đọc nội dung", "đọc bài viết", "tóm tắt", "trích xuất văn bản",
        "lấy text", "đọc tin tức", "llms.txt", "tải nội dung", "headless",
        "summary", "đọc nhanh", "đọc trang", "xem tin", "crawl"
    }

    # 4. Phân định Tìm kiếm Codebase (M0) vs Tìm kiếm Internet (M3)
    CODEBASE_SEARCH_REGEX = re.compile(
        r"\b(?:tìm|kiếm|search|grep)\s+(?:hàm|class|phương thức|biến|function|method|từ khóa|chuỗi|symbol|code)\s+['\"`]?([a-zA-Z0-9_\-\.]+)"
        r"|\b(?:grep|tìm kiếm)\s+(?:trong|tại|ở)\s+(?:codebase|repo|thư mục|folder|dự án|project)\b"
        r"|\b(?:tìm|liệt kê)\s+(?:các\s+)?(?:file|tệp)\s+trong\b",
        re.IGNORECASE,
    )

    # 5. File patterns & Keywords
    FILE_EXT_REGEX = re.compile(
        r"(?:^|\s|['\"`])([a-zA-Z0-9_\-\\/]+(?:\.[a-zA-Z0-9_\-\\/]+)*\.(?:py|md|json|yaml|yml|txt|html|css|js|ts|tsx|toml|sh|sql|ini|cfg))(?:$|\s|['\"`])",
        re.IGNORECASE,
    )
    FILE_PATH_REGEX = re.compile(
        r"(?:^|\s|['\"`])((?:core|services|intelligence|data|tests|tools|docs|brain|workspace)/[a-zA-Z0-9_\-/\.]+)(?:$|\s|['\"`])",
        re.IGNORECASE,
    )
    FILE_ACTION_KEYWORDS = {
        "đọc file", "xem file", "sửa file", "tạo file", "ghi file",
        "phẫu thuật file", "patch file", "view_file", "write_to_file",
        "replace_file_content", "kiểm tra file", "đọc mã nguồn", "soi code",
        "sửa mã", "viết code", "lưu vào file", "ghi vào tệp", "save to file"
    }

    # 6. Terminal patterns & Keywords
    TERMINAL_CMDS = {
        "pytest", "git status", "git diff", "git log", "git commit", "docker ps",
        "docker logs", "npm run", "npm test", "pip install", "python -m", "pwsh",
        "powershell", "curl", "systemctl", "cargo test", "cargo build", "poetry run"
    }
    TERMINAL_ACTION_REGEX = re.compile(
        r"\b(?:chạy lệnh|thực thi lệnh|gõ lệnh|run cmd|execute command|chạy test|kiểm thử)\s*[:'\"]?\s*([^'\"]+)"
        r"|\bchạy\s+(?:file\s+)?([a-zA-Z0-9_\-\/\.]+\.py)\b",
        re.IGNORECASE,
    )

    # 7. Search web keywords (tra cứu sự kiện, tri thức internet khi chưa có URL)
    SEARCH_KEYWORDS = {
        "tìm kiếm", "tra cứu", "search", "giá vàng", "thời tiết", "ai là",
        "tin tức mới nhất", "tìm hiểu", "nghiên cứu về", "top bài viết",
        "search web", "tìm trên mạng", "tra cứu thông tin"
    }

    # [Q-FIX-7] Các khối bối cảnh được hệ thống tiêm vào goal (không phải ý định gốc của Master).
    # Entity trong các khối này KHÔNG được phép định tuyến arbiter (tránh nhiễm độc kế hoạch).
    INJECTED_BLOCK_MARKERS = (
        "[BÀI HỌC KINH NGHIỆM TỪ QUÁ KHỨ]",
        "[REPLAN-FEEDBACK]",
        "[CONTEXT FROM KNOWLEDGE BASE]",
        "[SKILL DNA]",
        "<VERIFIED_EXPERIENCE_RECALL>",
        "<KNOWN_SYSTEM_GAPS_AND_DEFECTS>",
        "<PAST_FAILURE_CRITIC_AWARENESS>",
        "<TOOL_CATALOG>",
    )
    SYSTEM_OBSERVE_KEYWORDS = {
        "trạng thái hệ thống", "chẩn đoán hệ thống", "chẩn đoán trạng thái",
        "system status", "system health", "sức khỏe hệ thống", "tài nguyên hệ thống",
        "telemetry", "phần cứng của hệ thống", "phần cứng hệ thống",
        "vram", "ram đang sử dụng", "ram đang dùng", "model đang hoạt động",
        "mô hình ai đang hoạt động", "dịch vụ nào đang chạy", "trạng thái dịch vụ",
    }

    @classmethod
    def strip_injected_context(cls, goal: str) -> str:
        """Cắt bỏ mọi khối bối cảnh hệ thống tiêm vào đuôi goal, chỉ giữ mục tiêu gốc."""
        text = goal or ""
        cut_at = len(text)
        for marker in cls.INJECTED_BLOCK_MARKERS:
            idx = text.find(marker)
            if idx != -1:
                cut_at = min(cut_at, idx)
        return text[:cut_at].strip()

    @classmethod
    def is_self_observation_goal(cls, text_low: str) -> bool:
        return any(kw in text_low for kw in cls.SYSTEM_OBSERVE_KEYWORDS)

    @classmethod
    def arbitrate(cls, goal: str, context: Optional[Dict[str, Any]] = None) -> ArbiterVerdict:
        """
        Phân xử mục tiêu nhiệm vụ và trả về kết luận phân tuyến toán học xác định.
        Thực thi trong < 0.1ms với 0 LLM overhead.
        """
        raw_goal = cls.strip_injected_context(goal)
        if not raw_goal:
            return ArbiterVerdict(
                primary_domain=ToolDomain.GENERAL,
                confidence=0.5,
                core_cleaned_goal="",
                reason="Mục tiêu rỗng, bàn giao cho General pipeline."
            )

        # -------------------------------------------------------------
        # BƯỚC 0: BÓC TÁCH LỚP VỎ GIẢ TƯỞNG / GIẢ ĐỊNH (HYPOTHETICAL STRIPPER)
        # -------------------------------------------------------------
        is_hypothetical = False
        hypo_wrapper = None
        cleaned_goal = raw_goal

        hypo_match = cls.HYPOTHETICAL_REGEX.match(raw_goal)
        if hypo_match:
            is_hypothetical = True
            hypo_wrapper = hypo_match.group(0).strip()
            # Bóc tách lớp vỏ giả định để lấy hạt nhân thực sự của hành động
            stripped_candidate = raw_goal[hypo_match.end():].strip()
            if len(stripped_candidate) >= 5:
                cleaned_goal = stripped_candidate

        g_low = cleaned_goal.lower()

        # --- B2_SYSTEM_OBSERVE. MIỀN TỰ QUAN SÁT HỆ THỐNG (READ-ONLY TELEMETRY) ---
        # Đặt TRƯỚC mọi nhánh file/terminal để bối cảnh nhiễm (tên tệp trong bài học cũ)
        # không thể kéo mục tiêu chẩn đoán hệ thống sang VIEW_FILE sai hướng.
        if cls.is_self_observation_goal(g_low) and not cls.URL_REGEX.search(cleaned_goal):
            return ArbiterVerdict(
                primary_domain=ToolDomain.GENERAL,
                confidence=0.97,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                primary_target="JKAI system telemetry (read-only)",
                mandatory_tools=["get_system_status"],
                forbidden_tools=["VIEW_FILE", "WRITE_TO_FILE", "SYSTEM_CMD"],
                reason=f"{'[GIẢ ĐỊNH / MÔ PHỎNG]: ' if is_hypothetical else ''}Tác vụ tự quan sát trạng thái hệ thống (read-only). BẮT BUỘC dùng get_system_status để lấy số liệu thật, CẤM đọc tệp/suy diễn.",
            )

        # -------------------------------------------------------------
        # BƯỚC 1: TRÍCH XUẤT THỰC THỂ (URL, FILE, COMMAND, CODE SEARCH)
        # -------------------------------------------------------------
        urls: List[str] = cls.URL_REGEX.findall(cleaned_goal)
        # Bóc tách domain bare nếu chưa có scheme
        for m in cls.BARE_DOMAIN_REGEX.finditer(cleaned_goal):
            dom = m.group(1).rstrip("/.,;:")
            # Loại trừ nếu là tên file (ví dụ: something.py, app.json)
            if not any(dom.endswith("." + ext) for ext in ["py", "json", "md", "txt", "yaml", "yml", "sh"]):
                full_dom_url = f"https://{dom}"
                if full_dom_url not in urls and not any(dom in u for u in urls):
                    urls.append(full_dom_url)

        # Trích xuất localhost
        for m in cls.LOCALHOST_REGEX.finditer(cleaned_goal):
            lh = m.group(1).rstrip("/.,;:")
            full_lh_url = f"http://{lh}"
            if full_lh_url not in urls:
                urls.append(full_lh_url)

        # Làm sạch URLs khỏi dấu ngoặc và dấu câu kết câu (loại trừ dấu chấm/phẩy dính cuối câu)
        urls = [re.sub(r"[>\)'\",\.:;?!]+$", "", u).strip().rstrip(".,;:?!") for u in urls]
        urls = [u for u in urls if len(u) >= 4]

        # Trích xuất file
        files: List[str] = []
        for match in cls.FILE_EXT_REGEX.finditer(cleaned_goal):
            f_clean = match.group(1).strip(" '\"`")
            if f_clean not in files and not f_clean.startswith("http"):
                files.append(f_clean)
        for match in cls.FILE_PATH_REGEX.finditer(cleaned_goal):
            f_clean = match.group(1).strip(" '\"`")
            if f_clean not in files and not f_clean.startswith("http"):
                files.append(f_clean)

        # Trích xuất lệnh Terminal
        detected_cmds: List[str] = []
        term_match = cls.TERMINAL_ACTION_REGEX.search(cleaned_goal)
        if term_match:
            cmd_cand = term_match.group(1) or term_match.group(2)
            if cmd_cand:
                detected_cmds.append(cmd_cand.strip(" '\"`"))

        for cmd in cls.TERMINAL_CMDS:
            if re.search(rf"\b{re.escape(cmd)}\b", g_low):
                if cmd not in detected_cmds:
                    detected_cmds.append(cmd)

        # Kiểm tra tìm kiếm trong codebase
        code_search_match = cls.CODEBASE_SEARCH_REGEX.search(cleaned_goal)
        is_codebase_search = bool(code_search_match) or ("grep" in g_low) or (
            any(w in g_low for w in ["tìm trong code", "tìm trong repo", "tìm trong thư mục", "tìm file"])
        )
        # [RED TEAM FIX]: Loại trừ false positive nếu người dùng chỉ định tìm kiếm internet (trên google, online...)
        # trừ khi có từ khóa xác nhận phạm vi repo (trong codebase, trong repo, local...)
        has_internet_intent = any(w in g_low for w in ["trên google", "trên mạng", "trên internet", "online", "on the web", "search web", "tìm kiếm web"])
        has_explicit_repo = any(w in g_low for w in ["trong repo", "trong codebase", "trong thư mục", "ở repo", "ở codebase", "nội bộ", "local", "workspace"])
        if has_internet_intent and not has_explicit_repo:
            is_codebase_search = False

        extracted_code_query = code_search_match.group(1) if (code_search_match and code_search_match.lastindex and is_codebase_search) else None

        # -------------------------------------------------------------
        # BƯỚC 2: PHÂN TUYẾN TOÁN HỌC & ĐỘ ƯU TIÊN CHỦ QUYỀN
        # -------------------------------------------------------------
        hypo_prefix_note = f"[GIẢ ĐỊNH / MÔ PHỎNG]: '{hypo_wrapper}' -> " if is_hypothetical else ""

        # --- A. MIỀN CODEBASE SEARCH (M0) ---
        # "tìm hàm abc trong core" -> tuyệt đối là FILE (grep), CẤM đẩy ra SearchWeb!
        if is_codebase_search and not urls:
            primary_target = extracted_code_query or (files[0] if files else "codebase")
            return ArbiterVerdict(
                primary_domain=ToolDomain.FILE,
                secondary_domains=[],
                confidence=0.99,
                extracted_files=files,
                extracted_code_query=extracted_code_query,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_codebase_search=True,
                primary_target=primary_target,
                mandatory_tools=["grep_search", "view_file", "list_dir"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web", "OMNI_SEARCH_ENGINE", "BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Tìm kiếm nội bộ trong codebase/repo ('{primary_target}'). BẮT BUỘC dùng grep_search/view_file. CẤM SearchWeb.",
            )

        # --- B. MIỀN CÓ URL ĐÍCH DANH (M2 vs M4 vs HYBRID) ---
        if urls:
            primary_url = urls[0]
            is_visual = any(kw in g_low for kw in cls.VISUAL_KEYWORDS)
            has_save_file = any(kw in g_low for kw in ["lưu vào file", "ghi vào file", "lưu file", "save to file", "tạo file"]) or (
                len(files) > 0 and any(kw in g_low for kw in ["lưu", "ghi", "save", "write"])
            )

            # Trường hợp Hybrid: Đọc URL rồi lưu vào file
            if has_save_file:
                target_file = files[0] if files else "report.md"
                chosen_domain = ToolDomain.BROWSER if is_visual else ToolDomain.FAST_DOC
                return ArbiterVerdict(
                    primary_domain=ToolDomain.HYBRID,
                    secondary_domains=[chosen_domain, ToolDomain.FILE],
                    confidence=0.98,
                    extracted_urls=urls,
                    extracted_files=files or [target_file],
                    is_hypothetical=is_hypothetical,
                    hypothetical_wrapper=hypo_wrapper,
                    core_cleaned_goal=cleaned_goal,
                    is_visual_required=is_visual,
                    primary_target=f"{primary_url} -> {target_file}",
                    mandatory_tools=(
                        ["BROWSER_CONTROL", "WRITE_TO_FILE"] if is_visual else ["read_url_content", "WRITE_TO_FILE"]
                    ),
                    forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web"],
                    reason=f"{hypo_prefix_note}Quy trình liên hoàn (HYBRID): Tải nội dung '{primary_url}' sau đó ghi nhận vào file '{target_file}'.",
                )

            # Nếu yêu cầu trực quan rõ ràng -> M2 BROWSER (Playwright + Screenshot)
            if is_visual:
                return ArbiterVerdict(
                    primary_domain=ToolDomain.BROWSER,
                    secondary_domains=[ToolDomain.FAST_DOC],
                    confidence=1.0,
                    extracted_urls=urls,
                    is_hypothetical=is_hypothetical,
                    hypothetical_wrapper=hypo_wrapper,
                    core_cleaned_goal=cleaned_goal,
                    is_visual_required=True,
                    primary_target=primary_url,
                    mandatory_tools=["BROWSER_CONTROL", "browser_action", "browser_interact"],
                    forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web", "OMNI_SEARCH_ENGINE"],
                    reason=f"{hypo_prefix_note}Yêu cầu trực quan / screenshot / DOM interaction tại URL '{primary_url}'. BẮT BUỘC dùng BROWSER_CONTROL.",
                )

            # Nếu chỉ đọc bài viết / tóm tắt văn bản -> M4 FAST_DOC (0MB VRAM, <200ms)
            return ArbiterVerdict(
                primary_domain=ToolDomain.FAST_DOC,
                secondary_domains=[ToolDomain.BROWSER],
                confidence=0.98,
                extracted_urls=urls,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_visual_required=False,
                primary_target=primary_url,
                mandatory_tools=["read_url_content", "web_read", "FastWebReader", "BROWSER_CONTROL"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web", "OMNI_SEARCH_ENGINE"],
                reason=f"{hypo_prefix_note}Đọc sâu trích xuất văn bản siêu tốc từ URL đích danh '{primary_url}'. Ưu tiên Fast Doc Reader (0MB VRAM). CẤM SearchWeb.",
            )

        # --- B2_DESKTOP_OBSERVE. MIỀN QUAN SÁT DESKTOP HOST THỤ ĐỘNG (READ-ONLY) ---
        DESKTOP_OBSERVER_KEYWORDS = {
            "host_desktop_observer", "get_host_hardware_telemetry", "get_host_desktop_windows",
            "phần cứng của máy tính host", "phần cứng host", "danh sách cửa sổ", "cửa sổ desktop",
            "cửa sổ ứng dụng đang mở", "host satellite", "desktop windows"
        }
        has_observer = any(kw in g_low for kw in DESKTOP_OBSERVER_KEYWORDS)
        is_mutation_action = any(k in g_low for k in ["click", "nhấp chuột", "bấm chuột", "gõ phím", "nhập văn bản"])
        if has_observer and not is_mutation_action:
            return ArbiterVerdict(
                primary_domain=ToolDomain.DESKTOP_OS,
                secondary_domains=[],
                confidence=1.0,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_visual_required=False,
                primary_target="Host Satellite Read-Only Desktop Observer",
                mandatory_tools=["get_system_status"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web", "BROWSER_CONTROL", "SYSTEM_CMD"],
                reason=f"{hypo_prefix_note}Tác vụ Passive Read-Only quan sát phần cứng host. BẮT BUỘC dùng typed tool get_system_status.",
            )

        # --- B2_DESKTOP. MIỀN DESKTOP OS COMPUTER-USE (M5: Toàn màn hình Windows / ứng dụng desktop / chuột trực quan) ---
        DESKTOP_OS_KEYWORDS = {
            "desktop", "toàn màn hình windows", "toàn màn hình", "màn hình máy tính",
            "ứng dụng desktop", "cửa sổ windows", "notepad", "calculator", "calc.exe",
            "thao tác chuột desktop", "di chuột trên màn hình", "con trỏ chuột windows",
            "desktop computer use", "desktop agent", "os agent", "desktop ui"
        }
        has_desktop_os = any(kw in g_low for kw in DESKTOP_OS_KEYWORDS)
        if has_desktop_os and (any(kw in g_low for kw in cls.VISUAL_KEYWORDS) or any(k in g_low for k in ["chuột", "mouse", "click", "mở", "bấm", "nhấp", "di chuyển"])):
            target_app = "notepad.exe" if "notepad" in g_low else ("calc.exe" if "calc" in g_low else "Windows Desktop")
            return ArbiterVerdict(
                primary_domain=ToolDomain.DESKTOP_OS,
                secondary_domains=[],
                confidence=0.98,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_visual_required=True,
                primary_target=target_app,
                mandatory_tools=["desktop_observe", "desktop_act"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web", "BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Tác vụ điều khiển toàn màn hình Desktop Windows M5 ({target_app}). BẮT BUỘC dùng Desktop OS Actuator & Smooth Mouse Engine.",
            )

        # --- B2. MIỀN WEB-GUI / COMPUTER-USE (M2: Không cần URL đích danh nếu chỉ định rõ giao diện web / WebFig / click) ---
        WEB_GUI_KEYWORDS = {
            "webfig", "routeros", "mikrotik", "giao diện web", "trên giao diện",
            "click trực quan", "bước click", "thao tác giao diện", "điều khiển giao diện",
            "thao tác trên web", "điều khiển máy tính", "computer use", "webgui", "web gui"
        }
        has_web_gui = any(kw in g_low for kw in WEB_GUI_KEYWORDS)
        is_visual_action = any(kw in g_low for kw in cls.VISUAL_KEYWORDS) or any(
            kw in g_low for kw in ["click", "bấm", "chụp ảnh", "chụp màn hình", "nhấn"]
        )
        if (has_web_gui and is_visual_action) or ("webfig" in g_low):
            default_target = "http://127.0.0.1:8765" if "webfig" in g_low else "http://localhost:8000"
            return ArbiterVerdict(
                primary_domain=ToolDomain.BROWSER,
                secondary_domains=[],
                confidence=0.97,
                extracted_urls=[default_target],
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                is_visual_required=True,
                primary_target=default_target,
                mandatory_tools=["BROWSER_CONTROL", "browser_act", "visual_aci_gateway"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "search_web"],
                reason=f"{hypo_prefix_note}Tác vụ điều khiển giao diện trực quan / WebFig ({default_target}). BẮT BUỘC dùng Visual Browser M2 & Visual ACI Gateway.",
            )

        # --- C. MIỀN HYBRID (FILE + TERMINAL: Phẫu thuật code & Chạy kiểm thử) ---
        is_file_action = any(kw in g_low for kw in cls.FILE_ACTION_KEYWORDS) or bool(files)
        is_terminal = bool(detected_cmds) or any(
            kw in g_low for kw in ["chạy lệnh", "thực thi lệnh", "chạy test", "gõ lệnh", "terminal"]
        )

        if is_file_action and is_terminal:
            primary_file = files[0] if files else "workspace"
            primary_cmd = detected_cmds[0] if detected_cmds else "pytest"
            return ArbiterVerdict(
                primary_domain=ToolDomain.HYBRID,
                secondary_domains=[ToolDomain.FILE, ToolDomain.TERMINAL],
                confidence=0.96,
                extracted_files=files,
                extracted_commands=detected_cmds,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                primary_target=f"{primary_file} & {primary_cmd}",
                mandatory_tools=["VIEW_FILE", "replace_file_content", "WRITE_TO_FILE", "EXECUTE_COMMAND", "SYSTEM_CMD"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Nhiệm vụ kết hợp phẫu thuật tệp ('{primary_file}') và kiểm chứng dòng lệnh ('{primary_cmd}').",
            )

        # --- D. MIỀN FILE THUẦN TÚY (M0) ---
        if is_file_action and not is_terminal:
            primary_file = files[0] if files else None
            return ArbiterVerdict(
                primary_domain=ToolDomain.FILE,
                secondary_domains=[],
                confidence=0.98,
                extracted_files=files,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                primary_target=primary_file,
                mandatory_tools=["VIEW_FILE", "WRITE_TO_FILE", "replace_file_content", "smart_patch", "list_dir"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Thao tác tệp tin nội bộ workspace ({primary_file or 'tệp tin'}). BẮT BUỘC dùng công cụ File M0.",
            )

        # --- E. MIỀN TERMINAL THUẦN TÚY (M1) ---
        if is_terminal and not is_file_action:
            primary_cmd = detected_cmds[0] if detected_cmds else "pytest"
            return ArbiterVerdict(
                primary_domain=ToolDomain.TERMINAL,
                secondary_domains=[],
                confidence=0.95,
                extracted_commands=detected_cmds,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                primary_target=primary_cmd,
                mandatory_tools=["EXECUTE_COMMAND", "SYSTEM_CMD", "run_command"],
                forbidden_tools=["SEARCH_WEB_GLOBAL", "BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Thực thi dòng lệnh hệ thống có kiểm toán ({primary_cmd}) qua Thang phê duyệt 4 nấc M1.",
            )

        # --- F. MIỀN SEARCHWEB (M3: Tra cứu Internet khi CHƯA có URL) ---
        is_search = any(kw in g_low for kw in cls.SEARCH_KEYWORDS) or any(
            g_low.startswith(p) for p in ["tìm ", "tra cứu ", "search ", "hãy tìm "]
        )
        if is_search:
            clean_query = cleaned_goal
            for prefix in ["hãy tìm kiếm", "hãy tìm", "tìm kiếm", "tra cứu", "search for", "search"]:
                if clean_query.lower().startswith(prefix):
                    clean_query = clean_query[len(prefix):].strip(": ")
                    break

            return ArbiterVerdict(
                primary_domain=ToolDomain.SEARCHWEB,
                secondary_domains=[ToolDomain.FAST_DOC],
                confidence=0.92,
                extracted_search_query=clean_query,
                is_hypothetical=is_hypothetical,
                hypothetical_wrapper=hypo_wrapper,
                core_cleaned_goal=cleaned_goal,
                primary_target=clean_query,
                mandatory_tools=["SEARCH_WEB_GLOBAL", "OMNI_SEARCH_ENGINE", "web_read"],
                forbidden_tools=["BROWSER_CONTROL"],
                reason=f"{hypo_prefix_note}Nhiệm vụ tra cứu thông tin trực tuyến chưa có URL đích danh: '{clean_query}'.",
            )

        # --- G. GENERAL (Phân định tự do hoặc trò chuyện) ---
        return ArbiterVerdict(
            primary_domain=ToolDomain.GENERAL,
            confidence=0.5,
            is_hypothetical=is_hypothetical,
            hypothetical_wrapper=hypo_wrapper,
            core_cleaned_goal=cleaned_goal,
            primary_target=None,
            mandatory_tools=[],
            forbidden_tools=[],
            reason=f"{hypo_prefix_note}Nhiệm vụ tổng quát, bàn giao cho Planner tự do đúc kết chiến lược.",
        )

    @classmethod
    def generate_planner_guidance(cls, verdict: ArbiterVerdict) -> str:
        """
        Sinh chỉ dẫn cứng (Hard Boundary Directives) nhúng vào Planner prompt,
        giúp mô hình 3B-4B không thể chọn sai công cụ, kể cả trong tình huống giả định.
        """
        hypo_warn = (
            "\n⚡ CHỈ THỊ NGỮ CẢNH GIẢ ĐỊNH: Mặc dù yêu cầu có yếu tố giả tưởng/giả định, "
            "bạn PHẢI sinh bước hành động thực thi thật với đúng công cụ được chỉ định bên dưới!\n"
            if verdict.is_hypothetical else ""
        )

        if verdict.mandatory_tools == ["get_system_status"]:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC DÙNG TOOL TỰ QUAN SÁT HỆ THỐNG:\n"
                f"- Mục tiêu: {verdict.primary_target}\n"
                f"- Bước đầu tiên PHẢI gọi tool 'get_system_status' (args: {{}}) để lấy số liệu runtime thật.\n"
                f"- TUYỆT ĐỐI CẤM đọc docker-compose.yml, tệp cấu hình hay suy diễn số liệu.\n"
                f"- Nếu số liệu không truy xuất được, báo rõ 'không có dữ liệu'; KHÔNG được bịa.\n"
                f"</arbiter_constraint>\n"
            )

        if verdict.primary_domain == ToolDomain.BROWSER:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC PHẢI DÙNG BROWSER TRỰC QUAN (M2):\n"
                f"- Mục tiêu yêu cầu trực quan/screenshot/DOM: {verdict.primary_target}\n"
                f"- Bạn BẮT BUỘC phải dùng tool 'BROWSER_CONTROL' (với action='load_page') để mở URL và chụp ảnh màn hình.\n"
                f"- TUYỆT ĐỐI CẤM sử dụng SEARCH_WEB_GLOBAL hay tìm kiếm gián tiếp khi đã có sẵn URL!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.FAST_DOC:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC PHẢI DÙNG BỘ ĐỌC NHANH SIÊU TỐC (M4):\n"
                f"- Mục tiêu đọc nội dung văn bản từ URL: {verdict.primary_target}\n"
                f"- Bạn BẮT BUỘC dùng 'read_url_content' hoặc 'web_read' (hoặc 'BROWSER_CONTROL' chế độ text).\n"
                f"- Tiết kiệm RAM/VRAM, cấm bật visual browser không cần thiết. TUYỆT ĐỐI CẤM SEARCH_WEB_GLOBAL!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.FILE:
            sub_rule = (
                f"- Yêu cầu dò tìm codebase: Dùng 'grep_search' để quét thư mục, cấm SearchWeb!"
                if verdict.is_codebase_search else
                f"- Thao tác tệp workspace: Dùng 'VIEW_FILE', 'WRITE_TO_FILE' hoặc 'replace_file_content'."
            )
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC PHẢI DÙNG CÔNG CỤ TỆP TIN (FILE M0):\n"
                f"- Mục tiêu: {verdict.primary_target or 'workspace codebase'}\n"
                f"{sub_rule}\n"
                f"- TUYỆT ĐỐI CẤM dùng SEARCH_WEB_GLOBAL hay BROWSER_CONTROL cho tệp local!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.TERMINAL:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC PHẢI DÙNG DÒNG LỆNH HỆ THỐNG (TERMINAL M1):\n"
                f"- Mục tiêu thực thi dòng lệnh: {verdict.primary_target}\n"
                f"- Bạn BẮT BUỘC dùng 'SYSTEM_CMD' hoặc 'EXECUTE_COMMAND'. Lệnh sẽ được Thang phê duyệt 4 nấc kiểm toán.\n"
                f"- TUYỆT ĐỐI CẤM gọi tool file để chạy lệnh!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.SEARCHWEB:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC PHẢI DÙNG TÌM KIẾM WEB (SEARCHWEB M3):\n"
                f"- Mục tiêu tra cứu thông tin chưa có URL: '{verdict.primary_target}'\n"
                f"- Bạn BẮT BUỘC dùng 'SEARCH_WEB_GLOBAL' với query ngắn gọn, sau đó đọc bài viết bằng 'web_read'.\n"
                f"- CẤM dùng BROWSER_CONTROL khi chưa biết URL cụ thể!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.DESKTOP_OS:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC SỬ DỤNG TOOL QUAN SÁT HỆ THỐNG HOST (READ-ONLY):\n"
                f"- Mục tiêu: Thu thập telemetry phần cứng và trạng thái máy Host Master.\n"
                f"- Bạn BẮT BUỘC dùng tool 'get_system_status' (args: {{}}) cho dữ liệu phần cứng.\n"
                f"- TUYỆT ĐỐI CẤM sử dụng SEARCH_WEB_GLOBAL, SYSTEM_CMD, hoặc BROWSER_CONTROL!\n"
                f"</arbiter_constraint>\n"
            )
        elif verdict.primary_domain == ToolDomain.HYBRID:
            return (
                f"\n<arbiter_constraint priority='HIGHEST'>{hypo_warn}\n"
                f"🚨 BẮT BUỘC THỰC HIỆN THEO QUY TRÌNH LIÊN HOÀN (HYBRID):\n"
                f"- Mục tiêu kết hợp: {verdict.primary_target}\n"
                f"- Thiết lập các bước theo thứ tự hợp lý (ví dụ: Tải web -> Ghi file, hoặc Ghi code -> Chạy test).\n"
                f"- Sử dụng chính xác các công cụ hợp lệ: {', '.join(verdict.mandatory_tools)}.\n"
                f"</arbiter_constraint>\n"
            )
        return ""

    @classmethod
    def generate_resilient_recovery_step(cls, verdict: ArbiterVerdict, goal: str) -> Any:
        """
        Tạo bước cứu hộ thông minh khi Planner trả về kế hoạch rỗng [EMPTY-PLAN-SHIELD].
        Thay thế hoàn toàn cơ chế vơ đũa cả nắm sang SEARCH_WEB_GLOBAL cũ.
        """
        try:
            from planner import PlanStep, HardwareTarget
        except ImportError:
            import sys
            from pathlib import Path
            brain_dir = Path(__file__).resolve().parents[2] / "services" / "ai-brain"
            if str(brain_dir) not in sys.path:
                sys.path.insert(0, str(brain_dir))
            from planner import PlanStep, HardwareTarget

        if verdict.mandatory_tools == ["get_system_status"]:
            return PlanStep(
                id="auto_system_status_01",
                tool="get_system_status",
                args={},
                description="Auto-recovery: Lấy telemetry hệ thống thật (read-only) từ Mission Control",
                assigned_agent="agent_executor_alpha.md",
                hardware_target=HardwareTarget.ALPHA,
                expert_mindset="Quan sát viên read-only: chỉ báo cáo số liệu runtime thật, không suy diễn.",
                verification="Có active model, GPU + tổng VRAM MB, % RAM, trạng thái 6 dịch vụ và measured_at."
            )
        if verdict.primary_domain == ToolDomain.BROWSER:
            target_url = verdict.primary_target or (verdict.extracted_urls[0] if verdict.extracted_urls else "https://vietnamnet.vn/")
            return PlanStep(
                id="auto_browser_01",
                tool="BROWSER_CONTROL",
                args={
                    "url": target_url,
                    "action": "load_page",
                    "take_screenshot": True,
                    "objective": f"Mở trực quan trang {target_url} và chụp màn hình."
                },
                description=f"Auto-recovery: Mở trực quan trang web {target_url} và chụp ảnh màn hình.",
                assigned_agent="agent_executor_beta.md",
                hardware_target=HardwareTarget.BETA,
                expert_mindset="Truy cập trực quan và chụp ảnh màn hình trang web qua Playwright Chromium.",
                verification=f"Trang {target_url} được mở và ảnh chụp màn hình được lưu lại."
            )
        elif verdict.primary_domain == ToolDomain.FAST_DOC:
            target_url = verdict.primary_target or (verdict.extracted_urls[0] if verdict.extracted_urls else "https://vietnamnet.vn/")
            return PlanStep(
                id="auto_fastdoc_01",
                tool="BROWSER_CONTROL",
                args={"url": target_url, "action": "load_page", "objective": f"Đọc sâu nội dung trang {target_url}"},
                description=f"Auto-recovery: Đọc nội dung bài viết từ {target_url}",
                assigned_agent="agent_executor_beta.md",
                hardware_target=HardwareTarget.BETA,
                expert_mindset="Trích xuất văn bản sạch từ URL siêu tốc 0MB VRAM.",
                verification=f"Nội dung toàn văn từ {target_url} được trích xuất thành công."
            )
        elif verdict.primary_domain == ToolDomain.FILE:
            if verdict.is_codebase_search and verdict.extracted_code_query:
                q = verdict.extracted_code_query
                return PlanStep(
                    id="auto_grep_01",
                    tool="grep_search",
                    args={"SearchPath": "core", "Query": q},
                    description=f"Auto-recovery: Dò tìm mã nguồn cho '{q}' trong codebase",
                    assigned_agent="agent_executor_alpha.md",
                    hardware_target=HardwareTarget.ALPHA,
                    expert_mindset="Tìm kiếm từ khóa trong codebase nội bộ bằng công cụ grep.",
                    verification="Nhận được kết quả các dòng mã khớp."
                )
            target_file = verdict.primary_target
            if not target_file or target_file == "codebase":
                target_file = "README.md"
            return PlanStep(
                id="auto_file_01",
                tool="VIEW_FILE",
                args={"file_path": target_file},
                description=f"Auto-recovery: Kiểm tra tệp tin {target_file}",
                assigned_agent="agent_executor_alpha.md",
                hardware_target=HardwareTarget.ALPHA,
                expert_mindset="Đọc chính xác nội dung tệp tin nguồn không suy diễn.",
                verification=f"Tệp {target_file} được đọc thành công."
            )
        elif verdict.primary_domain == ToolDomain.TERMINAL:
            target_cmd = verdict.primary_target or "pytest"
            return PlanStep(
                id="auto_term_01",
                tool="SYSTEM_CMD",
                args={"command": target_cmd},
                description=f"Auto-recovery: Thực thi lệnh có kiểm toán {target_cmd}",
                assigned_agent="agent_executor_alpha.md",
                hardware_target=HardwareTarget.ALPHA,
                expert_mindset="Thực thi lệnh shell có kiểm duyệt và lưu vết audit.",
                verification="Lệnh trả về mã thoát hợp lệ và log được ghi nhận."
            )
        elif verdict.primary_domain == ToolDomain.DESKTOP_OS:
            return PlanStep(
                id="auto_host_telemetry_01",
                tool="get_system_status",
                args={},
                description="Auto-recovery: Thu thập telemetry phần cứng Host (read-only)",
                assigned_agent="agent_executor_alpha.md",
                hardware_target=HardwareTarget.ALPHA,
                expert_mindset="Thu thập telemetry CPU, RAM, GPU, VRAM từ Mission Control.",
                verification="Nhận được phản hồi status == success kèm dữ liệu phần cứng và measured_at."
            )
        elif verdict.primary_domain == ToolDomain.HYBRID:
            # Ưu tiên bước đầu tiên theo domain thứ nhất
            first_domain = verdict.secondary_domains[0] if verdict.secondary_domains else ToolDomain.FILE
            if first_domain in (ToolDomain.BROWSER, ToolDomain.FAST_DOC):
                target_url = verdict.extracted_urls[0] if verdict.extracted_urls else "https://vietnamnet.vn/"
                return PlanStep(
                    id="auto_hybrid_01",
                    tool="BROWSER_CONTROL",
                    args={"url": target_url, "action": "load_page", "objective": f"Đọc trang {target_url}"},
                    description=f"Auto-recovery (Bước 1): Tải nội dung từ {target_url}",
                    assigned_agent="agent_executor_beta.md",
                    hardware_target=HardwareTarget.BETA,
                    expert_mindset="Thu thập dữ liệu web ban đầu cho quy trình liên hoàn.",
                    verification=f"Đọc thành công {target_url}."
                )
            else:
                target_file = verdict.extracted_files[0] if verdict.extracted_files else "README.md"
                return PlanStep(
                    id="auto_hybrid_01",
                    tool="VIEW_FILE",
                    args={"file_path": target_file},
                    description=f"Auto-recovery (Bước 1): Kiểm tra tệp tin {target_file}",
                    assigned_agent="agent_executor_alpha.md",
                    hardware_target=HardwareTarget.ALPHA,
                    expert_mindset="Khởi tạo thao tác tệp cho quy trình liên hoàn.",
                    verification=f"Tệp {target_file} sẵn sàng."
                )
        else:
            search_query = verdict.extracted_search_query or verdict.primary_target or goal
            return PlanStep(
                id="auto_search_01",
                tool="SEARCH_WEB_GLOBAL",
                args={"query": search_query},
                description=f"Auto-recovery: Tra cứu thông tin trực tuyến cho: {search_query[:80]}",
                assigned_agent="agent_executor_alpha.md",
                hardware_target=HardwareTarget.ALPHA,
                expert_mindset="Tìm kiếm nguồn tin đáng tin cậy và không suy đoán.",
                verification="Nhận được danh sách kết quả tìm kiếm."
            )


# Sovereign Singleton Instance
tool_arbiter = DeterministicToolArbiter()
