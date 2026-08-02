"""
Tests for Vietnamese locale patterns (locale/vi_vn.py). Converted to proper pytest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils.regex.locale.vi_vn import (
    KNOWLEDGE_QUERY,
    ERROR_VI, AUDIT_VI, FIX_VI,
    SEARCH_NEWS,
    CHAT, SOCIAL_GREETING, IDENTITY_INQUIRY, CAPABILITIES_INQUIRY,
    BUILD, OPERATE,
    SINGLE_FILE_FIX, SMALL_SCOPE,
    clean_vn_for_match,
)


# ── KNOWLEDGE_QUERY ───────────────────────────────────────────────────
def test_knowledge_query():
    assert bool(KNOWLEDGE_QUERY.search("Python la gi?"))
    assert bool(KNOWLEDGE_QUERY.search("Tao la ai?"))
    assert bool(KNOWLEDGE_QUERY.search("Dinh nghia cua AI"))
    assert bool(KNOWLEDGE_QUERY.search("Hay giai thich ve machine learning"))
    assert bool(KNOWLEDGE_QUERY.search("Explain quantum computing"))
    assert bool(KNOWLEDGE_QUERY.search("Tim hieu ve Docker"))
    assert bool(KNOWLEDGE_QUERY.search("Khac nhau giua Python va Java"))
    assert bool(KNOWLEDGE_QUERY.search("Tai sao troi lai mua?"))
    assert bool(KNOWLEDGE_QUERY.search("Lam the nao de hoc lap trinh?"))
    assert bool(KNOWLEDGE_QUERY.search("Huong dan su dung Git"))
    assert not KNOWLEDGE_QUERY.search("Hom nay the nao?")
    assert not KNOWLEDGE_QUERY.search("Gio la may gio?")


# ── ERROR_VI ──────────────────────────────────────────────────────────
def test_error_vi():
    assert bool(ERROR_VI.search("Bi loi mat ket noi"))
    assert bool(ERROR_VI.search("Bug trong module"))
    assert bool(ERROR_VI.search("He thong bi crash"))
    assert bool(ERROR_VI.search("Ung dung khong chay"))
    assert bool(ERROR_VI.search("Can sua loi nay"))
    assert not ERROR_VI.search("Hom nay troi dep")
    assert bool(ERROR_VI.search("Tim nguyen nhan gay ra loi"))


# ── AUDIT_VI ──────────────────────────────────────────────────────────
def test_audit_vi():
    assert bool(AUDIT_VI.search("Ra soat toan bo code"))
    assert bool(AUDIT_VI.search("Kiem tra hieu nang"))
    assert bool(AUDIT_VI.search("Audit security"))
    assert bool(AUDIT_VI.search("Phan tich he thong"))
    assert bool(AUDIT_VI.search("Doc code gium toi"))
    assert not AUDIT_VI.search("Chao buoi sang")


# ── FIX_VI ────────────────────────────────────────────────────────────
def test_fix_vi():
    assert bool(FIX_VI.search("Sua loi nay di"))
    assert bool(FIX_VI.search("Fix bug trong file main.py"))
    assert bool(FIX_VI.search("Khac phuc su co"))
    assert bool(FIX_VI.search("Repair the database"))
    assert not FIX_VI.search("Hom nay the nao")


# ── SEARCH_NEWS ───────────────────────────────────────────────────────
def test_search_news():
    assert bool(SEARCH_NEWS.search("Tim tin tuc hom nay"))
    assert bool(SEARCH_NEWS.search("Search for python tutorial"))
    assert bool(SEARCH_NEWS.search("Latest news about AI"))
    assert bool(SEARCH_NEWS.search("Thong tin moi nhat"))
    assert not SEARCH_NEWS.search("Chao ban")


# ── CHAT ──────────────────────────────────────────────────────────────
def test_chat():
    assert bool(CHAT.search("Xin chào"))
    assert bool(CHAT.search("hello"))
    assert bool(CHAT.search("Cam on ban"))
    assert not CHAT.search("Python la gi")
    assert bool(CHAT.search("Thoi tiet hom nay"))


# ── SOCIAL_GREETING ───────────────────────────────────────────────────
def test_social_greeting():
    assert bool(SOCIAL_GREETING.search("Chao ban"))
    assert bool(SOCIAL_GREETING.search("Hi there"))
    assert bool(SOCIAL_GREETING.search("Cam on nhieu"))
    assert not SOCIAL_GREETING.search("Code giup toi")


# ── IDENTITY_INQUIRY ──────────────────────────────────────────────────
def test_identity_inquiry():
    assert bool(IDENTITY_INQUIRY.search("Ban la ai"))
    assert bool(IDENTITY_INQUIRY.search("Who are you?"))
    assert bool(IDENTITY_INQUIRY.search("Ai tao ra ban"))
    assert not IDENTITY_INQUIRY.search("Python la gi")


# ── CAPABILITIES_INQUIRY ──────────────────────────────────────────────
def test_capabilities_inquiry():
    assert bool(CAPABILITIES_INQUIRY.search("Liet ke tinh nang"))
    assert bool(CAPABILITIES_INQUIRY.search("Ban lam duoc gi"))
    assert bool(CAPABILITIES_INQUIRY.search("What are your features"))
    assert bool(CAPABILITIES_INQUIRY.search("Giới thiệu về bản thân"))
    assert not CAPABILITIES_INQUIRY.search("Python la gi")


# ── BUILD ─────────────────────────────────────────────────────────────
def test_build():
    assert bool(BUILD.search("Tao mot web app"))
    assert bool(BUILD.search("Build the project"))
    assert bool(BUILD.search("Deploy len server"))
    assert not BUILD.search("Chao ban")


# ── OPERATE ───────────────────────────────────────────────────────────
def test_operate():
    assert bool(OPERATE.search("Chay docker compose"))
    assert bool(OPERATE.search("Deploy he thong"))
    assert bool(OPERATE.search("Restart service"))
    assert bool(OPERATE.search("Kubectl get pods"))
    assert not OPERATE.search("Python la gi")


# ── SINGLE_FILE_FIX ───────────────────────────────────────────────────
def test_single_file_fix():
    assert bool(SINGLE_FILE_FIX.search("Sua loi trong main.py"))
    assert bool(SINGLE_FILE_FIX.search("Fix bug in app.js"))
    assert bool(SINGLE_FILE_FIX.search("Sua file config.json"))
    assert not SINGLE_FILE_FIX.search("Chao ban")


# ── SMALL_SCOPE ───────────────────────────────────────────────────────
def test_small_scope():
    assert bool(SMALL_SCOPE.search("Chi sua mot file"))
    assert bool(SMALL_SCOPE.search("Just a single file"))
    assert not SMALL_SCOPE.search("Sua toan bo project")


# ── clean_vn_for_match ────────────────────────────────────────────────
def test_clean_vn_for_match():
    assert clean_vn_for_match("Xin Chào") == "xin chao"
    assert clean_vn_for_match("định nghĩa") == "dinh nghia"
    assert clean_vn_for_match("Làm Thế Nào") == "lam the nao"
