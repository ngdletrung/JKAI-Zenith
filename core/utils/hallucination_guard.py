# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/hallucination_guard.py
# - Role: Anti-Hallucination & Epistemic Discipline Engine
# - Ownership: Mr LeeTrung
# - Status: Active | Version: v1.1
# [WORKING PRINCIPLES]:
# 1. Classifies every query into a knowledge type before building prompts.
# 2. FACT_CRITICAL queries get a strict PromptLock - no parametric improvisation.
# 3. PARAMETRIC_SAFE queries allow model reasoning - locked to reasoning style.
# 4. EpistemicShield wraps all responses with source + confidence metadata.
# 5. Strictly zero emojis in code or system configuration lines.
# -----------------------------------------------------------------------------
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger("JKAI.HallucinationGuard")


# ---------------------------------------------------------------------------
# Query Type Classification
# ---------------------------------------------------------------------------

class QueryType(str, Enum):
    FACT_CRITICAL      = "FACT_CRITICAL"
    TEMPORAL_SENSITIVE = "TEMPORAL_SENSITIVE"
    PARAMETRIC_SAFE    = "PARAMETRIC_SAFE"
    AMBIGUOUS          = "AMBIGUOUS"


# ---------------------------------------------------------------------------
# Pattern Definitions (Unicode-safe, non-raw strings)
# ---------------------------------------------------------------------------

_FACT_CRITICAL_PATTERNS: List[re.Pattern] = [
    # So lieu cu the
    re.compile(
        "(bao nhiêu|how many|số lượng|tổng số|tổng cộng|con số|số liệu"
        "|population|dân số|dân số)",
        re.IGNORECASE,
    ),
    # Moc thoi gian cu the
    re.compile(
        "(n\u0103m \\d{4}|th\u00e1ng \\d+|ng\u00e0y \\d+/\\d+|v\u00e0o n\u0103m|t\u1eeb n\u0103m|k\u1ec3 t\u1eeb"
        "|in year \\d{4}|since \\d{4})",
        re.IGNORECASE,
    ),
    # Don vi hanh chinh Viet Nam
    re.compile(
        "(tỉnh|thành phố|huyện|xã|phường|quận"
        "|đơn vị hành chính|cấp tỉnh|cấp huyện|cấp xã"
        "|province|district|commune|municipality)",
        re.IGNORECASE,
    ),
    # Phap ly va quy dinh
    re.compile(
        "(luật|nghị định|thông tư|quyết định"
        "|điều lệ|quy định|pháp luật|văn bản"
        "|decree|regulation|ordinance|law no)",
        re.IGNORECASE,
    ),
    # Ten nguoi, to chuc cu the
    re.compile(
        "(ai là|người nào|tổ chức nào|cơ quan nào|bộ nào"
        "|minister|director|who is the|who leads|who founded)",
        re.IGNORECASE,
    ),
    # Xac minh su that
    re.compile(
        "(kiểm tra|xác minh|thông tin.*đúng|có đúng không"
        "|có phải|thật sự|fact.?check|verify|true or false|is it true|correct or not)",
        re.IGNORECASE,
    ),
    # Thong ke, dieu tra
    re.compile(
        "(thống kê|dân số|diện tích|GDP|tăng trưởng"
        "|tỷ lệ|phần trăm|%|statistic|census|area in km)",
        re.IGNORECASE,
    ),
    # Tu khoa lich su
    re.compile(
        "(sự kiện|lịch sử|khi nào|thời điểm nào"
        "|xảy ra|diễn ra|bắt đầu từ|historical event|when did|when was)",
        re.IGNORECASE,
    ),
]

_TEMPORAL_SENSITIVE_PATTERNS: List[re.Pattern] = [
    re.compile(
        "(hiện tại|hiện nay|hiện hành|mới nhất|cập nhật"
        "|gần đây|latest|current|up.?to.?date|recently|as of today)",
        re.IGNORECASE,
    ),
    re.compile(
        "(hôm nay|tuần này|tháng này|năm nay"
        "|today|this week|this month|this year|right now)",
        re.IGNORECASE,
    ),
    re.compile(
        "(giá cả|tỷ giá|giá vàng|giá đô|lãi suất"
        "|chứng khoán|cổ phiếu|stock price|exchange rate|interest rate|gold price)",
        re.IGNORECASE,
    ),
    re.compile(
        "(tin tức|thời sự|news|breaking|update|sự kiện mới|latest news)",
        re.IGNORECASE,
    ),
]

_PARAMETRIC_SAFE_PATTERNS: List[re.Pattern] = [
    re.compile(
        "(code|viết|hàm|function|class|algorithm|thuật toán"
        "|script|debug|lỗi syntax|import|library|implement|coding)",
        re.IGNORECASE,
    ),
    re.compile(
        "(tính|calculate|integral|derivative|equation|phương trình"
        "|ma trận|vector|xác suất|logic|compute|formula|proof)",
        re.IGNORECASE,
    ),
    re.compile(
        "(dịch|translate|ngữ pháp|grammar|phong cách"
        "|viết lại|paraphrase|tóm tắt|summarize|rewrite|rephrase)",
        re.IGNORECASE,
    ),
    re.compile(
        "(brainstorm|ý tưởng|idea|đề xuất|suggest"
        "|thiết kế|design|tối ưu|optimize|cải thiện|improve|propose)",
        re.IGNORECASE,
    ),
    re.compile(
        "(nguyên lý|principle|khái niệm cơ bản|how does.*work"
        "|hoạt động như thế nào|định nghĩa của"
        "|definition of|explain how|what does.*mean)",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# QueryClassifier
# ---------------------------------------------------------------------------

class QueryClassifier:
    def classify(self, query: str) -> QueryType:
        q = (query or "").strip()
        if not q:
            return QueryType.AMBIGUOUS

        fact_score = sum(1 for p in _FACT_CRITICAL_PATTERNS if p.search(q))
        if fact_score >= 1:
            logger.debug("[HallucinationGuard] FACT_CRITICAL (score=%d): %s", fact_score, q[:60])
            return QueryType.FACT_CRITICAL

        temporal_score = sum(1 for p in _TEMPORAL_SENSITIVE_PATTERNS if p.search(q))
        if temporal_score >= 1:
            logger.debug("[HallucinationGuard] TEMPORAL_SENSITIVE (score=%d): %s", temporal_score, q[:60])
            return QueryType.TEMPORAL_SENSITIVE

        param_score = sum(1 for p in _PARAMETRIC_SAFE_PATTERNS if p.search(q))
        if param_score >= 1:
            logger.debug("[HallucinationGuard] PARAMETRIC_SAFE (score=%d): %s", param_score, q[:60])
            return QueryType.PARAMETRIC_SAFE

        logger.debug("[HallucinationGuard] AMBIGUOUS: %s", q[:60])
        return QueryType.AMBIGUOUS

    def classify_batch(self, queries: List[str]) -> List[QueryType]:
        return [self.classify(q) for q in queries]


# ---------------------------------------------------------------------------
# PromptLock
# ---------------------------------------------------------------------------

class PromptLock:
    FACT_CRITICAL_LOCK = (
        "[JKAI FACT-LOCK MODE ACTIVATED]\n"
        "NHIEM VU: Tra loi dua TUYET DOI tren tai lieu duoc cung cap trong [TAI LIEU NOI BO].\n\n"
        "LUAT BAT BUOC:\n"
        "1. CHI duoc trich xuat va tom tat tu tai lieu da cho. KHONG duoc tu sang tao.\n"
        "2. NEU tai lieu KHONG co thong tin lien quan, phan hoi chinh xac:\n"
        "   [JKAI-UNVERIFIED]: Toi khong tim thay du lieu xac thuc ve van de nay trong tai lieu noi bo."
        " Vui long kiem tra lai voi nguon chinh thong.\n"
        "3. NEU thay mau thuan giua tai lieu: bao cao ro rang, neu het phien ban khac nhau.\n"
        "4. TUYET DOI KHONG dung kien thuc tu qua trinh huan luyen cho con so, ngay thang, ten to chuc.\n"
        "5. Cuoi tra loi ghi: [Nguon: RAG tai lieu noi bo]\n"
    )

    TEMPORAL_SENSITIVE_LOCK = (
        "[JKAI TEMPORAL-LOCK MODE ACTIVATED]\n"
        "LUU Y: Cau hoi nay yeu cau thong tin co the da thay doi theo thoi gian.\n\n"
        "LUAT BAT BUOC:\n"
        "1. Neu tai lieu co ngay cap nhat: neu ro ngay do.\n"
        "2. Neu tai lieu KHONG co hoac co the cu: them canh bao:\n"
        "   [CANH BAO-THOI-HAN]: Thong tin nay co the da thay doi. Vui long xac minh.\n"
        "3. KHONG dua ra con so cu the neu khong co tai lieu xac nhan trong vong 12 thang.\n"
        "4. Cuoi tra loi ghi: [Du lieu co the outdated - Nen xac minh them]\n"
    )

    PARAMETRIC_SAFE_MODE = (
        "[JKAI REASONING MODE]\n"
        "Day la tac vu tu duy/lap luan - ban duoc phep su dung kien thuc noi tai.\n\n"
        "NGUYEN TAC:\n"
        "1. Ghi ro khi dua ra gia dinh: [GIA DINH]: ...\n"
        "2. Neu tai lieu co lien quan: uu tien tai lieu do.\n"
        "3. Voi code: dam bao logic chinh xac, them comment.\n"
        "4. Coi trong chat luong hon toc do.\n"
    )

    AMBIGUOUS_LOCK = (
        "[JKAI CAUTION MODE]\n"
        "Kieu cau hoi chua ro rang. Ap dung nguyen tac an toan:\n\n"
        "LUAT BAT BUOC:\n"
        "1. Neu tra loi ve su kien, so lieu cu the: ket thuc bang [Can xac minh them]\n"
        "2. Neu tai lieu khong du: noi ro 'Tai lieu hien tai khong du de tra loi chinh xac.'\n"
        "3. KHONG tu sang tac moc thoi gian, ten to chuc, so lieu thong ke.\n"
    )

    @classmethod
    def get_system_lock(cls, query_type: QueryType) -> str:
        mapping = {
            QueryType.FACT_CRITICAL:      cls.FACT_CRITICAL_LOCK,
            QueryType.TEMPORAL_SENSITIVE: cls.TEMPORAL_SENSITIVE_LOCK,
            QueryType.PARAMETRIC_SAFE:    cls.PARAMETRIC_SAFE_MODE,
            QueryType.AMBIGUOUS:          cls.AMBIGUOUS_LOCK,
        }
        return mapping.get(query_type, cls.AMBIGUOUS_LOCK)

    @classmethod
    def get_temperature(cls, query_type: QueryType) -> float:
        mapping = {
            QueryType.FACT_CRITICAL:      0.0,
            QueryType.TEMPORAL_SENSITIVE: 0.1,
            QueryType.PARAMETRIC_SAFE:    0.5,
            QueryType.AMBIGUOUS:          0.2,
        }
        return mapping.get(query_type, 0.2)


# ---------------------------------------------------------------------------
# EpistemicShield
# ---------------------------------------------------------------------------

@dataclass
class GuardedResponse:
    answer: str
    query_type: QueryType
    data_source: str
    confidence: float
    uncertainty_warning: str = ""
    should_verify: bool = False
    rag_evidence_count: int = 0
    verifier_verdict: str = ""
    elapsed_ms: float = 0.0

    def to_display(self) -> str:
        parts = [self.answer]
        if self.uncertainty_warning:
            parts.append(f"\n{self.uncertainty_warning}")
        footer_parts = [f"Nguon: {self.data_source}"]
        if self.rag_evidence_count > 0:
            footer_parts.append(f"Tai lieu: {self.rag_evidence_count}")
        label = "Cao" if self.confidence >= 0.8 else "Trung binh" if self.confidence >= 0.5 else "Thap"
        footer_parts.append(f"Do tin cay: {label} ({self.confidence:.0%})")
        if self.should_verify:
            footer_parts.append("Nen xac minh them")
        parts.append("\n[" + " | ".join(footer_parts) + "]")
        return "".join(parts)


class EpistemicShield:
    @staticmethod
    def wrap(
        answer: str,
        query_type: QueryType,
        rag_evidence_count: int = 0,
        rag_scores: Optional[List[float]] = None,
        verifier_verdict: str = "",
        elapsed_ms: float = 0.0,
    ) -> GuardedResponse:
        start = time.monotonic()
        confidence = 0.0
        data_source = "PARAMETRIC"

        if rag_evidence_count > 0:
            data_source = "RAG"
            if rag_scores:
                valid = [s for s in rag_scores if s > 0]
                confidence = sum(valid) / len(valid) if valid else 0.5
            else:
                confidence = 0.6

        if verifier_verdict == "VERIFIED":
            confidence = max(confidence, 0.85)
        elif verifier_verdict == "PARTIAL":
            confidence = max(confidence, 0.60)
        elif verifier_verdict == "CONTRADICTION":
            confidence = min(confidence, 0.30)
        elif verifier_verdict == "UNVERIFIED":
            confidence = min(confidence, 0.40)

        if "[JKAI-UNVERIFIED]" in answer:
            data_source = "UNVERIFIED"
            confidence = 0.0

        uncertainty_warning = ""
        should_verify = False

        if query_type == QueryType.FACT_CRITICAL:
            should_verify = True
            if data_source == "PARAMETRIC":
                uncertainty_warning = (
                    "[CANH BAO]: Cau hoi yeu cau du lieu cu the nhung khong co trong tai lieu noi bo. "
                    "Thong tin co the khong chinh xac. Vui long xac minh voi nguon chinh thong."
                )
            elif confidence < 0.65:
                uncertainty_warning = "[LUU Y]: Do tin cay thap. Du lieu trong tai lieu co the chua day du."
        elif query_type == QueryType.TEMPORAL_SENSITIVE:
            should_verify = True
            uncertainty_warning = (
                "[CANH BAO-THOI-HAN]: Thong tin nay co the da thay doi. "
                "Can cap nhat tu nguon hien hanh."
            )

        elapsed_total = elapsed_ms + (time.monotonic() - start) * 1000
        return GuardedResponse(
            answer=answer,
            query_type=query_type,
            data_source=data_source,
            confidence=confidence,
            uncertainty_warning=uncertainty_warning,
            should_verify=should_verify,
            rag_evidence_count=rag_evidence_count,
            verifier_verdict=verifier_verdict,
            elapsed_ms=elapsed_total,
        )


# ---------------------------------------------------------------------------
# Convenience Singletons
# ---------------------------------------------------------------------------

query_classifier = QueryClassifier()
epistemic_shield = EpistemicShield()


# ---------------------------------------------------------------------------
# 3-Level No-RAG Fallback System
# ---------------------------------------------------------------------------

class NoRagFallbackLevel(str, Enum):
    """
    3 muc xu ly khi FACT_CRITICAL query khong tim duoc RAG context.

    Level 1 - WEB_SEARCH:      Goi web search, lay nguon thuc.
    Level 2 - MODEL_DISCLAIMER: Dung model + disclaimer bat buoc (kien thuc on dinh).
    Level 3 - UNVERIFIED:      Tu choi hoan toan (thong tin nhay cam/de sai).
    """
    WEB_SEARCH         = "WEB_SEARCH"
    MODEL_DISCLAIMER   = "MODEL_DISCLAIMER"
    UNVERIFIED         = "UNVERIFIED"


# Patterns danh dau kien thuc ON DINH, CONG KHAI (du dieu kien Level 2)
# Day la nhung gi model hoc duoc tu nhieu nguon uy tin va it thay doi theo thoi gian
_STABLE_KNOWLEDGE_PATTERNS: List[re.Pattern] = [
    # Dia ly va hanh chinh co ban (ten goi, vi tri, cap bac)
    re.compile(
        "(thuộc tỉnh|tỉnh lỵ|vùng miền|miền bắc|miền trung|miền nam"
        "|thuủ đô|thành phố trực thuộc|capital city|located in|geography of"
        "|continent|country|nation|region|capital of)",
        re.IGNORECASE,
    ),
    # Khai niem hanh chinh co dinh (co cau, phan cap)
    re.compile(
        "(cấu trúc hành chính|phân cấp hành chính|administrative structure"
        "|system of government|administrative division|how many levels|bảo nhiêu cấp"
        "|how many cap|cơ cấu tổ chức"
        "|hanh chinh|cấu trúc)",
        re.IGNORECASE,
    ),
    # Su kien lich su da duoc kiem chung
    re.compile(
        "(lịch sử Việt Nam|chiến tranh|thống nhất|cách mạng"
        "|vietnam war|reunification|independence|founded in|established in|historical)",
        re.IGNORECASE,
    ),
    # Kien thuc co ban, on dinh ve KH-KT va khai niem
    re.compile(
        "(nguyên lý|how does|what is the difference|so sánh|explain|khác nhau"
        "|definition|concept|theory|principle|what is a|what are the)",
        re.IGNORECASE,
    ),
    # Cau hoi ve so luong co ban (on dinh, khong thay doi nhanh)
    # Dung .* cho phep cac tu o giua (vi du: how many administrative levels)
    re.compile(
        "(how many.{0,30}levels|how many.{0,30}tiers|how many.{0,30}provinces"
        "|how many.{0,30}districts|bảo nhiêu.{0,20}tỉnh|bảo nhiêu.{0,20}cấp"
        "|bao nhieu.{0,20}tinh|bao nhieu.{0,20}cap|bao nhieu.{0,20}huyen)",
        re.IGNORECASE,
    ),
]

# Patterns danh dau thong tin NHAY CAM, DE SAI (chi du Level 3 - UNVERIFIED)
# Day la nhung gi model co the bao ra sai so nghiem trong
_VOLATILE_SENSITIVE_PATTERNS: List[re.Pattern] = [
    # Nhan su hien tai (co the da thay doi)
    re.compile(
        "(hiện tại ai|ai đang giữ|bộ trưởng hiện nay|current minister"
        "|current president|current prime minister|who is currently|ai là bộ trưởng"
        "|who leads|who heads|current leader|who is the)",
        re.IGNORECASE,
    ),
    # So lieu thong ke co the cu (dan so, GDP cu the theo nam)
    re.compile(
        "(dân số năm 20\\d{2}|GDP năm|tăng trưởng năm"
        "|population in 20\\d{2}|GDP in 20\\d{2}|growth rate in 20\\d{2}"
        "|in year 20\\d{2}|nam 20\\d{2} dat)",
        re.IGNORECASE,
    ),
    # Phap luat cu the (so hieu van ban, dieu khoan)
    re.compile(
        "(nghị định số|thông tư số|quyết định số|article \\d+"
        "|decree no\\.|section \\d+|clause \\d+|diều \\d+ nghị định)",
        re.IGNORECASE,
    ),
    # Gia ca, ty gia (thay doi lien tuc)
    re.compile(
        "(giá hiện tại|giá hôm nay|tỷ giá hôm nay"
        "|current price|today price|live rate|spot price|today rate)",
        re.IGNORECASE,
    ),
]


class KnowledgeStabilityAnalyzer:
    """
    Phan tich muc do on dinh cua cau hoi de chon fallback level.

    Ket qua:
    - is_stable_public: True  → du dieu kien Level 2 (model + disclaimer)
    - is_stable_public: False → chi duoc Level 3 (UNVERIFIED)
    """

    def assess(self, query: str) -> bool:
        """
        True = kien thuc on dinh, model co the tra loi voi disclaimer.
        False = thong tin nhay cam, phai UNVERIFIED.
        """
        q = (query or "").strip()
        if not q:
            return False

        # Neu co bat ky volatile pattern nao → KHONG cho phep model tu doan
        volatile_hits = sum(1 for p in _VOLATILE_SENSITIVE_PATTERNS if p.search(q))
        if volatile_hits >= 1:
            logger.debug("[KnowledgeStability] VOLATILE detected (score=%d): %s", volatile_hits, q[:60])
            return False

        # Neu co stable pattern → cho phep model + disclaimer
        stable_hits = sum(1 for p in _STABLE_KNOWLEDGE_PATTERNS if p.search(q))
        if stable_hits >= 1:
            logger.debug("[KnowledgeStability] STABLE detected (score=%d): %s", stable_hits, q[:60])
            return True

        # Mac dinh: khong xac dinh duoc → an toan hon la UNVERIFIED
        return False


class NoRagFallbackDecider:
    """
    Quyet dinh muc fallback khi FACT_CRITICAL query khong co RAG context.

    Logic phan luong:
    1. Neu web_search_available=True     → Level 1: WEB_SEARCH
    2. Neu query la stable public knowledge → Level 2: MODEL_DISCLAIMER
    3. Mac dinh                          → Level 3: UNVERIFIED
    """

    def __init__(self) -> None:
        self._stability = KnowledgeStabilityAnalyzer()

    def decide(
        self,
        query: str,
        web_search_available: bool = False,
    ) -> NoRagFallbackLevel:
        """
        Quyet dinh fallback level cho query khong co RAG.

        Args:
            query: Cau hoi goc.
            web_search_available: True neu he thong co the goi web search.
        """
        # Level 1: Co web search → uu tien nhat
        if web_search_available:
            logger.info("[NoRagFallback] Level 1 WEB_SEARCH available for: %s", query[:60])
            return NoRagFallbackLevel.WEB_SEARCH

        # Level 2: Kien thuc on dinh → model + disclaimer
        if self._stability.assess(query):
            logger.info("[NoRagFallback] Level 2 MODEL_DISCLAIMER for: %s", query[:60])
            return NoRagFallbackLevel.MODEL_DISCLAIMER

        # Level 3: Tu choi hoan toan
        logger.info("[NoRagFallback] Level 3 UNVERIFIED for: %s", query[:60])
        return NoRagFallbackLevel.UNVERIFIED


# PromptLock extension: prompt cho Level 2 MODEL_DISCLAIMER
class _ModelDisclaimerPromptLock:
    """
    System prompt cho truong hop dung parametric memory voi disclaimer bat buoc.
    Duoc goi khi: FACT_CRITICAL + khong co RAG + kien thuc duoc danh gia la on dinh.
    """
    LOCK = (
        "[JKAI MODEL-DISCLAIMER MODE]\\n"
        "Tai lieu noi bo khong co thong tin ve cau hoi nay.\\n"
        "Ban duoc phep dung kien thuc noi tai NHUNG phai tuan thu NGHIEM NGAT cac quy tac sau:\\n\\n"
        "LUAT BAT BUOC:\\n"
        "1. Mo dau bang: [JKAI-MODEL-KNOWLEDGE]: Thong tin sau day tu kien thuc model, CHUA DUOC XAC NHAN boi tai lieu noi bo.\\n"
        "2. Tra loi chinh xac, ngan gon, khong bay bong.\\n"
        "3. Neu ro dieu gi ban KHONG CHAC CHAN: '[KHONG CHAC]: ...'\\n"
        "4. Ket thuc BANG DONG: [Nguon: Kien thuc model | Khuyen xac minh them tai nguon chinh thong]\\n"
        "5. TUYET DOI KHONG tu tao moc thoi gian (nam, ngay thang) neu khong chac chan 100%.\\n"
    )

    UNVERIFIED_RESPONSE_TEMPLATE = (
        "[JKAI-UNVERIFIED]: Toi khong tim thay thong tin xac thuc ve cau hoi nay trong tai lieu noi bo.\\n"
        "Cau hoi nay lien quan den thong tin co the thay doi hoac can nguon chinh thong.\\n"
        "Vui long xac minh tai:\\n"
        "  - Cac co quan nha nuoc: chinhphu.vn, dangcongsan.vn, gso.gov.vn\\n"
        "  - Bo nganh lien quan\\n"
        "  - Van ban phap luat chinh thuc"
    )


# Extend PromptLock with the disclaimer mode
PromptLock.MODEL_DISCLAIMER_LOCK = _ModelDisclaimerPromptLock.LOCK  # type: ignore[attr-defined]
PromptLock.UNVERIFIED_RESPONSE = _ModelDisclaimerPromptLock.UNVERIFIED_RESPONSE_TEMPLATE  # type: ignore[attr-defined]


# Singleton
fallback_decider = NoRagFallbackDecider()
