# -*- coding: utf-8 -*-
"""
Unit tests for DeterministicToolArbiter and Pentad Sovereign Actuators Matrix.
SDS v28.26.0 - Elite Hardened Tool Arbiter across Concrete & Hypothetical Scenarios.
"""

import pytest
from core.kernel.tool_arbiter import DeterministicToolArbiter, ToolDomain, ArbiterVerdict


# ---------------------------------------------------------------------------
# 1. BROWSER M2 (VISUAL & INTERACTIVE) VS FAST_DOC M4 (HEADLESS TEXT)
# ---------------------------------------------------------------------------

def test_arbiter_visual_browser_screenshot():
    """Trường hợp 1: Có URL và yêu cầu trực quan/screenshot -> BẮT BUỘC BROWSER (M2)."""
    goal = "hãy xem trang https://vietnamnet.vn/, chụp màn hình và tổng hợp tin mới hôm nay"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.BROWSER
    assert verdict.is_pure_browser() is True
    assert verdict.is_visual_required is True
    assert verdict.primary_target == "https://vietnamnet.vn/"
    assert "https://vietnamnet.vn/" in verdict.extracted_urls
    assert "BROWSER_CONTROL" in verdict.mandatory_tools
    assert "SEARCH_WEB_GLOBAL" in verdict.forbidden_tools

    step = DeterministicToolArbiter.generate_resilient_recovery_step(verdict, goal)
    assert step.tool == "BROWSER_CONTROL"
    assert step.args.get("take_screenshot") is True


def test_arbiter_fast_doc_reader_headless():
    """Trường hợp 2: Có URL nhưng chỉ đọc text/tóm tắt -> FAST_DOC (M4) siêu tốc 0MB VRAM."""
    goal = "đọc nội dung bài viết tại https://tuoitre.vn/kinh-te.htm và tóm tắt các ý chính"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.FAST_DOC
    assert verdict.is_browser() is True
    assert verdict.is_fast_doc() is True
    assert verdict.is_visual_required is False
    assert "https://tuoitre.vn/kinh-te.htm" in verdict.extracted_urls
    assert any(t in verdict.mandatory_tools for t in ["read_url_content", "web_read", "BROWSER_CONTROL"])
    assert "SEARCH_WEB_GLOBAL" in verdict.forbidden_tools


def test_arbiter_bare_domain_and_localhost():
    """Trường hợp 3: Domain không có scheme (vnexpress.net) và localhost:8000."""
    goal_bare = "vào trang vnexpress.net xem tin nóng"
    verdict_bare = DeterministicToolArbiter.arbitrate(goal_bare)
    assert verdict_bare.is_browser() is True
    assert "https://vnexpress.net" in verdict_bare.extracted_urls

    goal_lh = "truy cập http://localhost:8000/docs kiểm tra API"
    verdict_lh = DeterministicToolArbiter.arbitrate(goal_lh)
    assert verdict_lh.is_browser() is True
    assert "http://localhost:8000/docs" in verdict_lh.extracted_urls


# ---------------------------------------------------------------------------
# 2. CODEBASE SEARCH (M0) VS INTERNET SEARCH (M3)
# ---------------------------------------------------------------------------

def test_arbiter_codebase_grep_search_not_web():
    """Trường hợp 4: Tìm kiếm hàm/code trong repo -> FILE (grep_search), CẤM SearchWeb!"""
    goal = "tìm kiếm hàm resolve_tool_alias trong thư mục core"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.FILE
    assert verdict.is_file() is True
    assert verdict.is_codebase_search is True
    assert verdict.extracted_code_query == "resolve_tool_alias"
    assert "grep_search" in verdict.mandatory_tools
    assert "SEARCH_WEB_GLOBAL" in verdict.forbidden_tools

    guidance = DeterministicToolArbiter.generate_planner_guidance(verdict)
    assert "grep_search" in guidance
    assert "CẤM SearchWeb" in guidance or "TUYỆT ĐỐI CẤM dùng SEARCH_WEB_GLOBAL" in guidance

    step = DeterministicToolArbiter.generate_resilient_recovery_step(verdict, goal)
    assert step.tool == "grep_search"
    assert step.args.get("Query") == "resolve_tool_alias"


def test_arbiter_internet_searchweb():
    """Trường hợp 5: Tra cứu tri thức internet khi CHƯA có URL -> SEARCHWEB (M3)."""
    goal = "tìm kiếm giá vàng hôm nay tại Việt Nam"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.SEARCHWEB
    assert verdict.is_search_web() is True
    assert "SEARCH_WEB_GLOBAL" in verdict.mandatory_tools
    assert len(verdict.extracted_urls) == 0


# ---------------------------------------------------------------------------
# 3. GIẢ TƯỞNG & GIẢ ĐỊNH (COUNTERFACTUAL / HYPOTHETICAL CASES)
# ---------------------------------------------------------------------------

def test_arbiter_hypothetical_url_scenario():
    """Trường hợp 6: Câu lệnh giả định với URL ('Giả sử có URL https://... hãy chụp ảnh')."""
    goal = "Giả sử có URL https://example.com/test-dashboard, hãy mở trực quan và chụp màn hình"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.is_hypothetical is True
    assert verdict.primary_domain == ToolDomain.BROWSER
    assert "https://example.com/test-dashboard" in verdict.extracted_urls
    assert verdict.is_visual_required is True

    guidance = DeterministicToolArbiter.generate_planner_guidance(verdict)
    assert "CHỈ THỊ NGỮ CẢNH GIẢ ĐỊNH" in guidance
    assert "BẮT BUỘC PHẢI DÙNG BROWSER TRỰC QUAN" in guidance


def test_arbiter_hypothetical_file_scenario():
    """Trường hợp 7: Câu lệnh giả định với file ('Nếu muốn kiểm tra file core/kernel/...')."""
    goal = "Nếu muốn kiểm tra file core/kernel/tool_arbiter.py thì mở lên xem"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.is_hypothetical is True
    assert verdict.primary_domain == ToolDomain.FILE
    assert "core/kernel/tool_arbiter.py" in verdict.extracted_files
    assert any(t in verdict.mandatory_tools for t in ["VIEW_FILE", "replace_file_content"])


def test_arbiter_hypothetical_terminal_scenario():
    """Trường hợp 8: Câu lệnh giả định với terminal ('Kịch bản mô phỏng: chạy pytest...')."""
    goal = "Kịch bản mô phỏng: chạy test pytest tests/test_local_tool_execution.py"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.is_hypothetical is True
    assert verdict.primary_domain in (ToolDomain.TERMINAL, ToolDomain.HYBRID)
    assert "pytest" in verdict.extracted_commands or any("pytest" in c for c in verdict.extracted_commands)


# ---------------------------------------------------------------------------
# 4. QUY TRÌNH LIÊN HOÀN (HYBRID MULTI-STAGE WORKFLOWS)
# ---------------------------------------------------------------------------

def test_arbiter_hybrid_browse_then_save():
    """Trường hợp 9: Tải web và lưu vào file -> HYBRID (FAST_DOC/BROWSER + FILE)."""
    goal = "đọc trang https://vietnamnet.vn/ rồi lưu vào file tin_tuc.md"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.HYBRID
    assert verdict.is_hybrid() is True
    assert verdict.has_file() is True
    assert verdict.has_browser() is True
    assert "https://vietnamnet.vn/" in verdict.extracted_urls
    assert "tin_tuc.md" in verdict.extracted_files
    assert "WRITE_TO_FILE" in verdict.mandatory_tools


def test_arbiter_hybrid_file_then_test():
    """Trường hợp 10: Sửa file và chạy test -> HYBRID (FILE + TERMINAL)."""
    goal = "sửa file core/kernel/policy_snapshot.py và chạy lệnh pytest tests/test_execution_boundary_closure.py"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.HYBRID
    assert verdict.has_file() is True
    assert verdict.has_terminal() is True
    assert "core/kernel/policy_snapshot.py" in verdict.extracted_files
    assert any("pytest" in c for c in verdict.extracted_commands)


# ---------------------------------------------------------------------------
# 5. RESILIENT RECOVERY STEP VALIDATION
# ---------------------------------------------------------------------------

def test_arbiter_recovery_step_visual_browser():
    """Trường hợp 11: Recovery step cho BROWSER visual sinh load_page có screenshot."""
    goal = "xem trang https://dantri.com.vn và chụp ảnh màn hình"
    verdict = DeterministicToolArbiter.arbitrate(goal)
    step = DeterministicToolArbiter.generate_resilient_recovery_step(verdict, goal)

    assert step.tool == "BROWSER_CONTROL"
    assert step.args.get("url") == "https://dantri.com.vn"
    assert step.args.get("take_screenshot") is True


def test_arbiter_recovery_step_terminal_system_cmd():
    """Trường hợp 12: Recovery step cho TERMINAL sinh SYSTEM_CMD."""
    goal = "chạy lệnh git status trong terminal"
    verdict = DeterministicToolArbiter.arbitrate(goal)
    step = DeterministicToolArbiter.generate_resilient_recovery_step(verdict, goal)

    assert step.tool in ("SYSTEM_CMD", "EXECUTE_COMMAND")
    assert "git" in str(step.args.get("command", ""))


# ---------------------------------------------------------------------------
# 6. RED TEAM EDGE CASES (MICRO-PATCH VERIFICATION)
# ---------------------------------------------------------------------------

def test_arbiter_trailing_punctuation_in_url():
    """Trường hợp 13: URL có dấu chấm hoặc phẩy dính cuối câu phải được làm sạch triệt để."""
    goal = "đọc bài viết https://example.com/blog/intro. Sau đó tóm tắt nội dung,"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.is_browser() is True
    assert "https://example.com/blog/intro" in verdict.extracted_urls
    assert not any(u.endswith(".") for u in verdict.extracted_urls)
    assert not any(u.endswith(",") for u in verdict.extracted_urls)


def test_arbiter_code_search_with_internet_keyword_routes_to_searchweb():
    """Trường hợp 14: Tìm hàm nhưng có chỉ định internet (trên google/online) -> SEARCHWEB, không nhầm sang FILE."""
    goal = "tìm kiếm hàm sha256 trên Google"
    verdict = DeterministicToolArbiter.arbitrate(goal)

    assert verdict.primary_domain == ToolDomain.SEARCHWEB
    assert verdict.is_search_web() is True
    assert "SEARCH_WEB_GLOBAL" in verdict.mandatory_tools
    assert "grep_search" not in verdict.mandatory_tools

