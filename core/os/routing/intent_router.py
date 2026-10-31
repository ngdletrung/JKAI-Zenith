# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL INTENT ROUTER v5.0 (REV5 — HYBRID SEMANTIC) ║
║   Tích Hợp Semantic Fallback, Compound Parser & Active Learning  ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Nhận Thức Tự Tiến Hóa Toàn Diện. 🎯🧬🧠*
"""

import os
import re
import ast
import yaml
import operator
import logging
import math
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple

from core.os.routing.semantic_fallback import semantic_fallback_engine
from core.os.routing.compound_parser import compound_intent_parser
from core.os.routing.active_learner import active_learning_engine
try:
    from core.os.routing.entity_extractor import IngressEntityExtractor
except ImportError:
    IngressEntityExtractor = None

logger = logging.getLogger("JKAI.IntentRouter")

# F1 (Rev4): hàm toán học duy nhất được phép gọi trong evaluate_math.
_MATH_FUNC_WHITELIST = {"sqrt": math.sqrt}

# Pre-compiled high performance regexes for evaluate_math (<0.2ms execution)
_RE_LEAD_PATTERNS = re.compile(
    r'(?i)(?:tính\s+toán|tinh\s+toan|tính\s+giúp\s+tôi|tinh\s+giup\s+toi|tính\s+giúp\s+mình|tinh\s+giup\s+minh|'
    r'tính\s+giúp|tinh\s+giup|tính\s+hộ|tinh\s+ho|tính|tinh|bằng\s+mấy|bang\s+may|'
    r'bằng\s+bao\s+nhiêu|bang\s+bao\s+nhieu|kết\s+quả\s+là|ket\s+qua\s+la|kết\s+quả|ket\s+qua|calculate|compute|eval)\s*[:=]?'
)
_RE_VIET_OPS = re.compile(
    r'(?i)(\d+)\s*(?:(nhân|nhan|x|\*)|(chia cho|chia)|(cộng|cong)|(trừ|tru))\s*(\d+)'
)
_RE_SQRT_PREFIX = re.compile(r'(?i)(?:căn\s+bậc\s+hai|can\s+bac\s+hai|√)\s*(?:của|cua|of)?\s*')
_RE_SQRT_CALL = re.compile(r'(?i)\bsqrt\s*\(?\s*(\d+(?:\.\d+)?)\s*\)?')
_RE_DOT_THOUSANDS = re.compile(r'(\d)\.(\d{3})(?=[\.\s,đ]|$)')
_RE_PCT_OF = re.compile(r'(\d+(?:\.\d+)?)\s*%\s*(?:của|of)\s*(\d+(?:\.\d+)?)')
_RE_SALARY_PCT = re.compile(r'(\d+(?:[.,]\d+)?)\s*triệu.*trừ\s+(\d+(?:[.,]\d+)?)\s*%')
_RE_SPLIT_EVEN = re.compile(r'chia\s+(?:đều\s+)?(\d[\d,]*)\s*(?:đồng|vnd|k|triệu)?\s+cho\s+(\d+)\s*(?:người|phần|nhóm)?')

# F2 (Rev5): semantic fallback INTERNAL dưới ngưỡng này không được thắng (rơi xuống GENERAL).
# Rev5: hạ từ 0.30 -> 0.22 do corpus v1.0 prototype score thực tế thấp hơn.
_SEMANTIC_INTERNAL_MIN_SCORE = 0.22

_TEMPORAL_CUES = {
    'hôm nay', 'hom nay', 'chiều nay', 'chieu nay', 'sáng nay', 'sang nay',
    'tối qua', 'toi qua', 'bây giờ', 'bay gio', 'hiện tại', 'hien tai',
    'mới nhất', 'moi nhat', 'vừa xong', 'vua xong', 'ngày mai', 'ngay mai',
    'tuần này', 'tuan nay', 'tháng này', 'thang nay', 'năm nay', 'nam nay',
    'trận', 'tỉ số', 'ti so', 'đá với', 'da voi'
}
_STATIC_FACT_CUES = {
    'con sông', 'dài nhất thế giới', 'sông dài nhất', 'núi cao nhất', 'đỉnh núi',
    'chiến thắng điện biên phủ', 'tác giả của truyện kiều', 'sao lá cây'
}


class IntentMode(str, Enum):
    MATH = "MATH"
    META_INTROSPECTION = "META_INTROSPECTION"
    SOCIAL = "SOCIAL"
    OFFICE = "OFFICE"
    CODING = "CODING"
    REALTIME = "REALTIME"
    INTERNAL = "INTERNAL"
    REASONING = "REASONING"
    GENERAL = "GENERAL"


class ActionType(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"


@dataclass
class RouteDecision:
    mode: IntentMode
    role: str                       # RECEPTIONIST | CODE_EXECUTOR | PLANNER
    action_type: ActionType = ActionType.CREATE
    need_kb: bool = False
    need_web: bool = False
    need_tools: bool = False
    force_synthesis: bool = False
    math_result: Optional[str] = None
    confidence: float = 1.0
    reason: str = ""
    tags: List[str] = field(default_factory=list)
    max_turns: int = 5
    kb_top_k: int = 3
    is_compound: bool = False
    need_operational_context: bool = False   # Kích hoạt RecentOperationsStore
    require_verification: bool = False       # Kích hoạt PreFlightVerificationGate
    is_meta_introspection: bool = False      # Kích hoạt SelfInspectionMode
    scope: str = "QUERY_OR_GENERAL"          # P0.4: MULTI_RESOURCE | SINGLE_RESOURCE | QUERY_OR_GENERAL
    target_files: List[str] = field(default_factory=list)
    latency_ms: float = 0.0  # Routing latency (ms), measured in route()
    route_path: str = "RULE"  # Rev4: RULE | SEMANTIC | GENERAL — nhánh thực tế đã quyết định


class CentralIntentRouter:
    """
    🧠 Bộ Não Định Tuyến Ý Định Tự Tiến Hóa v4.1 (Cognitive Evolution)
    """

    def __init__(self):
        self.lexicons: Dict[str, List[str]] = {}
        self.reload_lexicons()

    def reload_lexicons(self) -> None:
        """Nạp động toàn bộ từ khóa từ thư mục lexicons/*.yaml ngoài."""
        lex_dir = os.path.join(os.path.dirname(__file__), "lexicons")
        if not os.path.exists(lex_dir):
            os.makedirs(lex_dir, exist_ok=True)

        categories = ["social", "office", "coding", "realtime", "internal", "reasoning", "meta"]
        for cat in categories:
            yaml_path = os.path.join(lex_dir, f"{cat}.yaml")
            if os.path.exists(yaml_path):
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        self.lexicons[cat] = [str(k).lower().strip() for k in data.get("keywords", []) if k]
                except Exception as e:
                    logger.warning(f"[INTENT-ROUTER] Lỗi đọc lexicon {cat}.yaml: {e}")
                    self.lexicons[cat] = []
            else:
                self.lexicons[cat] = []

        logger.info(f"🎯 [INTENT-ROUTER]: Loaded dynamic lexicons across {len(self.lexicons)} categories.")

    def get_lexicon(self, category: str) -> List[str]:
        return self.lexicons.get(category, [])

    @staticmethod
    def detect_action_type(text: str) -> ActionType:
        """Nhận diện loại hành động: CREATE, READ, UPDATE, DELETE, EXECUTE."""
        t_low = text.lower()
        if any(w in t_low for w in ["xóa", "hủy", "delete", "remove", "drop", "purge"]):
            return ActionType.DELETE
        if any(w in t_low for w in ["sửa", "cập nhật", "update", "chỉnh sửa", "bổ sung", "thay đổi", "edit", "patch"]):
            return ActionType.UPDATE
        if any(w in t_low for w in ["đọc", "xem", "tra cứu", "hiển thị", "show", "read", "view", "get", "check"]):
            return ActionType.READ
        if any(w in t_low for w in ["chạy", "thực thi", "run", "execute", "exec", "start", "khởi chạy"]):
            return ActionType.EXECUTE
        return ActionType.CREATE

    def _detect_operational_reference(self, text: str) -> bool:
        """Phát hiện câu hỏi tham chiếu đến hành động vừa xảy ra."""
        patterns = ["vừa rồi", "hồi nãy", "lúc trước", "vừa xong", "mới đây", "vừa làm", "lúc nãy", "trước đó", "ngay trước", "hôm qua"]
        return any(p in text.lower() for p in patterns)

    def _detect_verification_need(self, text: str) -> bool:
        """Phát hiện câu hỏi yêu cầu xác minh thực tế trước khi trả lời."""
        patterns = ["bao nhiêu", "số lượng", "có ... không", "tồn tại", "hiện tại", "trạng thái", "thực tế", "kiểm tra", "xác minh", "nguồn từ đâu"]
        return any(p in text.lower() for p in patterns)

    @staticmethod
    def evaluate_math(text: str) -> Optional[str]:
        """Tính toán số học tức thì bằng AST parser an toàn (<0.5ms)."""
        try:
            text_low = text.lower()
            _OFFICE_OR_EXPLANATION_KWS = (
                'tại sao', 'vì sao', 'giải mã', 'kiến trúc', 'hàm', 'script', 'lỗi', 'python',
                'nghỉ lễ', 'lễ', 'thông báo', 'soạn thảo', 'soạn', 'tạo file', 'tạo', 'word',
                'docx', 'excel', 'xlsx', 'pdf', 'hợp đồng', 'tờ trình', 'báo cáo', 'văn bản'
            )
            if any(kw in text_low for kw in _OFFICE_OR_EXPLANATION_KWS):
                return None

            # Fast path: Bỏ qua nếu hoàn toàn không chứa chữ số hoặc căn bậc hai
            if not any(c.isdigit() for c in text) and 'căn' not in text_low and 'can' not in text_low and 'sqrt' not in text_low and '√' not in text_low:
                return None

            # Bỏ qua nếu có dạng ngày tháng ngày/tháng hoặc ngày/tháng/năm
            if re.search(r'(?:ngày\s+)?\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b', text_low):
                if not any(k in text_low for k in ('tính', 'tinh', 'bằng mấy', 'bang may', 'bằng bao nhiêu', 'calculate', 'compute')):
                    return None

            # 1. Xử lý phần trăm tài chính: "15% của 200000"
            pct_of_match = _RE_PCT_OF.search(text_low)
            if pct_of_match:
                pct = float(pct_of_match.group(1)) / 100.0
                base = float(pct_of_match.group(2))
                res = base * pct
                res_fmt = int(res) if res.is_integer() else round(res, 4)
                return f"Kết quả `{pct_of_match.group(1)}% của {pct_of_match.group(2)}` là: **{res_fmt:,}**"

            # Rev5-A: Lương triệu trừ phần trăm: "Lương 18 triệu mà bị trừ 10,5% bảo hiểm..."
            salary_pct_match = _RE_SALARY_PCT.search(text_low)
            if salary_pct_match:
                salary_m = float(salary_pct_match.group(1).replace(',', '.')) * 1_000_000
                deduct_pct = float(salary_pct_match.group(2).replace(',', '.')) / 100.0
                result_m = salary_m * (1 - deduct_pct)
                result_m_int = int(result_m) if result_m == int(result_m) else round(result_m)
                return f"Kết quả: **{result_m_int:,}**"

            # Rev5-B: Chia đều: "chia 9.000.000 đồng cho 3 người"
            if 'chia' in text_low and ('người' in text_low or 'phần' in text_low or 'nhóm' in text_low):
                text_nodot = _RE_DOT_THOUSANDS.sub(lambda m: m.group(1) + m.group(2), text_low)
                text_nodot = _RE_DOT_THOUSANDS.sub(lambda m: m.group(1) + m.group(2), text_nodot)
                split_match = _RE_SPLIT_EVEN.search(text_nodot)
                if split_match:
                    total = float(split_match.group(1).replace(',', ''))
                    parts = float(split_match.group(2))
                    if parts > 0:
                        each = total / parts
                        each_int = int(each) if each == int(each) else round(each, 2)
                        return f"Mỗi người nhận: **{each_int:,}**"

            # 2. Chuẩn hóa toán tử tiếng Việt sang ký hiệu toán học
            def _replace_op(m):
                a, op_mul, op_div, op_add, op_sub, b = m.groups()
                sym = '*' if op_mul else ('/' if op_div else ('+' if op_add else '-'))
                return f"{a} {sym} {b}"
            
            clean_text = _RE_VIET_OPS.sub(_replace_op, text)
            clean_text = _RE_LEAD_PATTERNS.sub(' ', clean_text)
            clean_text = _RE_SQRT_PREFIX.sub(' sqrt ', clean_text)
            clean_text = _RE_SQRT_CALL.sub(r'sqrt(\g<1>)', clean_text)

            # 3. Trích xuất toàn bộ cụm biểu thức số học
            cand_matches = re.findall(r'(?:sqrt|[\d\.\s\+\-\*\/\(\)\%\^])+', clean_text)
            valid_exprs = []
            for m in cand_matches:
                m_clean = m.strip()
                if re.search(r'\d', m_clean) and (re.search(r'[\+\-\*\/\%\^]', m_clean) or 'sqrt' in m_clean):
                    if re.match(r'^(?:sqrt|[0-9\s\+\-\*\/\.\(\)\%\^])+$', m_clean):
                        valid_exprs.append(m_clean)

            if not valid_exprs:
                return None

            expr = max(valid_exprs, key=len).strip()
            py_expr = expr.replace('^', '**')
            node = ast.parse(py_expr, mode='eval')

            def _eval(n):
                if isinstance(n, ast.Expression):
                    return _eval(n.body)
                elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
                    return n.value
                elif isinstance(n, ast.BinOp):
                    left, right = _eval(n.left), _eval(n.right)
                    ops = {
                        ast.Add: operator.add, ast.Sub: operator.sub,
                        ast.Mult: operator.mul, ast.Div: operator.truediv,
                        ast.Mod: operator.mod, ast.Pow: operator.pow
                    }
                    if type(n.op) in ops:
                        if isinstance(n.op, ast.Div) and right == 0:
                            return None
                        return ops[type(n.op)](left, right)
                elif isinstance(n, ast.UnaryOp):
                    operand = _eval(n.operand)
                    if isinstance(n.op, ast.USub): return -operand
                    if isinstance(n.op, ast.UAdd): return operand
                elif isinstance(n, ast.Call):
                    if (isinstance(n.func, ast.Name) and n.func.id in _MATH_FUNC_WHITELIST
                            and len(n.args) == 1 and not n.keywords):
                        arg = _eval(n.args[0])
                        if isinstance(arg, (int, float)) and arg >= 0:
                            return _MATH_FUNC_WHITELIST[n.func.id](arg)
                        return None
                    raise ValueError("Call ngoài whitelist bị từ chối")
                elif isinstance(n, (ast.Name, ast.Attribute)):
                    raise ValueError("Name/Attribute ngoài whitelist bị từ chối")
                return None

            res = _eval(node)
            if res is not None:
                if isinstance(res, float) and res.is_integer():
                    res = int(res)
                return f"Kết quả phép tính `{expr}` là: **{res:,}**" if isinstance(res, (int, float)) else f"Kết quả: **{res}**"
        except Exception:
            pass
        return None

    def route(self, goal: str, is_office_task: bool = False, history: list = None) -> RouteDecision:
        """
        Quyết định lộ trình xử lý kết hợp Compound Intent Parsing & Semantic Fallback.
        P0.4: Tích hợp IngressEntityExtractor để khẳng định Scope (MULTI_RESOURCE / SINGLE_RESOURCE).
        """
        start_time = time.perf_counter()
        decision = self._route_inner(goal, is_office_task=is_office_task, history=history)
        if goal and goal.strip() and IngressEntityExtractor is not None:
            try:
                extracted = IngressEntityExtractor.extract(goal.strip())
                decision.scope = extracted.scope
                decision.target_files = extracted.target_paths
                if extracted.is_multi_resource:
                    decision.is_compound = True
                    if "MULTI_RESOURCE" not in decision.tags:
                        decision.tags.append("MULTI_RESOURCE")
            except Exception:
                pass
        decision.latency_ms = (time.perf_counter() - start_time) * 1000
        return decision

    def _route_inner(self, goal: str, is_office_task: bool = False, history: list = None) -> RouteDecision:
        if not goal or not goal.strip():
            return RouteDecision(
                mode=IntentMode.GENERAL,
                role="RECEPTIONIST",
                reason="Empty goal",
                tags=["CHAT"],
                max_turns=1,
                route_path="GENERAL"
            )

        g_strip = goal.strip()
        g_low = g_strip.lower()

        # ── 0. TYPO & ACCENT NORMALIZATION (Chuẩn hóa lỗi gõ nhanh tiếng Việt) ──
        _TYPO_MAP = {
            "điều khỉ": "điều khiển",
            "dieu khi": "điều khiển",
            "ai-browse": "ai-browser",
            "ai browse": "ai-browser",
            "aibrowse": "ai-browser",
            "clik": "click",
            "clcik": "click",
        }
        for wrong, right in _TYPO_MAP.items():
            if wrong in g_low:
                g_low = g_low.replace(wrong, right)
                g_strip = re.sub(re.escape(wrong), right, g_strip, flags=re.IGNORECASE)
        action_type = self.detect_action_type(g_strip)

        # Lấy danh sách từ khóa
        social_kws = self.get_lexicon("social")
        office_kws = self.get_lexicon("office")
        coding_kws = self.get_lexicon("coding")
        realtime_kws = self.get_lexicon("realtime")
        internal_kws = self.get_lexicon("internal")
        reasoning_kws = self.get_lexicon("reasoning")

        # ── 1. COMPOUND INTENT PARSING: Quét từng mệnh đề nếu là câu phức ──
        clauses = compound_intent_parser.split_clauses(g_strip)
        is_compound = len(clauses) > 1

        tags_set: Set[str] = set()
        for clause in clauses:
            c_low = clause.lower()
            if is_office_task or any(k in c_low for k in office_kws):
                tags_set.add("OFFICE")
            if any(k in c_low for k in coding_kws):
                tags_set.add("CODING")
            if any(k in c_low for k in reasoning_kws):
                tags_set.add("ANALYSIS")
            if any(k in c_low for k in realtime_kws):
                tags_set.add("LOOKUP")

        tags: List[str] = list(tags_set)

        # ── PRIORITY 0.5: CONTINUATION / NỐI TIẾP NHIỆM VỤ (<0.1ms) ──
        _CONTINUATION_CUES = {
            "tiếp tục", "tiếp", "tiep tuc", "tiep", "continue", "tiếp đi", "tiep di",
            "viết tiếp", "viet tiep", "nói tiếp", "noi tiep", "làm tiếp", "lam tiep",
            "chạy tiếp", "chay tiep", "trình bày tiếp", "trinh bay tiep", "tiếp tục nào",
            "tiếp tục đi", "nói tiếp đi", "làm tiếp đi", "go on", "proceed"
        }
        g_clean = g_low.strip(" .!?:;\n\t\"'")
        is_cont = g_clean in _CONTINUATION_CUES or any(
            g_clean.startswith(c) for c in ["tiếp tục", "tiếp đi", "nói tiếp", "viết tiếp", "làm tiếp", "chạy tiếp"]
        )
        if is_cont:
            decision = RouteDecision(
                mode=IntentMode.REASONING,
                role="PLANNER",
                action_type=ActionType.EXECUTE,
                need_kb=True,
                need_web=False,
                need_tools=True,
                confidence=0.99,
                reason=f"Phát hiện khẩu lệnh tiếp nối nhiệm vụ ('{g_strip}'). Kế thừa ngữ cảnh, cấm reset về hội thoại xã giao.",
                tags=["CONTINUATION", "ANALYSIS"],
                max_turns=5,
                kb_top_k=5,
                is_compound=False,
                route_path="RULE"
            )
            active_learning_engine.record_query(g_strip, "REASONING", 0.99, ["CONTINUATION", "ANALYSIS"])
            return decision

        # ── PRIORITY 1: MATH (<1ms) ──
        math_res = self.evaluate_math(g_strip)
        if math_res:
            decision = RouteDecision(
                mode=IntentMode.MATH,
                role="RECEPTIONIST",
                action_type=ActionType.EXECUTE,
                math_result=math_res,
                confidence=1.0,
                reason="Evaluated pure arithmetic expression successfully.",
                tags=["MATH"],
                max_turns=0,
                kb_top_k=0
            )
            active_learning_engine.record_query(g_strip, "MATH", 1.0, ["MATH"])
            return decision

        # ── PRIORITY 1.2: CÂU HỎI TRA CỨU TÍNH NĂNG & NĂNG LỰC HỆ THỐNG (<0.2ms) ──
        # Nhận diện: "bạn có tính năng...", "bạn có điều khiển được...", "hệ thống có thể..."
        # Cưỡng chế định tuyến FAST Receptionist, cấm kích hoạt DEEP / CODING pipeline gây ảo giác!
        _CAP_QUESTION_LEADS = [
            "bạn có tính năng", "ban co tinh nang", "có tính năng", "co tinh nang",
            "bạn có chức năng", "ban co chuc nang", "có chức năng", "co chuc nang",
            "bạn có điều khiển", "ban co dieu khien", "có điều khiển được", "co dieu khien duoc",
            "bạn có thể điều khiển", "ban co the dieu khien", "có thể điều khiển",
            "bạn có làm được", "ban co lam duoc", "có làm được không", "co lam duoc khong",
            "ai-browser", "browser_control"
        ]
        is_cap_query = any(cq in g_low for cq in _CAP_QUESTION_LEADS)
        is_interrogative = any(q in g_low for q in ["không", "khong", "được", "duoc", "ah", "ạ", "hả", "ha", "chăng", "?"]) or any(
            g_low.startswith(p) for p in ["bạn có ", "ban co ", "hệ thống có ", "he thong co "]
        )
        is_explicit_cmd = any(cmd in g_low for cmd in ["hãy mở", "hãy click", "hãy làm", "hãy chạy", "hãy tạo", "hãy sửa"])

        if is_cap_query and is_interrogative and not is_explicit_cmd:
            decision = RouteDecision(
                mode=IntentMode.META_INTROSPECTION,
                role="RECEPTIONIST",
                action_type=ActionType.READ,
                need_kb=True,
                need_web=False,
                need_tools=False,
                confidence=0.99,
                reason=f"Câu hỏi tra cứu năng lực/tính năng hệ thống ('{g_strip}'). Định tuyến FAST Receptionist, cấm DEEP pipeline.",
                tags=["INTERNAL", "META", "CAPABILITY"],
                max_turns=1,
                kb_top_k=5,
                is_compound=is_compound,
                route_path="RULE"
            )
            active_learning_engine.record_query(g_strip, "META_INTROSPECTION", 0.99, ["CAPABILITY"])
            return decision

        # ── PRIORITY 1.5: META INTROSPECTION (Self-Knowledge & System Status) ──
        meta_patterns = [
            "bao nhiêu skill", "kỹ năng gì", "skill gì", "danh sách skill",
            "nguồn từ đâu", "nguon tu dau", "sao bạn bảo", "sao ban bao",
            "bạn có bao nhiêu", "he thong co bao nhieu", "tại sao bạn nói",
            "còn skill nào", "những skill nào", "thiếu dữ liệu"
        ]
        if any(p in g_low for p in meta_patterns) or ("skill" in g_low and any(k in g_low for k in ["gì", "lam gi", "làm gì", "như thế nào", "ở đâu"])):
            decision = RouteDecision(
                mode=IntentMode.META_INTROSPECTION,
                role="RECEPTIONIST",
                action_type=ActionType.READ,
                need_kb=True,
                need_web=False,
                need_tools=False,
                confidence=0.99,
                reason="Meta-introspection: Querying internal system state, skills, or operational memory.",
                tags=["INTERNAL", "META"],
                max_turns=1,
                kb_top_k=5,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "META_INTROSPECTION", 0.99, ["META"])
            return decision

        # ── PRIORITY 2: SOCIAL / GREETING (<50ms) ──
        if any(p in g_low for p in social_kws):
            decision = RouteDecision(
                mode=IntentMode.SOCIAL,
                role="RECEPTIONIST",
                action_type=action_type,
                need_kb=False,
                need_web=False,
                need_tools=False,
                confidence=0.98,
                reason="Social query / greeting detected. Direct LLM reflex.",
                tags=["CHAT"],
                max_turns=0,
                kb_top_k=0,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "SOCIAL", 0.98, ["CHAT"])
            return decision

        # ── PRIORITY 3: OFFICE FILE CREATION / UPDATE ──
        if "OFFICE" in tags:
            decision = RouteDecision(
                mode=IntentMode.OFFICE,
                role="CODE_EXECUTOR",
                action_type=action_type,
                need_kb=False,
                need_web=False,
                need_tools=True,
                confidence=0.95,
                reason=f"Office document request ({action_type.value} Word/Excel/PDF).",
                tags=tags or ["OFFICE"],
                max_turns=1 if not is_compound else 2,
                kb_top_k=2,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "OFFICE", 0.95, tags)
            return decision

        # ── PRIORITY 4: CODING & SCRIPTING ──
        if "CODING" in tags:
            decision = RouteDecision(
                mode=IntentMode.CODING,
                role="CODE_EXECUTOR",
                action_type=action_type,
                need_kb=False,
                need_web=False,
                need_tools=True,
                confidence=0.92,
                reason="Software engineering, debugging, or scripting intent.",
                tags=tags or ["CODING"],
                max_turns=3,
                kb_top_k=3,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "CODING", 0.92, tags)
            return decision

        # ── PRIORITY 5: REALTIME INFORMATION ──
        if any(k in g_low for k in realtime_kws):
            decision = RouteDecision(
                mode=IntentMode.REALTIME,
                role="RECEPTIONIST",
                action_type=ActionType.READ,
                need_kb=False,
                need_web=True,
                need_tools=True,
                force_synthesis=True,
                confidence=0.90,
                reason="Real-time news, market prices, or current event query.",
                tags=tags or ["LOOKUP"],
                max_turns=3,
                kb_top_k=5,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "REALTIME", 0.90, tags)
            return decision

        # ── PRIORITY 6: INTERNAL DATA / MEMORY ──
        if any(k in g_low for k in internal_kws):
            decision = RouteDecision(
                mode=IntentMode.INTERNAL,
                role="RECEPTIONIST",
                action_type=ActionType.READ,
                need_kb=True,
                need_web=False,
                need_tools=True,
                confidence=0.88,
                reason="Internal workspace or long-term memory query.",
                tags=tags or ["LOOKUP"],
                max_turns=2,
                kb_top_k=5,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "INTERNAL", 0.88, tags)
            return decision

        # ── PRIORITY 7: DEEP REASONING (WITH HYBRID LOCAL-WEB 0đ GROUNDING) ──
        if "ANALYSIS" in tags:
            analysis_needs_web = (
                "LOOKUP" in tags
                or any(k in g_low for k in ["giá", "thị trường", "bao nhiêu tiền", "hôm nay", "mới nhất", "công thức", "mua ở đâu", "chi phí thực tế"])
            )
            decision = RouteDecision(
                mode=IntentMode.REASONING,
                role="PLANNER",
                action_type=action_type,
                need_kb=True,
                need_web=analysis_needs_web,
                need_tools=analysis_needs_web,
                confidence=0.85,
                reason="Strategic analysis, comparative study, or architectural reasoning.",
                tags=tags or ["ANALYSIS"],
                max_turns=5,
                kb_top_k=5,
                is_compound=is_compound
            )
            active_learning_engine.record_query(g_strip, "REASONING", 0.85, tags)
            return decision

        # ── PRIORITY 8: SEMANTIC FALLBACK CLASSIFIER (<1ms) ──
        # Nếu từ khóa không match, dùng Cosine TF-IDF với Semantic Prototypes
        # Rev5 Policy (Gate 2 Final):
        # 1. Tri thức bách khoa/địa lý tĩnh không bao giờ match REALTIME (Zero False-Positive).
        # 2. Câu hỏi thời sự/thời gian động hỗ trợ ngưỡng nhạy 0.15; câu thông thường ngưỡng 0.17.
        # 3. Guard chống false-positive REALTIME và INTERNAL (<0.22).
        is_static_fact = any(sf in g_low for sf in _STATIC_FACT_CUES)
        has_temporal = any(tc in g_low for tc in _TEMPORAL_CUES)

        semantic_match = None
        if not is_static_fact:
            eff_thresh = 0.15 if has_temporal else 0.17
            semantic_match = semantic_fallback_engine.classify_semantic(g_strip, threshold=eff_thresh)
            if semantic_match:
                s_mode_str, s_score = semantic_match
                if s_mode_str == "INTERNAL" and s_score < _SEMANTIC_INTERNAL_MIN_SCORE:
                    logger.info(f"[SEMANTIC-FALLBACK-REJECT]: INTERNAL {s_score:.2f} < {_SEMANTIC_INTERNAL_MIN_SCORE}")
                    semantic_match = None
                elif s_mode_str == "REALTIME" and not has_temporal and s_score < 0.22:
                    logger.info(f"[SEMANTIC-FALLBACK-REJECT]: REALTIME false-positive {s_score:.2f} < 0.22 without temporal cue")
                    semantic_match = None
        if semantic_match:
            try:
                s_mode = IntentMode[s_mode_str]
                role = "CODE_EXECUTOR" if s_mode in (IntentMode.OFFICE, IntentMode.CODING) else ("PLANNER" if s_mode == IntentMode.REASONING else "RECEPTIONIST")
                logger.info(f"🔍 [SEMANTIC-FALLBACK-HIT]: Matched {s_mode.value} with similarity {s_score:.2f}")
                decision = RouteDecision(
                    mode=s_mode,
                    role=role,
                    action_type=action_type,
                    confidence=min(0.85, s_score),
                    reason=f"Semantic fallback similarity match ({s_score:.2f}).",
                    tags=[s_mode.value],
                    max_turns=3,
                    is_compound=is_compound,
                    route_path="SEMANTIC"
                )
                active_learning_engine.record_query(g_strip, s_mode.value, s_score, [s_mode.value])
                return decision
            except Exception:
                pass

        # ── PRIORITY 9: GENERAL REFLEX ──
        decision = RouteDecision(
            mode=IntentMode.GENERAL,
            role="RECEPTIONIST",
            action_type=action_type,
            need_kb=True,
            need_web=False,
            need_tools=True,
            confidence=0.75,
            reason="General knowledge query or conversational task.",
            tags=tags or ["CHAT"],
            max_turns=2,
            kb_top_k=3,
            is_compound=is_compound,
            route_path="GENERAL"
        )
        active_learning_engine.record_query(g_strip, "GENERAL", 0.75, tags or ["CHAT"])
        return decision


intent_router = CentralIntentRouter()
