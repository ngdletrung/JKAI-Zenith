# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL INTENT ROUTER v4.0 (COGNITIVE EVOLUTION) ║
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
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple

from core.os.routing.semantic_fallback import semantic_fallback_engine
from core.os.routing.compound_parser import compound_intent_parser
from core.os.routing.active_learner import active_learning_engine

logger = logging.getLogger("JKAI.IntentRouter")


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
        """Tính toán số học tức thì bằng AST parser an toàn."""
        try:
            text_low = text.lower()
            _OFFICE_OR_EXPLANATION_KWS = [
                'tại sao', 'vì sao', 'giải mã', 'kiến trúc', 'hàm', 'script', 'lỗi', 'python',
                'nghỉ lễ', 'lễ', 'thông báo', 'soạn thảo', 'soạn', 'tạo file', 'tạo', 'word',
                'docx', 'excel', 'xlsx', 'pdf', 'hợp đồng', 'tờ trình', 'báo cáo', 'văn bản'
            ]
            if any(kw in text_low for kw in _OFFICE_OR_EXPLANATION_KWS):
                return None

            # Bỏ qua nếu có dạng ngày tháng ngày/tháng hoặc ngày/tháng/năm
            if re.search(r'(?:ngày\s+)?\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b', text_low):
                # Nếu không có từ khóa ép buộc tính toán ('tính', 'bằng mấy', 'calculate')
                if not any(k in text_low for k in ['tính', 'tinh', 'bằng mấy', 'bang may', 'bằng bao nhiêu', 'calculate', 'compute']):
                    return None

            # 1. Xử lý phần trăm tài chính: "15% của 200000"
            pct_of_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:của|of)\s*(\d+(?:\.\d+)?)', text_low)
            if pct_of_match:
                pct = float(pct_of_match.group(1)) / 100.0
                base = float(pct_of_match.group(2))
                res = base * pct
                res_fmt = int(res) if res.is_integer() else round(res, 4)
                return f"Kết quả `{pct_of_match.group(1)}% của {pct_of_match.group(2)}` là: **{res_fmt:,}**"

            # 2. Loại bỏ các tiền tố toán học tiếng Việt và tiếng Anh phổ biến (có dấu & không dấu)
            clean_text = text
            # Chuẩn hóa tiền tố mà không phụ thuộc vào \b tiếng Việt
            lead_patterns = [
                r'tính\s+toán', r'tinh\s+toan', r'tính\s+giúp\s+tôi', r'tinh\s+giup\s+toi',
                r'tính\s+giúp', r'tinh\s+giup', r'tính\s+hộ', r'tinh\s+ho', r'tính', r'tinh',
                r'bằng\s+mấy', r'bang\s+may', r'bằng\s+bao\s+nhiêu', r'bang\s+bao\s+nhieu',
                r'kết\s+quả\s+là', r'ket\s+qua\s+la', r'kết\s+quả', r'ket\s+qua',
                r'calculate', r'compute', r'eval'
            ]
            for lp in lead_patterns:
                clean_text = re.sub(rf'(?i){lp}\s*[:=]?', ' ', clean_text)

            # 2. Trích xuất toàn bộ cụm biểu thức số học
            cand_matches = re.findall(r'[\d\.\s\+\-\*\/\(\)\%\^]+', clean_text)
            valid_exprs = []
            for m in cand_matches:
                m_clean = m.strip()
                # Phải có ít nhất 1 chữ số và 1 toán tử
                if re.search(r'\d', m_clean) and re.search(r'[\+\-\*\/\%\^]', m_clean):
                    if re.match(r'^[0-9\s\+\-\*\/\.\(\)\%\^]+$', m_clean):
                        valid_exprs.append(m_clean)

            if not valid_exprs:
                return None

            expr = max(valid_exprs, key=len).strip()
            # Thay thế ^ thành ** cho Python AST
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
        decision = self._route_inner(goal, is_office_task=is_office_task, history=history)
        if goal and goal.strip():
            try:
                from core.os.routing.entity_extractor import IngressEntityExtractor
                extracted = IngressEntityExtractor.extract(goal.strip())
                decision.scope = extracted.scope
                decision.target_files = extracted.target_paths
                if extracted.is_multi_resource:
                    decision.is_compound = True
                    if "MULTI_RESOURCE" not in decision.tags:
                        decision.tags.append("MULTI_RESOURCE")
            except Exception:
                pass
        return decision

    def _route_inner(self, goal: str, is_office_task: bool = False, history: list = None) -> RouteDecision:
        if not goal or not goal.strip():
            return RouteDecision(
                mode=IntentMode.GENERAL,
                role="RECEPTIONIST",
                reason="Empty goal",
                tags=["CHAT"],
                max_turns=1
            )

        g_strip = goal.strip()
        g_low = g_strip.lower()
        action_type = self.detect_action_type(g_strip)

        # Lấy danh sách từ khóa
        social_kws = self.get_lexicon("social")
        office_kws = self.get_lexicon("office")
        coding_kws = self.get_lexicon("coding")
        realtime_kws = self.get_lexicon("realtime")
        internal_kws = self.get_lexicon("internal")
        reasoning_kws = self.get_lexicon("reasoning")

        # ── 1. COMPOUND INTENT PARSING: Quét từng mệnh đề nếu là câu phức ──
        is_compound = compound_intent_parser.is_compound_intent(g_strip)
        clauses = compound_intent_parser.split_clauses(g_strip)

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

        # ── PRIORITY 7: DEEP REASONING ──
        if "ANALYSIS" in tags:
            decision = RouteDecision(
                mode=IntentMode.REASONING,
                role="PLANNER",
                action_type=action_type,
                need_kb=True,
                need_web=False,
                need_tools=False,
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
        semantic_match = semantic_fallback_engine.classify_semantic(g_strip, threshold=0.25)
        if semantic_match:
            s_mode_str, s_score = semantic_match
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
                    is_compound=is_compound
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
            is_compound=is_compound
        )
        active_learning_engine.record_query(g_strip, "GENERAL", 0.75, tags or ["CHAT"])
        return decision


intent_router = CentralIntentRouter()
