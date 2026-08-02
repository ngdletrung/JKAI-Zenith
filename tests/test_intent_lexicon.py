"""
Tests for intent_lexicon (keyword-based intent classifier).
Converted from legacy script-style to proper pytest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.utils.intent_lexicon import (
    _normalize,
    full_classify,
    extract_scalar,
    extract_action_pairs,
    extract_context_pairs,
    extract_entities,
    INTENT_BOOKS,
    ADVANCED_INTENT_BOOKS,
)


# ── _normalize ─────────────────────────────────────────────────────────
def test_normalize():
    assert _normalize("") == ""
    assert _normalize(None) == ""
    assert _normalize("HELLO") == "hello"
    assert _normalize("hello, world!") == "hello world"
    assert _normalize("ko") == "khong"
    assert _normalize("dc") == "duoc"
    assert _normalize("j") == "gi"
    assert _normalize("ko dc j") == "khong duoc gi"
    assert _normalize("tìm kiếm") == "tim kiem"
    assert _normalize("được") == "duoc"
    assert _normalize("àáảãạ") == "aaaaa"
    assert _normalize("êềếểễệ") == "eeeeee"
    assert _normalize("Tìm kiếm news hôm nay") == "tim kiem news hom nay"
    assert _normalize("  nhiều    space  ") == "nhieu space"
    assert _normalize("hello.world,test;data:here!query?") == "hello world test data here query"


# ── extract_scalar ─────────────────────────────────────────────────────
def test_extract_scalar():
    assert extract_scalar("find 5 articles") == 5
    assert extract_scalar("10 papers and 3 reports") == 10
    assert extract_scalar("no numbers here") is None


# ── extract_action_pairs ───────────────────────────────────────────────
def test_extract_action_pairs():
    assert len(extract_action_pairs("tim tin tuc")) > 0
    assert len(extract_action_pairs("search news")) > 0
    assert len(extract_action_pairs("sua loi")) > 0
    assert len(extract_action_pairs("phan tich du lieu")) > 0
    assert extract_action_pairs("hello world") == []


# ── extract_context_pairs ──────────────────────────────────────────────
def test_extract_context_pairs():
    assert len(extract_context_pairs("the gioi hom nay")) > 0
    assert len(extract_context_pairs("viet nam hom qua")) > 0
    assert len(extract_context_pairs("cong nghe hom nay")) > 0
    assert extract_context_pairs("just testing") == []


# ── extract_entities ───────────────────────────────────────────────────
def test_extract_entities():
    ents = extract_entities("the gioi hom nay")
    assert "today" in ents.get("time", [])
    assert "global" in ents.get("location", [])
    ents2 = extract_entities("cong nghe viet nam")
    assert "technology" in ents2.get("topic", [])
    assert "vietnam" in ents2.get("location", [])


# ── full_classify: Core INTENT_BOOKS ───────────────────────────────────
def test_classify_core_intents():
    assert full_classify("create a new app")["task"]["value"] == "CREATE"
    assert full_classify("edit the file")["task"]["value"] == "EDIT"
    assert full_classify("delete file")["task"]["value"] == "DELETE"
    assert full_classify("analyze this data")["task"]["value"] == "ANALYZE"
    assert full_classify("explain concept please")["task"]["value"] == "EXPLAIN"
    assert full_classify("plan a roadmap")["task"]["value"] == "PLAN"
    assert full_classify("translate to english")["task"]["value"] == "TRANSLATE"


# ── full_classify: ADVANCED_INTENT_BOOKS ───────────────────────────────
def test_classify_advanced_intents():
    assert full_classify("debug lỗi crash này")["task"]["value"] == "DEBUG"
    assert full_classify("tìm kiếm tin tức mới nhất")["task"]["value"] == "SEARCH"
    assert full_classify("nghiên cứu thị trường")["task"]["value"] == "RESEARCH"
    assert full_classify("tóm tắt bài viết này")["task"]["value"] == "SUMMARIZE"


# ── full_classify: Domains ─────────────────────────────────────────────
def test_classify_domains():
    assert full_classify("viết code python")["domain"]["value"] == "CODING"
    assert full_classify("triển khai kubernetes")["domain"]["value"] == "DEVOPS"
    assert full_classify("phân tích dataset csv")["domain"]["value"] == "DATA"


# ── full_classify: Social / Emotion ────────────────────────────────────
def test_classify_social_emotion():
    assert full_classify("tôi không hiểu")["social"]["value"] == "CONFUSED"
    assert full_classify("bực mình quá")["social"]["value"] == "FRUSTRATED"
    assert full_classify("chào bạn")["social"]["value"] == "GREETING"


# ── full_classify: Politeness ──────────────────────────────────────────
def test_classify_politeness():
    assert full_classify("làm ơn giúp tôi")["politeness"]["value"] == "REQUESTING"
    assert full_classify("làm ngay đi")["politeness"]["value"] == "COMMANDING"


# ── full_classify: Question type ───────────────────────────────────────
def test_classify_question_type():
    assert full_classify("định nghĩa là gì")["question_type"]["value"] == "WHAT"
    assert full_classify("làm thế nào để code")["question_type"]["value"] == "HOW"
    assert full_classify("tại sao trời mưa")["question_type"]["value"] == "WHY"


# ── full_classify: Format ──────────────────────────────────────────────
def test_classify_format():
    assert full_classify("liệt kê các bước")["format"]["value"] == "LIST"
    assert full_classify("viết code cho tôi")["format"]["value"] == "CODE"
    assert full_classify("trả về json")["format"]["value"] == "JSON"


# ── full_classify: Meta ────────────────────────────────────────────────
def test_classify_meta():
    assert full_classify("tiếp tục đi")["meta"]["value"] == "CONTINUE"
    assert full_classify("thử lại")["meta"]["value"] == "RETRY"


# ── full_classify: Language detection ──────────────────────────────────
def test_classify_language():
    assert full_classify("xin chào tôi là người việt nam")["language"] == "VIETNAMESE"


# ── full_classify: Edge cases ──────────────────────────────────────────
def test_classify_edge_cases():
    assert full_classify("")["task"]["value"] is None
    assert full_classify("   ")["task"]["value"] is None
    assert full_classify("xyzabc")["task"]["value"] is None
    assert full_classify("123 456")["task"]["value"] is None


# ── full_classify: Negation reduces confidence ─────────────────────────
def test_classify_negation_lowers_confidence():
    r_pos = full_classify("create app")
    r_neg = full_classify("không create app")
    assert r_neg["task"]["confidence"] < r_pos["task"]["confidence"]


# ── full_classify: Scalar in result ────────────────────────────────────
def test_classify_scalar():
    assert full_classify("tìm 3 bài báo về AI")["scalar"] == 3
    assert full_classify("không có số")["scalar"] is None


# ── full_classify: Action/Context pairs ────────────────────────────────
def test_classify_pairs_and_entities():
    r = full_classify("tìm kiếm tin tức thế giới hôm nay")
    assert len(r["action_pairs"]) > 0
    assert len(r["context_pairs"]) > 0
    assert len(r.get("entities", {})) > 0


# ── full_classify: is_question ─────────────────────────────────────────
def test_classify_is_question():
    assert full_classify("bạn là ai?")["is_question"] is True
    assert full_classify("định nghĩa là gì")["is_question"] is True
    assert full_classify("bạn là ai?")["is_question"] is True
    assert full_classify("hãy tạo ứng dụng")["is_question"] is False


# ── Confidence: exact match = 1.0 ─────────────────────────────────────
def test_classify_exact_match_confidence():
    assert full_classify("khởi tạo dự án")["task"]["confidence"] == 1.0


# ── Cross-module drift check: keywords shared with core/utils/regex/locale/vi_vn.py ──
def test_cross_module_keyword_drift():
    _EDIT_KW = set()
    for cat in INTENT_BOOKS.get("EDIT", {}).values():
        _EDIT_KW.update(w.lower() for w in cat)
    _DEBUG_KW = set()
    for cat in ADVANCED_INTENT_BOOKS.get("DEBUG", {}).values():
        _DEBUG_KW.update(w.lower() for w in cat)
    _CREATE_KW = set()
    for cat in INTENT_BOOKS.get("CREATE", {}).values():
        _CREATE_KW.update(w.lower() for w in cat)

    assert "fix" in _EDIT_KW
    assert "crash" in _DEBUG_KW
    assert "repair" in _DEBUG_KW
    assert "build" in _CREATE_KW
    assert "scaffold" in _CREATE_KW
